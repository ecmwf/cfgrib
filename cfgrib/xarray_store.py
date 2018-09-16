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
import numpy as np
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
    def from_path(cls, path, flavour_name='ecmwf', errors='ignore', **kwargs):
        flavour = FLAVOURS[flavour_name].copy()
        config = flavour.pop('dataset', {}).copy()
        config.update(kwargs)
        return cls(ds=cfgrib.Dataset.from_path(path, errors=errors, **config), **flavour)

    def __attrs_post_init__(self):
        self.variable_map = self.variable_map.copy()
        for name, var in self.ds.variables.items():
            if self.ds.encode_vertical and 'GRIB_typeOfLevel' in var.attributes:
                type_of_level = var.attributes['GRIB_typeOfLevel']
                coord_name = self.type_of_level_map.get(type_of_level, type_of_level)
                if isinstance(coord_name, T.Callable):
                    coord_name = coord_name(var.attributes)
                self.variable_map['level'] = coord_name.format(**var.attributes)

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
    store = GribDataStore.from_path(path, **overrides)
    return _open_dataset(store, **kwargs)


#
# write support
#
DEFAULT_GRIB_KEYS = {
    'centre': 255,  # missing value, see: http://apps.ecmwf.int/codes/grib/format/grib1/centre/0/
    'typeOfLevel': 'surface',
}


def regular_ll_params(values, min_value=-180., max_value=360.):
    # type: (T.Sequence, float, float) -> T.Tuple[float, float, int]
    start, stop, num = float(values[0]), float(values[-1]), len(values)
    if min(start, stop) < min_value or max(start, stop) > max_value:
        raise ValueError("Unsupported spatial grid: out of bounds (%r, %r)" % (start, stop))
    check_values = np.linspace(start, stop, num)
    if not np.allclose(check_values, values):
        raise ValueError("Unsupported spatial grid: not regular %r" % (check_values,))
    return (start, stop, num)


def detect_regular_ll_grib_keys(lon, lat):
    # type: (np.ndarray, np.ndarray) -> T.Dict[bytes, T.Any]
    grib_keys = {}  # type: T.Dict[bytes, T.Any]

    lon_start, lon_stop, lon_num = regular_ll_params(lon)
    lon_scan_negatively = lon_stop < lon_start
    lon_step = abs(lon_stop - lon_start) / (lon_num - 1.)
    if lon_start < 0.:
        lon_start += 360.
    if lon_stop < 0.:
        lon_stop += 360.
    grib_keys['longitudeOfFirstGridPointInDegrees'] = lon_start
    grib_keys['longitudeOfLastGridPointInDegrees'] = lon_stop
    grib_keys['Ni'] = lon_num
    grib_keys['iDirectionIncrementInDegrees'] = lon_step
    grib_keys['iScansNegatively'] = lon_scan_negatively

    lat_start, lat_stop, lat_num = regular_ll_params(lat, min_value=-90., max_value=90.)
    grib_keys['latitudeOfFirstGridPointInDegrees'] = lat_start
    grib_keys['latitudeOfLastGridPointInDegrees'] = lat_stop
    grib_keys['Nj'] = lat_num
    grib_keys['jDirectionIncrementInDegrees'] = abs(lat_stop - lat_start) / (lat_num - 1.)
    grib_keys['jScansPositively'] = lat_stop > lat_start
    grib_keys['gridType'] = 'regular_ll'

    return grib_keys


def detect_grib_keys(data_var, default_grib_keys):
    # type: (xr.DataArray, dict) -> T.Tuple[dict, dict]
    detected_grib_keys = {}
    suggested_grib_keys = default_grib_keys.copy()

    if 'latitude' in data_var.dims and 'longitude' in data_var.dims:
        regular_ll_grib_keys = detect_regular_ll_grib_keys(data_var.longitude, data_var.latitude)
        detected_grib_keys.update(regular_ll_grib_keys)

    if 'air_pressure' in data_var.dims or 'air_pressure' in data_var.coords:
        detected_grib_keys['typeOfLevel'] = 'isobaricInhPa'

    if 'GRIB_typeOflevel' in data_var.attrs:
        suggested_grib_keys['typeOflevel'] = data_var.attrs['GRIB_typeOflevel']

    if 'number' in data_var.dims or 'number' in data_var.coords:
        # cannot set 'number' key without setting a productDefinitionTemplateNumber in GRIB2
        detected_grib_keys['productDefinitionTemplateNumber'] = 1

    if 'shortName' in data_var.attrs:
        detected_grib_keys['shortName'] = data_var.attrs['shortName']

    if 'GRIB_shortName' in data_var.attrs:
        suggested_grib_keys['shortName'] = data_var.attrs['GRIB_shortName']
    elif data_var.name:
        suggested_grib_keys['shortName'] = data_var.name

    return detected_grib_keys, suggested_grib_keys


def detect_sample_name(grib_keys):
    # type: (T.Mapping) -> str
    if grib_keys['gridType'] == 'regular_ll':
        geography = 'regular_ll'
    else:
        raise NotImplementedError("Unsupported 'gridType': %r" % grib_keys['gridType'])

    if grib_keys['typeOfLevel'] == 'isobaricInhPa':
        vertical = 'pl'
    elif grib_keys['typeOfLevel'] in ('surface', 'meanSea'):
        vertical = 'sfc'
    else:
        raise NotImplementedError("Unsupported 'typeOfLevel': %r" % grib_keys['typeOfLevel'])

    sample_name = '%s_%s_grib2' % (geography, vertical)
    return sample_name


def merge_grib_keys(grib_keys, detected_grib_keys, default_grib_keys):
    from cfgrib import dataset

    merged_grib_keys = {k: v for k, v in grib_keys.items()}
    dataset.dict_merge(merged_grib_keys, detected_grib_keys)
    for key, value in default_grib_keys.items():
        if key not in merged_grib_keys:
            merged_grib_keys[key] = value
    return merged_grib_keys


def canonical_dataarray_to_grib(
        file, data_var, grib_keys={}, default_grib_keys=DEFAULT_GRIB_KEYS, sample_name=None
):
    # type: (T.BinaryIO, xr.DataArray, T.Mapping[str, T.Any], T.Mapping[str, T.Any], str) -> None
    from cfgrib import cfmessage
    from cfgrib import eccodes
    from cfgrib import dataset

    detected_grib_keys, suggested_grib_keys = detect_grib_keys(data_var, default_grib_keys)
    merged_grib_keys = merge_grib_keys(grib_keys, detected_grib_keys, suggested_grib_keys)

    if 'gridType' not in merged_grib_keys:
        raise ValueError("required grid_key 'gridType' not passed nor auto-detected")

    if sample_name is None:
        sample_name = detect_sample_name(merged_grib_keys)

    header_coords_names = []
    for coord_name in dataset.ALL_HEADER_DIMS:
        if coord_name in set(data_var.coords):
            header_coords_names.append(coord_name)
            if coord_name not in data_var.dims:
                data_var = data_var.expand_dims(coord_name)

    header_coords_values = [data_var.coords[name].values.tolist() for name in header_coords_names]
    for items in itertools.product(*header_coords_values):
        message = cfmessage.CfMessage.from_sample_name(sample_name)
        for key, value in merged_grib_keys.items():
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


def to_grib(dataset, path, mode='wb', **kwargs):
    # validate Dataset keys, DataArray names, and attr keys/values
    _validate_dataset_names(dataset)
    _validate_attrs(dataset)

    with open(path, mode=mode) as file:
        for data_var in dataset.data_vars.values():
            canonical_dataarray_to_grib(file, data_var, **kwargs)
