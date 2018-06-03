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
from builtins import object, str

import collections
import functools
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
        ei_keys=EDITION_INDEPENDENT_KEYS,  # type: T.List[str]
        grid_type_map=GRID_TYPE_MAP,  # type: T.Mapping[str, T.List[str]]
        log=LOG,  # type: logging.Logger
):
    # type: (...) -> T.List[str]
    grid_type = message.get('gridType')
    if grid_type in grid_type_map:
        grid_type_keys = grid_type_map[grid_type]
    else:
        log.warning("unknown gridType %r", grid_type)
        grid_type_keys = []
    all_significant_keys = ei_keys + grid_type_keys
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
    attributes = collections.OrderedDict()  # type: T.Dict[str, T.Any]
    for key in attributes_keys:
        values = index.get(key, [])
        if len(values) > 1:
            raise ValueError("multiple values for unique attribute %r: %r" % (key, values))
        if values and values[0] != 'undef':
            attributes[key] = values[0]
    return attributes


HEADER_COORDINATES_KEYS = ['number', 'dataDate', 'dataTime', 'endStep', 'topLevel']


def sniff_header_coordinates(
        significant_index,  # type: T.Mapping[str, T.Any]
        header_coordinates_keys=HEADER_COORDINATES_KEYS,  # type: T.Iterable[str]
):
    # type: (...) -> T.Dict[str, T.List[T.Any]]
    header_coordinates = collections.OrderedDict()    # type: T.Dict[str, T.List[T.Any]]
    for key in header_coordinates_keys:
        header_coordinates[key] = significant_index[key]
    return header_coordinates


@attr.attrs()
class CoordinateVariable(object):
    name = attr.attrib(type=str)
    values = attr.attrib(type=T.List[T.Any])

    def __attrs_post_init__(self):
        self.attributes = {}
        if len(self.values) > 1:
            self.dimensions = (self.name,)
            self.data = self.values
            self.shape = (len(self.values))
        else:
            self.dimensions = ()
            self.data = self.values[0]
            self.shape = ()

    @property
    def size(self):
        return len(self.values)


@attr.attrs()
class DataVariable(object):
    stream = attr.attrib()
    paramId = attr.attrib()
    name = attr.attrib(default=None, type=str)

    @classmethod
    def fromstream(cls, paramId, name=None, *args, **kwargs):
        return cls(stream=messages.Stream(*args, **kwargs), paramId=paramId, name=name)

    def __attrs_post_init__(self):
        paramId_index = self.stream.index(['paramId'])
        if len(paramId_index) > 1:
            raise NotImplementedError("GRIB must have only one variable")
        leader = next(paramId_index.select(paramId=self.paramId))
        if self.name is None:
            self.name = leader.get('shortName', 'paramId==%s' % self.paramId)
        self.significant_keys = sniff_significant_keys(leader)
        significant_index = messages.Index(self.stream.path, self.significant_keys)

        self.attributes = enforce_unique_attributes(significant_index, VARIABLE_ATTRIBUTES_KEYS)
        self.coordinates = sniff_header_coordinates(significant_index)
        # FIXME: move to a function
        self.coordinates['i'] = list(range(significant_index['numberOfDataPoints'][0]))
        self.dimensions = tuple(dim for dim, values in self.coordinates.items() if len(values) > 1)
        self.attributes['coordinates'] = ' '.join(self.coordinates.keys())

        self.ndim = len(self.dimensions)
        self.shape = tuple(len(values) for values in self.coordinates.values() if len(values) > 1)

        # Variable attributes
        self.dtype = np.dtype('float32')
        self.scale = True
        self.mask = False
        self.size = functools.reduce(lambda x, y: x * y, self.shape, 1)
        self.data = self.build_array()

    def build_array(self):
        # type: () -> np.ndarray
        data = np.full(self.shape, fill_value=np.nan, dtype=self.dtype)
        for message in self.stream.index(['paramId']).select(paramId=self.paramId):
            header_coordinate_indexes = []  # type: T.List[int]
            for dim in self.dimensions[:-1]:
                header_coordinate_indexes.append(self.coordinates[dim].index(message[dim]))
            # NOTE: fill a single field as found in the message
            data[header_coordinate_indexes] = message['values']
        return data

    def __getitem__(self, item):
        return self.data[item]


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
    dimensions = collections.OrderedDict()
    variables = collections.OrderedDict()
    for param_id in param_ids:
        data_variable = DataVariable(stream=stream, paramId=param_id)
        vars = collections.OrderedDict()
        vars[data_variable.name] = data_variable
        coordinate_variables = collections.OrderedDict()
        for k, v in data_variable.coordinates.items():
            coordinate_variables[k] = CoordinateVariable(name=k, values=v)
        vars.update(coordinate_variables)
        dims = collections.OrderedDict()
        for dim in data_variable.dimensions:
            dims[dim] = coordinate_variables[dim].size
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
