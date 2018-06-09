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
from builtins import list, object, str

import collections
import datetime
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
GLOBAL_ATTRIBUTES_KEYS = ['edition', 'centre', 'centreDescription']

# NOTE: 'dataType' may have multiple values for the same variable, i.e. ['an', 'fc']
VARIABLE_ATTRIBUTES_KEYS = ['paramId', 'shortName', 'units', 'name', 'cfName', 'missingValue']

SPATIAL_COORDINATES_ATTRIBUTES_KEYS = ['gridType', 'numberOfPoints']

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
        'pl',
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
    'reduced_gg': ['N',  'pl'],
    'sh': ['M', 'K', 'J'],
}
GRID_TYPE_KEYS = list(set(k for _, ks in GRID_TYPE_MAP.items() for k in ks))

HEADER_COORDINATES_MAP = [
    ('number', ['totalNumber']),
    ('endStep', ['stepUnits', 'stepType']),
    ('topLevel', ['typeOfLevel']),  # NOTE: no support for mixed 'isobaricInPa' / 'isobaricInhPa'.
]
HEADER_COORDINATES_KEYS = [k for k, _ in HEADER_COORDINATES_MAP]
HEADER_COORDINATES_KEYS += [k for _, ks in HEADER_COORDINATES_MAP for k in ks]

REF_TIME_COORDINATE_KEYS = ['dataDate', 'dataTime']

ALL_KEYS = GLOBAL_ATTRIBUTES_KEYS + VARIABLE_ATTRIBUTES_KEYS + \
    SPATIAL_COORDINATES_ATTRIBUTES_KEYS + GRID_TYPE_KEYS + HEADER_COORDINATES_KEYS + \
    REF_TIME_COORDINATE_KEYS


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


def from_grib_date_time(date, time):
    # type: (int, int) -> int
    """
    Convert the date and time as encoded in a GRIB file in standard numpy-compatible
    datetime64 string.

    :param int date: the content of "dataDate" key
    :param int time: the content of "dataTime" key

    :rtype: str
    """
    # (int, int) -> int
    hour = time // 100
    minute = time % 100
    year = date // 10000
    month = date // 100 % 100
    day = date % 100
    data_datetime = datetime.datetime(year, month, day, hour, minute)
    # Python 2 compatible timestamp implementation without timezone hurdle
    # see: https://docs.python.org/3/library/datetime.html#datetime.datetime.timestamp
    return int((data_datetime - datetime.datetime(1970, 1, 1)).total_seconds())


def data_date_time(index):
    reverse_index = {}
    direct_index = {}
    data = []
    idate = index.index_keys.index('dataDate')
    itime = index.index_keys.index('dataTime')
    for header_values in index.offsets:
        date = header_values[idate]
        time = header_values[itime]
        seconds = from_grib_date_time(date, time)
        if seconds not in data:
            data.append(seconds)
        reverse_index[seconds] = (date, time)
        direct_index[date, time] = seconds
    attributes = {
        'units': 'seconds since 1970-01-01T00:00:00+00:00',
        'calendar': 'proleptic_gregorian',
        'axis': 'T',
        'standard_name': 'forecast_reference_time',
    }
    return data, attributes, reverse_index, direct_index


@attr.attrs(cmp=False)
class Variable(object):
    dimensions = attr.attrib(type=T.Sequence[str])
    data = attr.attrib(type=np.ndarray)
    attributes = attr.attrib(default={}, type=T.Mapping[str, T.Any])

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented
        equal = (self.dimensions, self.attributes) == (other.dimensions, other.attributes)
        return equal and np.array_equal(self.data, other.data)


@attr.attrs()
class DataArray(object):
    path = attr.attrib()
    shape = attr.attrib()
    offsets = attr.attrib(repr=False)
    missing_value = attr.attrib()

    @property
    def data(self):
        if not hasattr(self, '_data'):
            self._data = self.build_array()
        return self._data

    def build_array(self):
        # type: () -> np.ndarray
        data = np.full(self.shape, fill_value=np.nan, dtype='float32')
        with open(self.path) as file:
            for header_indexes, offset in sorted(self.offsets.items(), key=lambda x: x[1]):
                # NOTE: fill a single field as found in the message
                message = messages.Message.fromfile(file, offset=offset[0])
                values = message.message_get('values', eccodes.CODES_TYPE_DOUBLE)
                data.__getitem__(header_indexes).flat[:] = values
        data[data == self.missing_value] = np.nan
        return data

    def __getitem__(self, item):
        return self.data[item]

    @property
    def dtype(self):
        return self.data.dtype


