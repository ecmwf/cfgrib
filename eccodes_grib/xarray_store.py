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

import attr
from xarray import Variable
from xarray.core import indexing
from xarray.core.utils import FrozenOrderedDict
from xarray.backends.common import AbstractDataStore, BackendArray


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


@attr.attrs()
class GribDataStore(AbstractDataStore):
    ds = attr.attrib()

    @classmethod
    def fromstream(cls, *args, **kwargs):
        import eccodes_grib
        return cls(ds=eccodes_grib.Dataset.fromstream(*args, **kwargs))

    def open_store_variable(self, name, var):
        from eccodes_grib import dataset

        if isinstance(var, dataset.DataVariable):
            data = indexing.LazilyOuterIndexedArray(WrapGrib(var.data))
        else:
            data = var.data

        dimensions = var.dimensions
        attrs = var.attributes

        encoding = {}
        # save source so __repr__ can detect if it's local or not
        encoding['source'] = self.ds.stream.path
        encoding['original_shape'] = var.data.shape

        return Variable(dimensions, data, attrs, encoding)

    def get_variables(self):
        return FrozenOrderedDict((k, self.open_store_variable(k, v))
                                 for k, v in self.ds.variables.items())

    def get_attrs(self):
        return FrozenOrderedDict(self.ds.attributes)

    def get_dimensions(self):
        return self.ds.dimensions

    def get_encoding(self):
        encoding = {}
        encoding['unlimited_dims'] = {k for k, v in self.ds.dimensions.items() if v is None}
        return encoding
