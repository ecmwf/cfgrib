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
from builtins import bytes, int, float, list, object, str

import collections
import functools
import logging
import pkg_resources
import typing as T  # noqa

import attr
import numpy as np

from . import eccodes
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
GRID_TYPE_KEYS = list(set(k for _, ks in GRID_TYPE_MAP.items() for k in ks))

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
VARIABLE_ATTRIBUTES_DEF = [
    ('paramId', int), ('shortName', bytes, 100), ('units', bytes, 100),
    ('name', bytes, 256), ('cfName', bytes, 100), ('missingValue', int),
]
VARIABLE_ATTRIBUTES_KEYS = [k if isinstance(k, str) else k[0] for k in VARIABLE_ATTRIBUTES_DEF]

HEADER_COORDINATES_MAP = [
    ('number', ['totalNumber']),
    ('dataDate', []),
    ('dataTime', []),
    ('endStep', ['stepUnits', 'stepType']),
    ('topLevel', ['typeOfLevel']),  # NOTE: no support for mixed 'isobaricInPa' / 'isobaricInhPa'.
]
HEADER_COORDINATES_DEF = [(k, int) for k, _ in HEADER_COORDINATES_MAP]
HEADER_COORDINATES_DEF += [(k, bytes, 20) if k=='typeOfLevel' else (k, int) for _, ks in HEADER_COORDINATES_MAP for k in ks]
HEADER_COORDINATES_KEYS = [k if isinstance(k, str) else k[0] for k in HEADER_COORDINATES_DEF]
FIELD_ATTRIBUTES_DEF = list((('gridType', bytes, 20), ('numberOfDataPoints', int)))  # NOTE: .copy() for python2
FIELD_ATTRIBUTES_KEYS = list(k if isinstance(k, str) else k[0] for k in FIELD_ATTRIBUTES_DEF)

GLOBAL_ATTRIBUTES_DEF = [('edition', int), ('centre', bytes, 20), ('centreDescription', bytes, 100)]
GLOBAL_ATTRIBUTES_KEYS = [k if isinstance(k, str) else k[0] for k in GLOBAL_ATTRIBUTES_DEF]

ALL_DEF = GLOBAL_ATTRIBUTES_DEF + VARIABLE_ATTRIBUTES_DEF + FIELD_ATTRIBUTES_DEF + \
          HEADER_COORDINATES_DEF + [(k, float) for k in GRID_TYPE_KEYS]
ALL_KEYS = [k if isinstance(k, str) else k[0] for k in ALL_DEF]


class AbstractCoordinateVariable(object):
    pass


class CoordinateNotFound(Exception):
    pass


def enforce_unique_attributes(
        index,  # type: messages.Index
        attributes_keys,  # type: T.Sequence[str]
):
    # type: (...) -> T.Dict[str, T.Any]
    attributes = collections.OrderedDict()  # type: T.Dict[str, T.Any]
    for key in attributes_keys:
        values = index[key]
        if len(values) > 1:
            raise ValueError("multiple values for unique attribute %r: %r" % (key, values))
        if values:
            attributes[key] = values[0]
    return attributes


@attr.attrs()
class HeaderCoordinateVariable(AbstractCoordinateVariable):
    index = attr.attrib()
    coordinate_key = attr.attrib(type=str)
    attributes_keys = attr.attrib(default=(), type=T.List[str])
    name = attr.attrib(default=None, type=str)

    def __attrs_post_init__(self):
        values = self.index[self.coordinate_key]
        if len(values) == 1 and values[0] == 'undef':
            raise CoordinateNotFound("missing from GRIB stream: %r" % self.coordinate_key)

        self.attributes = enforce_unique_attributes(self.index, self.attributes_keys)
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
    index = attr.attrib()
    name = attr.attrib(default='i', type=str)

    def __attrs_post_init__(self):
        grid_type = self.index['gridType'][0]
        attributes_keys = FIELD_ATTRIBUTES_KEYS.copy()
        attributes_keys.extend(GRID_TYPE_MAP.get(grid_type, []))
        self.attributes = enforce_unique_attributes(self.index, attributes_keys)
        self.data = list(range(self.attributes['numberOfDataPoints']))
        self.size = len(self.data)
        self.dimensions = (self.name,)
        self.shape = (self.size,)


