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
        'Ni', 'iDirectionIncrementInDegrees', 'iScansNegatively',
        'longitudeOfFirstGridPointInDegrees', 'longitudeOfLastGridPointInDegrees',
        'Nj', 'jDirectionIncrementInDegrees', 'jPointsAreConsecutive', 'jScansPositively',
        'latitudeOfFirstGridPointInDegrees', 'latitudeOfLastGridPointInDegrees',
    ],
    'reduced_ll': [
        'Nj', 'jDirectionIncrementInDegrees', 'jPointsAreConsecutive', 'jScansPositively',
        'latitudeOfFirstGridPointInDegrees', 'latitudeOfLastGridPointInDegrees',
        # FIXME: 'pl' is an array and needs special handling
    ],
    'regular_gg': [
        'Ni', 'iDirectionIncrementInDegrees', 'iScansNegatively',
        'longitudeOfFirstGridPointInDegrees', 'longitudeOfLastGridPointInDegrees',
        'N',
    ],
    'lambert': [
        'LaDInDegrees', 'LoVInDegrees', 'iScansNegatively',
        'jPointsAreConsecutive', 'jScansPositively',
        'latitudeOfFirstGridPointInDegrees', 'latitudeOfSouthernPoleInDegrees',
        'longitudeOfFirstGridPointInDegrees', 'longitudeOfSouthernPoleInDegrees',
        'DyInMetres', 'DxInMetres', 'Latin2InDegrees', 'Latin1InDegrees', 'Ny', 'Nx',
    ],
    'reduced_gg': [
        'N',  # FIXME: 'pl' is an array and needs special handling
    ],
    'sh': ['M', 'K', 'J'],
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

# NOTE: 'dataType' may have multiple values, i.e. ['an', 'fc']
VARIABLE_ATTRIBUTES_KEYS = ['paramId', 'shortName', 'units', 'name', 'cfName', 'missingValue']


def enforce_unique_attributes(
        stream,  # type: messages.Stream
        attributes_keys,  # type: T.Sequence[str]
):
    # type: (...) -> T.Dict[str, T.Any]
    index = stream.index(attributes_keys)
    attributes = collections.OrderedDict()  # type: T.Dict[str, T.Any]
    for key in attributes_keys:
        values = index.get(key, [])
        if len(values) > 1:
            raise ValueError("multiple values for unique attribute %r: %r" % (key, values))
        if values:
            attributes[key] = values[0]
    return attributes


HEADER_COORDINATES_DEF = [
    ('number', ['totalNumber']),
    ('dataDate', []),
    ('dataTime', []),
    ('endStep', ['stepUnits', 'stepType']),
    ('topLevel', ['typeOfLevel']),  # NOTE: no support for mixed 'isobaricInPa' / 'isobaricInhPa'.
]
FIELD_ATTRIBUTES_KEYS = ['gridType', 'numberOfDataPoints']


class AbstractCoordinateVariable(object):
    pass


class CoordinateNotFound(Exception):
    pass


@attr.attrs()
class HeaderCoordinateVariable(AbstractCoordinateVariable):
    stream = attr.attrib()
    coordinate_key = attr.attrib(type=str)
    attributes_keys = attr.attrib(default=(), type=T.List[str])
    name = attr.attrib(default=None, type=str)

    def __attrs_post_init__(self):
        values = self.stream.index([self.coordinate_key])[self.coordinate_key]
        if len(values) == 1 and values[0] == 'undef':
            raise CoordinateNotFound("missing from GRIB stream: %r" % self.coordinate_key)

        self.attributes = enforce_unique_attributes(self.stream, self.attributes_keys)
        if not self.name:
            self.name = self.coordinate_key
        self.size = len(values)
        if self.size > 1:
            self.dimensions = (self.name,)
            self.data = values
            self.shape = (self.size,)
        else:
            self.dimensions = ()
            self.data = values[0]
            self.shape = ()


@attr.attrs()
class SpatialCoordinateVariable(AbstractCoordinateVariable):
    stream = attr.attrib()
    name = attr.attrib(default='i', type=str)

    def __attrs_post_init__(self):
        grid_type = self.stream.first().get('gridType')
        attribute_keys = FIELD_ATTRIBUTES_KEYS.copy()
        attribute_keys.extend(GRID_TYPE_MAP.get(grid_type, []))
        self.attributes = enforce_unique_attributes(self.stream, attribute_keys)
        self.data = list(range(self.attributes['numberOfDataPoints']))
        self.size = len(self.data)
        self.dimensions = (self.name,)
        self.shape = (self.size,)


@attr.attrs()
class DataVariable(AbstractCoordinateVariable):
    stream = attr.attrib()
    paramId = attr.attrib()
    name = attr.attrib(default=None, type=str)

    @classmethod
    def fromstream(cls, paramId, name=None, *args, **kwargs):
        return cls(stream=messages.Stream(*args, **kwargs), paramId=paramId, name=name)

    def __attrs_post_init__(self, log=LOG):
        paramId_index = self.stream.index(['paramId'])
        if len(paramId_index) > 1:
            raise NotImplementedError("GRIB must have only one variable")

        leader = next(paramId_index.select(paramId=self.paramId))
        if self.name is None:
            self.name = leader.get('shortName', 'paramId==%s' % self.paramId)

        self.attributes = enforce_unique_attributes(self.stream, VARIABLE_ATTRIBUTES_KEYS)
        self.coordinates = collections.OrderedDict()
        for coord_key, attrs_keys in HEADER_COORDINATES_DEF:
            try:
                self.coordinates[coord_key] = HeaderCoordinateVariable(
                    stream=self.stream, coordinate_key=coord_key, attributes_keys=attrs_keys,
                )
            except CoordinateNotFound:
                log.exception("coordinate %r failed", coord_key)

        # FIXME: move to a function
        self.coordinates['i'] = SpatialCoordinateVariable(stream=self.stream)
        self.dimensions = tuple(dim for dim, coord in self.coordinates.items() if coord.size > 1)
        self.attributes['coordinates'] = ' '.join(self.coordinates.keys())

        self.ndim = len(self.dimensions)
        self.shape = tuple(coord.size for coord in self.coordinates.values() if coord.size > 1)

        # Variable attributes
        self.dtype = np.dtype('float32')
        self.scale = True
        self.mask = False
        self.size = functools.reduce(lambda x, y: x * y, self.shape, 1)

    @property
    def data(self):
        if not hasattr(self, '_data'):
            self._data = self.build_array()
        return self._data

    def build_array(self):
        # type: () -> np.ndarray
        data = np.full(self.shape, fill_value=np.nan, dtype=self.dtype)
        for message in self.stream.index(['paramId']).select(paramId=self.paramId):
            if self.ndim > 1:
                header_indexes = []  # type: T.List[int]
                for dim in self.dimensions[:-1]:
                    header_indexes.append(self.coordinates[dim].data.index(message[dim]))
                # NOTE: fill a single field as found in the message
                data[header_indexes] = message['values']
            else:
                data[:] = message['values']
        missing_value = self.attributes.get('missingValue', 9999)
        data[data == missing_value] = np.nan
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
        vars = collections.OrderedDict([(data_variable.name, data_variable)])
        vars.update(data_variable.coordinates)
        dims = collections.OrderedDict()
        for dim in data_variable.dimensions:
            dims[dim] = vars[dim].size
        dict_merge(dimensions, dims)
        dict_merge(variables, vars)
    attributes = enforce_unique_attributes(stream, global_attributes_keys)
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
        self.variables = variables  # type: T.Dict[str, AbstractCoordinateVariable]
        self.attributes = attributes  # type: T.Dict[str, T.Any]
