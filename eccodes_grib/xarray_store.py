#
# Copyright 2017-2018 B-Open Solutions srl.
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

from __future__ import absolute_import, division, print_function, unicode_literals

import collections

import attr
from xarray import Variable
from xarray.core import indexing
from xarray.core.utils import FrozenOrderedDict
from xarray.backends.api import open_dataset as _open_dataset
from xarray.backends.common import AbstractDataStore, BackendArray

import eccodes_grib


class WrapGrib(BackendArray):
    def __init__(self, variable):
        self.variable = variable

    def __getitem__(self, item):
        return indexing.NumpyIndexingAdapter(self.variable.data)[item]

    @property
    def shape(self):
        return self.variable.data.shape

    @property
    def dtype(self):
        return self.variable.data.dtype


FLAVOURS = {
    'eccodes': {
        'dataset': {
            'encode_time': False,
            'encode_vertical': False,
            'encode_geography': False,
        }
    },
    'ecmwf': {
        'variable_map': {
            'forecast_reference_time': 'time',
            'forecast_period': 'step',
            'time': 'valid_time',
            'air_pressure': 'level',
        }
    },
    'cds': {
        'variable_map': {
            'number': 'realization',
            'forecast_period': 'leadtime',
            'air_pressure': 'plev',
            'latitude': 'lat',
            'longitude': 'lon',
        }
    },
}


@attr.attrs()
class GribDataStore(AbstractDataStore):
    ds = attr.attrib()
    variable_map = attr.attrib(default={})

    @classmethod
    def fromstream(cls, path, flavour_name='ecmwf', **kwargs):
        flavour = FLAVOURS[flavour_name]
        config = flavour.get('dataset', {}).copy()
        config.update(kwargs)
        variable_map = flavour.get('variable_map', {})
        return cls(ds=eccodes_grib.Dataset.fromstream(path, **config), variable_map=variable_map)

    def open_store_variable(self, name, var):
        if isinstance(var.data, eccodes_grib.dataset.DataArray):
            data = indexing.LazilyOuterIndexedArray(WrapGrib(var.data))
        else:
            data = var.data

        dimensions = tuple(self.variable_map.get(dim, dim) for dim in var.dimensions)
        attrs = var.attributes

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
    store = GribDataStore.fromstream(path, flavour_name=flavour_name, **overrides)
    return _open_dataset(store, **kwargs)


def eccodes_grib2netcdf():
    import argparse

    parser = argparse.ArgumentParser(description='Convert a GRIB file into a NetCDF file.')
    parser.add_argument('input', help='Path to the input GRIB file.')
    parser.add_argument('--flavour_name', default='cds',
        help='Translation flavour. Can be "cds", "eccodes" or "ecmwf".')
    parser.add_argument('--output', '-o', default='{input}.nc',
        help='Path to the output file.')

    args = parser.parse_args()
    print('Loading:', args.input)
    ds = open_dataset(args.input, flavour_name=args.flavour_name)
    outpath = args.output.format(input=args.input)
    print('Creating:', outpath)
    ds.to_netcdf(outpath)
