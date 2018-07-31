#
# Copyright 2017-2018 European Centre for Medium-Range Weather Forecasts (ECMWF).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Authors:
#   Alessandro Amici - B-Open - https://bopen.eu
#

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import itertools
import logging
import typing as T

import attr
import xarray as xr  # noqa
from xarray import Variable
from xarray.core import indexing
from xarray.core.utils import FrozenOrderedDict
from xarray.backends.api import open_dataset as _open_dataset
from xarray.backends.api import _validate_attrs, _validate_dataset_names
from xarray.backends.common import AbstractDataStore, BackendArray

import cfgrib


LOGGER = logging.getLogger(__name__)


class WrapGrib(BackendArray):
    def __init__(self, backend_array):
        self.backend_array = backend_array

    def __getattr__(self, item):
        return getattr(self.backend_array, item)

    def __getitem__(self, item):
        key, np_inds = indexing.decompose_indexer(
            item, self.shape, indexing.IndexingSupport.OUTER_1VECTOR)

        array = self.backend_array[key.tuple]

        if len(np_inds.tuple) > 0:
            array = indexing.NumpyIndexingAdapter(array)[np_inds]

        return array


FLAVOURS = {
    'eccodes': {
        'dataset': {
            'encode_time': False,
            'encode_vertical': False,
            'encode_geography': False,
        },
    },
    'ecmwf': {
        'variable_map': {},
        'type_of_level_map': {
            'hybrid': lambda attrs: 'L%d' % ((attrs['GRIB_NV'] - 2) // 2),
        },
    },
    'cds': {
        'variable_map': {
            'number': 'realization',
            'time': 'forecast_reference_time',
            'valid_time': 'step',
            'step': 'leadtime',
            'air_pressure': 'plev',
            'latitude': 'lat',
            'longitude': 'lon',
            'topLevel': 'level',
        },
        'type_of_level_map': {
            'hybrid': lambda attrs: 'L%d' % ((attrs['GRIB_NV'] - 2) // 2),
        },
    },
}


@attr.attrs()
class GribDataStore(AbstractDataStore):
    ds = attr.attrib()
    variable_map = attr.attrib(default={})
    type_of_level_map = attr.attrib(default={})

    @classmethod
    def frompath(cls, path, flavour_name='ecmwf', errors='ignore', **kwargs):
        flavour = FLAVOURS[flavour_name].copy()
        config = flavour.pop('dataset', {}).copy()
        config.update(kwargs)
        return cls(ds=cfgrib.Dataset.frompath(path, errors=errors, **config), **flavour)

    def __attrs_post_init__(self):
        self.variable_map = self.variable_map.copy()
        for name, var in self.ds.variables.items():
            if self.ds.encode_vertical and 'GRIB_typeOfLevel' in var.attributes:
                type_of_level = var.attributes['GRIB_typeOfLevel']
                coord_name = self.type_of_level_map.get(type_of_level, type_of_level)
                if isinstance(coord_name, T.Callable):
                    coord_name = coord_name(var.attributes)
                self.variable_map['topLevel'] = coord_name.format(**var.attributes)

    def open_store_variable(self, name, var):
        if isinstance(var.data, cfgrib.dataset.OnDiskArray):
            data = indexing.LazilyOuterIndexedArray(WrapGrib(var.data))
        else:
            data = var.data

        dimensions = tuple(self.variable_map.get(dim, dim) for dim in var.dimensions)
        attrs = var.attributes

        # the coordinates attributes need a special treatment
        if 'coordinates' in attrs:
            coordinates = [self.variable_map.get(d, d) for d in attrs['coordinates'].split()]
            attrs['coordinates'] = ' '.join(coordinates)

        encoding = {}
        # save source so __repr__ can detect if it's local or not
        encoding['source'] = self.ds.stream.path
        encoding['original_shape'] = var.data.shape

        return Variable(dimensions, data, attrs, encoding)

    def get_variables(self):
        return FrozenOrderedDict((self.variable_map.get(k, k), self.open_store_variable(k, v))
                                 for k, v in self.ds.variables.items())

    def get_attrs(self):
        return FrozenOrderedDict(self.ds.attributes)

    def get_dimensions(self):
        return collections.OrderedDict((self.variable_map.get(d, d), s)
                                       for d, s in self.ds.dimensions.items())

    def get_encoding(self):
        encoding = {}
        encoding['unlimited_dims'] = {k for k, v in self.ds.dimensions.items() if v is None}
        return encoding


def open_dataset(path, flavour_name='ecmwf', filter_by_keys={}, errors='ignore', **kwargs):
    overrides = {
        'flavour_name': flavour_name,
        'filter_by_keys': filter_by_keys,
        'errors': errors,
    }
    for k in list(kwargs):  # copy to allow the .pop()
        if k.startswith('encode_'):
            overrides[k] = kwargs.pop(k)
    store = GribDataStore.frompath(path, **overrides)
    return _open_dataset(store, **kwargs)


#
# write support
#
def sample_name_detection(grib_attributes):
    # type: (T.Mapping) -> str

    if grib_attributes['gridType'] == 'regular_ll':
        geography = 'regular_ll'
    else:
        raise NotImplementedError("Unsupported 'gridType': %r" % grib_attributes['gridType'])

    if grib_attributes['typeOfLevel'] == 'isobaricInhPa':
        vertical = 'pl'
    elif grib_attributes['typeOfLevel'] in ('surface', 'meanSea'):
        vertical = 'sfc'
    else:
        raise NotImplementedError("Unsupported 'typeOfLevel': %r" % grib_attributes['typeOfLevel'])

    sample_name = '%s_%s_grib2' % (geography, vertical)
    return sample_name


def ecmwf_dataarray_to_grib(file, data_var, global_attributes={}, sample_name=None):
    # type: (T.BinaryIO, xr.DataArray, T.Dict[str, T.Any], str) -> None
    from cfgrib import cfmessage
    from cfgrib import eccodes
    from cfgrib import dataset

    grib_attributes = {k[5:]: v for k, v in global_attributes.items() if k[:5] == 'GRIB_'}
    grib_attributes.update({k[5:]: v for k, v in data_var.attrs.items() if k[:5] == 'GRIB_'})

    if sample_name is None:
        sample_name = sample_name_detection(grib_attributes)

    header_coords_names = []
    for coord_name in dataset.ALL_HEADER_DIMS:
        if coord_name in set(data_var.coords):
            header_coords_names.append(coord_name)
            if coord_name not in data_var.dims:
                data_var = data_var.expand_dims(coord_name)

    header_coords_values = [data_var.coords[name].values.tolist() for name in header_coords_names]
    for items in itertools.product(*header_coords_values):
        message = cfmessage.CfMessage.fromsample(sample_name)
        for key, value in grib_attributes.items():
            try:
                message[key] = value
            except eccodes.EcCodesError as ex:
                if ex.code != eccodes.lib.GRIB_READ_ONLY:
                    LOGGER.exception("Can't encode key: %r" % key)

        for coord_name, coord_value in zip(header_coords_names, items):
            message[coord_name] = coord_value

        select = {n: v for n, v in zip(header_coords_names, items)}
        message['values'] = data_var.sel(**select).values.flat[:].tolist()

        message.write(file)


def to_grib(ecmwf_dataset, path, mode='wb', sample_name=None):
    # validate Dataset keys, DataArray names, and attr keys/values
    _validate_dataset_names(ecmwf_dataset)
    _validate_attrs(ecmwf_dataset)

    with open(path, mode=mode) as file:
        for data_var in ecmwf_dataset.data_vars.values():
            ecmwf_dataarray_to_grib(
                file, data_var, global_attributes=ecmwf_dataset.attrs, sample_name=sample_name,
            )