@attr.attrs()
class DataVariable(AbstractCoordinateVariable):
    index = attr.attrib()
    stream = attr.attrib()
    paramId = attr.attrib()
    name = attr.attrib(default=None, type=str)

    @classmethod
    def fromstream(cls, paramId, name=None, *args, **kwargs):
        stream = messages.Stream(*args, **kwargs)
        index = stream.index(ALL_KEYS)
        return cls(index=index, stream=stream, paramId=paramId, name=name)

    def __attrs_post_init__(self, log=LOG):
        if self.name is None:
            self.name = 'paramId_%s' % self.paramId
            for paramId, shortName in zip(self.index['paramId'], self.index['shortName']):
                if paramId == self.paramId:
                    self.name = shortName

        self.attributes = enforce_unique_attributes(self.index, VARIABLE_ATTRIBUTES_KEYS)
        self.coordinates = collections.OrderedDict()
        for coord_key, attrs_keys in HEADER_COORDINATES_MAP:
            try:
                self.coordinates[coord_key] = HeaderCoordinateVariable(
                    self.index, coordinate_key=coord_key, attributes_keys=attrs_keys,
                )
            except CoordinateNotFound:
                log.exception("coordinate %r failed", coord_key)

        # FIXME: move to a function
        self.coordinates['i'] = SpatialCoordinateVariable(self.index)
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
        for message in self.stream:
            if message.message_get('paramId', eccodes.CODES_TYPE_LONG) != self.paramId:
                continue
            header_indexes = []  # type: T.List[int]
            header_values = []
            for dim in self.dimensions[:-1]:
                header_values.append(message.message_get(dim, eccodes.CODES_TYPE_LONG))
                header_indexes.append(self.coordinates[dim].data.index(header_values[-1]))
            # NOTE: fill a single field as found in the message
            values = message.message_get('values', eccodes.CODES_TYPE_DOUBLE)
            data.__setitem__(tuple(header_indexes + [slice(None, None)]), values)
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


def build_dataset_components(stream, py_index=False, global_attributes_keys=GLOBAL_ATTRIBUTES_KEYS):
    if py_index:
        index = stream.py_index(ALL_KEYS)
    else:
        index = stream.index(ALL_KEYS)
    param_ids = index['paramId']
    dimensions = collections.OrderedDict()
    variables = collections.OrderedDict()
    for param_id in param_ids:
        data_variable = DataVariable(index=index, stream=stream, paramId=param_id)
        vars = collections.OrderedDict([(data_variable.name, data_variable)])
        vars.update(data_variable.coordinates)
        dims = collections.OrderedDict()
        for dim in data_variable.dimensions:
            dims[dim] = vars[dim].size
        dict_merge(dimensions, dims)
        dict_merge(variables, vars)
    attributes = enforce_unique_attributes(index, global_attributes_keys)
    attributes['eccodesGribVersion'] = VERSION
    return dimensions, variables, attributes


@attr.attrs()
class Dataset(object):
    stream = attr.attrib()
    py_index = attr.attrib(default=False)

    @classmethod
    def fromstream(cls, path, py_index=False, **kwagrs):
        return cls(stream=messages.Stream(path, **kwagrs), py_index=py_index)

    def __attrs_post_init__(self):
        dimensions, variables, attributes = build_dataset_components(self.stream, self.py_index)
        self.dimensions = dimensions  # type: T.Dict[str, T.Optional[int]]
        self.variables = variables  # type: T.Dict[str, AbstractCoordinateVariable]
        self.attributes = attributes  # type: T.Dict[str, T.Any]
