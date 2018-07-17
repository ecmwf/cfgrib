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

import attr
from xarray import Variable
from xarray.core import indexing
from xarray.core.utils import FrozenOrderedDict
from xarray.backends.api import open_dataset as _open_dataset
from xarray.backends.common import AbstractDataStore, BackendArray

import cfgrib


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
        'variable_map': {
            'forecast_reference_time': 'time',
            'forecast_period': 'step',
            'time': 'valid_time',
            'air_pressure': 'level',
            'topLevel': 'level',
        },
        'type_of_level_map': {
            'hybrid': 'L{GRIB_hybrid_level_count}',
        },
    },
    'cds': {
        'variable_map': {
            'number': 'realization',
            'forecast_period': 'leadtime',
            'air_pressure': 'plev',
            'latitude': 'lat',
            'longitude': 'lon',
            'topLevel': 'level',
        },
        'type_of_level_map': {
            'hybrid': 'L{GRIB_hybrid_level_count}',
        },
    },
}


@attr.attrs()
class GribDataStore(AbstractDataStore):
    ds = attr.attrib()
    variable_map = attr.attrib(default={})
    type_of_level_map = attr.attrib(default={})

    @classmethod
    def frompath(cls, path, flavour_name='ecmwf', **kwargs):
        flavour = FLAVOURS[flavour_name].copy()
        config = flavour.pop('dataset', {}).copy()
        config.update(kwargs)
        return cls(ds=cfgrib.Dataset.frompath(path, **config), **flavour)

    def __attrs_post_init__(self):
        self.variable_map = self.variable_map.copy()
        for name, var in self.ds.variables.items():
            if self.ds.encode_vertical and 'GRIB_typeOfLevel' in var.attributes:
                type_of_level = var.attributes['GRIB_typeOfLevel']
                coord_name = self.type_of_level_map.get(type_of_level, type_of_level)
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


def open_dataset(path, flavour_name='ecmwf', **kwargs):
    overrides = {}
    for k in list(kwargs):  # copy to allow the .pop()
        if k.startswith('encode_'):
            overrides[k] = kwargs.pop(k)
    store = GribDataStore.frompath(path, flavour_name=flavour_name, **overrides)
    return _open_dataset(store, **kwargs)


def cfgrib2netcdf():
    import argparse

    parser = argparse.ArgumentParser(description='Convert a GRIB file into a NetCDF file.')
    parser.add_argument('input', help='Path to the input GRIB file.')
    parser.add_argument(
        '--flavour_name', default='cds', help='Translation flavour: "cds", "eccodes" or "ecmwf".'
    )
    parser.add_argument(
        '--output', '-o', default='{input}.nc', help='Path to the output file.'
    )

    args = parser.parse_args()
    print('Loading: %r with flavour %r' % (args.input, args.flavour_name))
    ds = open_dataset(args.input, flavour_name=args.flavour_name)
    outpath = args.output.format(input=args.input)
    print('Creating:', outpath)
    ds.to_netcdf(outpath)
