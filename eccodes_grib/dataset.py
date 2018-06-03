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
import itertools
import logging
import pkg_resources
import typing as T  # noqa

import attr
import numpy as np

from . import messages

LOG = logging.getLogger(__name__)
VERSION = pkg_resources.get_distribution("eccodes_grib").version

#
# Edition-independent keys in ecCodes namespaces. Documented in:
#   https://software.ecmwf.int/wiki/display/ECC/GRIB%3A+Namespaces
#
LS_KEYS = ['edition', 'centre', 'centreDescription', 'dataType', 'level']
PARAMETER_KEYS = ['paramId', 'shortName', 'units', 'name', 'cfName']
TIME_KEYS = [
    'dataDate', 'endStep', 'startStep', 'stepRange', 'stepUnits', 'dataTime', 'validityDate',
    'validityTime', 'stepType',
]
GEOGRAPHY_KEYS = ['gridType']
VERTICAL_KEYS = ['bottomLevel', 'pv', 'topLevel', 'typeOfLevel']

NAMESPACE_KEYS = PARAMETER_KEYS + TIME_KEYS + GEOGRAPHY_KEYS + VERTICAL_KEYS

GRID_TYPE_MAP = {
    'regular_ll': [
        'Ni', 'Nj', 'iDirectionIncrementInDegrees', 'iScansNegatively',
        'jDirectionIncrementInDegrees', 'jPointsAreConsecutive', 'jScansPositively',
        'latitudeOfFirstGridPointInDegrees', 'latitudeOfLastGridPointInDegrees',
        'longitudeOfFirstGridPointInDegrees', 'longitudeOfLastGridPointInDegrees',
    ],
    'regular_gg': [
        'Ni', 'Nj', 'iDirectionIncrementInDegrees', 'iScansNegatively',
        'N', 'jPointsAreConsecutive', 'jScansPositively',
        'latitudeOfFirstGridPointInDegrees', 'latitudeOfLastGridPointInDegrees',
        'longitudeOfFirstGridPointInDegrees', 'longitudeOfLastGridPointInDegrees',
    ],
}

#
# Other edition-independent keys documented in ecCodes presentations
#
DATA_KEYS = ['numberOfDataPoints', 'packingType']

#
# Undocumented, apparently edition-independent keys
#
ENSEMBLE_KEYS = ['number', 'totalNumber']

EDITION_INDEPENDENT_KEYS = LS_KEYS + NAMESPACE_KEYS + DATA_KEYS + ENSEMBLE_KEYS


def sniff_significant_keys(
        message,  # type: T.Mapping[str, T.Any]
        ei_keys=EDITION_INDEPENDENT_KEYS,  # type: T.Iterable[str]
        grid_type_map=GRID_TYPE_MAP,  # type: T.Mapping[str, T.Iterable[str]]
        log=LOG,  # type: logging.Logger
):
    # type: (...) -> T.List[str]
    grid_type = message.get('gridType')
    if grid_type in grid_type_map:
        grid_type_keys = grid_type_map[grid_type]
    else:
        log.warning("unknown gridType %r", grid_type)
        grid_type_keys = set()
    all_significant_keys = itertools.chain(ei_keys, grid_type_keys)
    return [key for key in all_significant_keys if message.get(key) is not None]


VARIABLE_ATTRIBUTES_KEYS = ['paramId', 'shortName', 'units', 'name', 'cfName', 'dataType']
COORDINATES_ATTRIBUTES_KEYS = [
    'stepUnits', 'stepType',
    'typeOfLevel',  # NOTE: we don't support mixed 'isobaricInPa' and 'isobaricInhPa', for now.
    'gridType',
    'numberOfDataPoints',
]


def enforce_unique_attributes(
        index,  # type: T.Mapping[str, T.Any]
        attributes_keys,  # type: T.Iterable[str]
):
    # type: (...) -> T.Dict[str, T.Any]
    attributes = {}
    for key in attributes_keys:
        values = index.get(key, [])
        if len(values) > 1:
            raise ValueError("multiple values for unique attribute %r: %r" % (key, values))
        if values and values[0] != 'undef':
            attributes[key] = values[0]
    return attributes


RAW_COORDINATES_KEYS = ['number', 'dataDate', 'dataTime', 'endStep', 'topLevel']


