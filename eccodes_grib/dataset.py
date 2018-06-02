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
from builtins import object

import functools
import logging
import typing as T  # noqa

import attr
import numpy as np

from . import messages

LOG = logging.getLogger(__name__)


#
# Edition-independent keys in ecCodes namespaces. Documented in:
#   https://software.ecmwf.int/wiki/display/ECC/GRIB%3A+Namespaces
#
PARAMETER_KEYS = {'centre', 'paramId', 'shortName', 'units', 'name'}
TIME_KEYS = {
    'dataDate', 'endStep', 'startStep', 'stepRange', 'stepUnits', 'dataTime', 'validityDate',
    'validityTime', 'stepType',
}
GEOGRAPHY_KEYS = {'gridType'}
VERTICAL_KEYS = {'bottomLevel', 'level', 'pv', 'topLevel', 'typeOfLevel'}

NAMESPACE_KEYS = PARAMETER_KEYS | TIME_KEYS | GEOGRAPHY_KEYS | VERTICAL_KEYS

GRID_TYPE_MAP = {
    'regular_ll': {
        'Ni', 'Nj', 'iDirectionIncrementInDegrees', 'iScansNegatively',
        'jDirectionIncrementInDegrees', 'jPointsAreConsecutive', 'jScansPositively',
        'latitudeOfFirstGridPointInDegrees', 'latitudeOfLastGridPointInDegrees',
        'longitudeOfFirstGridPointInDegrees', 'longitudeOfLastGridPointInDegrees',
    },
    'regular_gg': {
        'Ni', 'Nj', 'iDirectionIncrementInDegrees', 'iScansNegatively',
        'N', 'jPointsAreConsecutive', 'jScansPositively',
        'latitudeOfFirstGridPointInDegrees', 'latitudeOfLastGridPointInDegrees',
        'longitudeOfFirstGridPointInDegrees', 'longitudeOfLastGridPointInDegrees',
    },
}

#
# Other edition-independent keys documented in ecCodes presentations
#
DATA_KEYS = {'numberOfDataPoints', 'packingType'}

#
# Undocumented, apparently edition-independent keys
#
ENSEMBLE_KEYS = {'number'}


EDITION_INDEPENDENT_KEYS = NAMESPACE_KEYS | DATA_KEYS | ENSEMBLE_KEYS


def sniff_significant_keys(
        message,  # type: T.Mapping[str, T.Any]
        ei_keys=EDITION_INDEPENDENT_KEYS,  # type: T.Set[str]
        grid_type_map=GRID_TYPE_MAP,  # type: T.Mapping[str, T.Set[str]]
        log=LOG    # type: logging.Logger
):
    # type: (...) -> T.List[str]
    grid_type = message.get('gridType')
    if grid_type in grid_type_map:
        grid_type_keys = grid_type_map[grid_type]
    else:
        log.warning("unknown gridType %r", grid_type)
        grid_type_keys = set()
    all_significant_keys = ei_keys | grid_type_keys
    return [key for key in all_significant_keys if message.get(key) is not None]


def sniff_coordinates_and_attrs(significant_index):
    coordinates = {}
    attrs = {}
    for key, value in significant_index.items():
        if len(value) > 1:
            coordinates[key] = value
        elif len(value) == 1:
            attrs[key] = value[0]
    return coordinates, attrs


def cached(method):
    # type: (T.Callable) -> T.Callable
    @functools.wraps(method)
    def cached_method(self):
        cache_name = '_' + method.__name__
        if not hasattr(self, cache_name):
            setattr(self, cache_name, method(self))
        return getattr(self, cache_name)
    return cached_method


@attr.attrs()
class Variable(object):
    paramId = attr.attrib()
    dataset = attr.attrib()
    name = attr.attrib(default=None)

    def __attrs_post_init__(self):
        self.paramId_index = self.dataset.stream.index(['paramId'])
        if len(self.paramId_index) > 1:
            raise NotImplementedError("GRIB must have only one variable")
        leader = next(self.paramId_index.select(paramId=self.paramId))
        if self.name is None:
            self.name = leader.get('shortName', 'paramId==%s' % self.paramId)
        self.significant_keys = sniff_significant_keys(leader)
        self.significant_index = messages.Index(self.dataset.path, self.significant_keys)

        self.coordinates, self.attrs = sniff_coordinates_and_attrs(self.significant_index)
        self.dimensions = [name for name, coord in self.coordinates.items() if len(coord) > 1]
        self.ndim = len(self.dimensions)
        self.shape = [len(coord) for coord in self.coordinates.values() if len(coord) > 1]

        # Variable attributes
        self.dtype = np.dtype('float32')
        self.scale = True
        self.mask = False
        self.size = leader['numberOfDataPoints']

    def ncattrs(self):
        return self.attrs.copy()

    @cached
    def build_array(self):
        return np.full(self.shape, fill_value=np.nan, dtype=self.dtype)

    def __getitem__(self, item):
        return self.build_array()[item]


@attr.attrs()
class Dataset(object):
    path = attr.attrib()
    mode = attr.attrib(default='r')

    def __attrs_post_init__(self):
        self.stream = messages.Stream(self.path, mode=self.mode)

    @property
    @cached
    def variables(self):
        index = self.stream.index(['paramId'])
        variables = {}
        for param_id in index['paramId']:
            variable = Variable(paramId=param_id, dataset=self)
            variables[variable.name] = variable
        return variables