def build_data_var_components(
        path, index, encode_datetime=False, encode_grid_type=False, log=LOG, **kwargs
):
    # FIXME: This function is a monster. It must die... but not today :/
    # BEWARE: The order of the instructions in the function is significant.
    leader = messages.Stream(path=path, **kwargs).first()
    attributes = enforce_unique_attributes(index, VARIABLE_ATTRIBUTES_KEYS)

    spatial_attributes_keys = SPATIAL_COORDINATES_ATTRIBUTES_KEYS[:]
    spatial_attributes_keys.extend(GRID_TYPE_MAP.get(leader['gridType'], []))
    attributes.update(enforce_unique_attributes(index, spatial_attributes_keys))

    coord_vars = collections.OrderedDict()
    for coord_key, attrs_keys in HEADER_COORDINATES_MAP:
        values = index[coord_key]
        if len(values) == 1 and values[0] == 'undef':
            log.info("missing from GRIB stream: %r" % coord_key)
            continue
        attrs = enforce_unique_attributes(index, attrs_keys)
        data = np.array(values)
        dimensions = (coord_key,)
        if len(values) == 1:
            data = data[0]
            dimensions = ()
        coord_vars[coord_key] = Variable(
            dimensions=dimensions, data=data, attributes=attrs,
        )
    if encode_datetime:
        values, attrs, reverse_index, direct_index = data_date_time(index)
        data = np.array(values)
        dimensions = ('ref_time',)
        coord_vars['ref_time'] = Variable(
            dimensions=dimensions, data=data, attributes=attrs,
        )
    else:
        for coord_key in REF_TIME_COORDINATE_KEYS:
            values = index[coord_key]
            if len(values) == 1 and values[0] == 'undef':
                log.info("missing from GRIB stream: %r" % coord_key)
                continue
            data = np.array(values)
            dimensions = (coord_key,)
            if len(values) == 1:
                data = data[0]
                dimensions = ()
            coord_vars[coord_key] = Variable(
                dimensions=dimensions, data=data, attributes=attrs,
            )

    # FIXME: move to a function
    attributes['coordinates'] = ' '.join(coord_vars.keys()) + ' lat lon'
    dimensions = tuple(d for d, c in coord_vars.items() if c.data.size > 1)
    shape = tuple(coord_vars[d].data.size for d in dimensions)
    if encode_grid_type and leader['gridType'] == 'regular_ll':
        spacial_ndim = 2
        dimensions += ('lat', 'lon')
        shape += (leader['Nj'], leader['Ni'],)
        coord_vars['lat'] = Variable(
            dimensions=('lat',), data=np.linspace(-90., 90., leader['Nj']),
            attributes={'units': 'degrees_north'},
        )
        coord_vars['lon'] = Variable(
            dimensions=('lon',), data=np.linspace(0., 360, leader['Ni'], endpoint=False),
            attributes={'units': 'degrees_north'},
        )

    else:
        spacial_ndim = 1
        dimensions += ('i',)
        shape += (leader['numberOfPoints'],)

        # add secondary coordinates
        latitude = leader['latitudes']
        coord_vars['lat'] = Variable(
            dimensions=('i',), data=np.array(latitude), attributes={'units': 'degrees_north'},
        )
        longitude = leader['longitudes']
        coord_vars['lon'] = Variable(
            dimensions=('i',), data=np.array(longitude), attributes={'units': 'degrees_east'},
        )
    offsets = collections.OrderedDict()
    for header_values, offset in index.offsets.items():
        header_indexes = []  # type: T.List[int]
        for dim in dimensions[:-spacial_ndim]:
            if encode_datetime and dim == 'ref_time':
                date = header_values[index.index_keys.index('dataDate')]
                time = header_values[index.index_keys.index('dataTime')]
                header_value = direct_index[date, time]
                header_indexes.append(coord_vars[dim].data.tolist().index(header_value))
            else:
                header_value = header_values[index.index_keys.index(dim)]
                header_indexes.append(coord_vars[dim].data.tolist().index(header_value))
        offsets[tuple(header_indexes)] = offset
    missing_value = attributes.get('missingValue', 9999)
    data = DataArray(
        path=path, shape=shape, offsets=offsets, missing_value=missing_value,
    )
    data_var = Variable(dimensions=dimensions, data=data, attributes=attributes)
    dims = collections.OrderedDict((d, s) for d, s in zip(dimensions, data_var.data.shape))
    return dims, data_var, coord_vars


def dict_merge(master, update):
    for key, value in update.items():
        if key not in master:
            master[key] = value
        elif master[key] == value:
            pass
        else:
            raise ValueError("key present and new value is different: "
                             "key=%r value=%r new_value=%r" % (key, master[key], value))


def build_dataset_components(stream, encode_datetime=False, encode_grid_type=False):
    index = stream.index(ALL_KEYS)
    param_ids = index['paramId']
    dimensions = collections.OrderedDict()
    variables = collections.OrderedDict()
    for param_id, short_name in zip(param_ids, index['shortName']):
        var_index = index.subindex(paramId=param_id)
        dims, data_var, coord_vars = build_data_var_components(
            path=stream.path, index=var_index,
            encode_datetime=encode_datetime, encode_grid_type=encode_grid_type
        )
        vars = collections.OrderedDict([(short_name, data_var)])
        vars.update(coord_vars)
        dict_merge(dimensions, dims)
        dict_merge(variables, vars)
    attributes = enforce_unique_attributes(index, GLOBAL_ATTRIBUTES_KEYS)
    attributes['eccodesGribVersion'] = VERSION
    return dimensions, variables, attributes


@attr.attrs()
class Dataset(object):
    stream = attr.attrib()
    encode_datetime = attr.attrib(default=False)
    encode_grid_type = attr.attrib(default=False)

    @classmethod
    def fromstream(cls, path, encode_datetime=False, encode_grid_type=False, **kwagrs):
        dataset = cls(
            stream=messages.Stream(path, **kwagrs),
            encode_datetime=encode_datetime, encode_grid_type=encode_grid_type,
        )
        return dataset

    def __attrs_post_init__(self):
        dims, vars, attrs = build_dataset_components(
            self.stream, self.encode_datetime, self.encode_grid_type,
        )
        self.dimensions = dims  # type: T.Dict[str, T.Optional[int]]
        self.variables = vars  # type: T.Dict[str, Variable]
        self.attributes = attrs  # type: T.Dict[str, T.Any]