def sniff_raw_coordinates(
        significant_index,  # type: T.Mapping[str, T.Any]
        raw_coordinates_keys=RAW_COORDINATES_KEYS,  # type: T.Iterable[str]
        grid_type_map=GRID_TYPE_MAP,  # type: T.Mapping[str, T.Iterable[str]]
):
    # type: (...) -> T.Dict[str, T.Any]
    raw_coordinates = {}
    for key in raw_coordinates_keys:
        raw_coordinates[key] = significant_index[key]
    raw_coordinates['i'] = list(range(significant_index['numberOfDataPoints'][0]))
    return raw_coordinates


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
class CoordinateVariable(object):
    name = attr.attrib()
    values = attr.attrib()

    @property
    def size(self):
        return len(self.values)


@attr.attrs()
class DataVariable(object):
    stream = attr.attrib()
    paramId = attr.attrib()
    name = attr.attrib(default=None)

    @classmethod
    def fromstream(cls, paramId, name=None, *args, **kwargs):
        return cls(stream=messages.Stream(*args, **kwargs), paramId=paramId, name=name)

    def __attrs_post_init__(self):
        self.paramId_index = self.stream.index(['paramId'])
        if len(self.paramId_index) > 1:
            raise NotImplementedError("GRIB must have only one variable")
        leader = next(self.paramId_index.select(paramId=self.paramId))
        if self.name is None:
            self.name = leader.get('shortName', 'paramId==%s' % self.paramId)
        self.significant_keys = sniff_significant_keys(leader)
        self.significant_index = messages.Index(self.stream.path, self.significant_keys)

        self.attributes = enforce_unique_attributes(self.significant_index, VARIABLE_ATTRIBUTES_KEYS)
        self.coordinates = sniff_raw_coordinates(self.significant_index)
        self.dimensions = [name for name, coord in self.coordinates.items() if len(coord) > 1]
        self.attributes['coordinates'] = ' '.join(k for k, v in self.coordinates.items() if len(v) == 1)

        self.ndim = len(self.dimensions)
        self.shape = [len(coord) for coord in self.coordinates.values() if len(coord) > 1]

        # Variable attributes
        self.dtype = np.dtype('float32')
        self.scale = True
        self.mask = False
        self.size = leader['numberOfDataPoints']

    @cached
    def build_array(self):
        # type: () -> np.ndarray
        return np.full(self.shape, fill_value=np.nan, dtype=self.dtype)

    def __getitem__(self, item):
        return self.build_array()[item]


def dict_merge(master, update):
    for key, value in update.items():
        if key not in master:
            master[key] = value
        elif master[key] == value:
            pass
        else:
            raise ValueError("key present and new value is different: "
                             "key=%r value=%r new_value=%r" % (key, master[key], value))


GLOBAL_ATTRIBUTES_KEYS = ['edition', 'centre', 'centreDescription']


def build_dataset_components(stream, global_attributes_keys=GLOBAL_ATTRIBUTES_KEYS):
    param_ids = stream.index(['paramId'])['paramId']
    dimensions = {}
    variables = {}
    for param_id in param_ids:
        data_variable = DataVariable(stream=stream, paramId=param_id)
        vars = {data_variable.name: data_variable}
        coordinate_variables = {k: CoordinateVariable(name=k, values=v) for k, v in data_variable.coordinates.items()}
        vars.update(coordinate_variables)
        dims = {dim: coordinate_variables[dim].size for dim in data_variable.dimensions}
        dict_merge(dimensions, dims)
        dict_merge(variables, vars)
    index = stream.index(global_attributes_keys)
    attributes = enforce_unique_attributes(index, global_attributes_keys)
    attributes['eccodesGribVersion'] = VERSION
    return dimensions, variables, attributes


@attr.attrs()
class Dataset(object):
    stream = attr.attrib()

    @classmethod
    def fromstream(cls, *args, **kwagrs):
        return cls(stream=messages.Stream(*args, **kwagrs))

    def __attrs_post_init__(self):
        dimensions, variables, attributes = build_dataset_components(self.stream)
        self.dimensions = dimensions  # type: T.Dict[str, T.Optional[int]]
        self.variables = variables  # type: T.Dict[str, T.Union[CoordinateVariable, DataVariable]]
        self.attributes = attributes  # type: T.Dict[str, T.Any]
