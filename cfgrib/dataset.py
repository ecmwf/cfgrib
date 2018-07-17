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
from builtins import list, object, set, str

import collections
import datetime
import functools
import logging
import pkg_resources
import typing as T  # noqa

import attr
import numpy as np

from . import eccodes
from . import messages

LOG = logging.getLogger(__name__)

#
# Edition-independent keys in ecCodes namespaces. Documented in:
#   https://software.ecmwf.int/wiki/display/ECC/GRIB%3A+Namespaces
#
GLOBAL_ATTRIBUTES_KEYS = ['edition', 'centre', 'centreDescription', 'subCentre', 'table2Version']

# NOTE: 'dataType' may have multiple values for the same variable, i.e. ['an', 'fc']
DATA_ATTRIBUTES_KEYS = [
    'paramId', 'shortName', 'units', 'name', 'cfName', 'cfVarName', 'missingValue',
    'totalNumber', 'gridType', 'gridDefinitionDescription', 'numberOfPoints',
    'stepUnits', 'stepType', 'typeOfLevel', 'hybrid_level_count', 'NV',
]

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
    ('number', True),
]
VERTICAL_COORDINATE_MAP = [
    ('topLevel', False),  # NOTE: no support for mixed 'isobaricInPa' / 'isobaricInhPa'.
]
PLEV_COORDINATE_MAP = [
    ('air_pressure', False),  # NOTE: this supports mixed 'isobaricInPa' / 'isobaricInhPa'.
]
DATA_TIME_COORDINATE_MAP = [
    ('dataDate', True),
    ('dataTime', True),
    ('endStep', True),
]
REF_TIME_COORDINATE_MAP = [
    ('forecast_reference_time', True),
    ('forecast_period', True),
]

ALL_MAPS = [
    HEADER_COORDINATES_MAP, VERTICAL_COORDINATE_MAP, PLEV_COORDINATE_MAP, DATA_TIME_COORDINATE_MAP,
    REF_TIME_COORDINATE_MAP,
]


ALL_KEYS = GLOBAL_ATTRIBUTES_KEYS + DATA_ATTRIBUTES_KEYS + GRID_TYPE_KEYS \
           + [k for m in ALL_MAPS for k, _ in m]

# taken from eccodes stepUnits.table
GRIB_STEP_UNITS_TO_SECONDS = [
    60, 3600, 86400, None, None, None, None, None, None, None,
    10800, 21600, 43200, 1, 900, 1800,
]

COORD_ATTRS = {
    'forecast_reference_time': {
        'units': 'seconds since 1970-01-01T00:00:00+00:00', 'calendar': 'proleptic_gregorian',
        'standard_name': 'forecast_reference_time', 'long_name': 'initial time of forecast',
    },
    'forecast_period': {
        'units': 'seconds',
        'standard_name': 'forecast_period', 'long_name': 'time since forecast_reference_time',
    },
    'time': {
        'units': 'seconds since 1970-01-01T00:00:00+00:00', 'calendar': 'proleptic_gregorian',
        'standard_name': 'time', 'long_name': 'time',
    },
    'latitude': {
        'units': 'degrees_north',
        'standard_name': 'latitude', 'long_name': 'latitude',
    },
    'longitude': {
        'units': 'degrees_east',
        'standard_name': 'longitude', 'long_name': 'longitude',
    },
    'air_pressure': {
        'units': 'Pa', 'positive': 'down',
        'standard_name': 'air_pressure', 'long_name': 'pressure',
    },
}


def enforce_unique_attributes(
        index,
        attributes_keys,
):
    # type: (messages.Index, T.Sequence[str]) -> T.Dict[str, T.Any]
    attributes = collections.OrderedDict()  # type: T.Dict[str, T.Any]
    for key in attributes_keys:
        values = index[key]
        if len(values) > 1:
            raise ValueError("multiple values for unique attribute %r: %r" % (key, values))
        if values:
            attributes['GRIB_' + key] = values[0]
    return attributes


def from_grib_date_time(message, keys=('dataDate', 'dataTime')):
    # type: (T.Mapping, str, str) -> int
    """
    Convert the date and time as encoded in a GRIB file in standard numpy-compatible
    datetime64 string.

    :param int date: the content of "dataDate" key
    :param int time: the content of "dataTime" key

    :rtype: str
    """
    date_key, time_key = keys
    date = message[date_key]
    time = message[time_key]
    hour = time // 100
    minute = time % 100
    year = date // 10000
    month = date // 100 % 100
    day = date % 100
    data_datetime = datetime.datetime(year, month, day, hour, minute)
    # Python 2 compatible timestamp implementation without timezone hurdle
    # see: https://docs.python.org/3/library/datetime.html#datetime.datetime.timestamp
    return int((data_datetime - datetime.datetime(1970, 1, 1)).total_seconds())


def from_grib_step(message, step_key='endStep', step_unit_key='stepUnits'):
    # type: (T.Mapping, str, str) -> int
    to_seconds = GRIB_STEP_UNITS_TO_SECONDS[message[step_unit_key]]
    return message[step_key] * to_seconds


def from_grib_pl_level(message, level_key='topLevel'):
    type_of_level = message['typeOfLevel']
    if type_of_level == 'isobaricInhPa':
        coord = message[level_key] * 100.
    elif type_of_level == 'isobaricInPa':
        coord = float(message[level_key])
    else:
        raise ValueError("Unsupported value of typeOfLevel: %r" % type_of_level)
    return coord


COMPUTED_KEYS = {
    'forecast_reference_time': from_grib_date_time,
    'forecast_period': from_grib_step,
    'time': functools.partial(from_grib_date_time, keys=('validityDate', 'validityTime')),
    'air_pressure': from_grib_pl_level,
    'hybrid_level_count': lambda m: (m['NV'] - 2) // 2
}


@attr.attrs()
class CfMessage(messages.ComputedKeysMessage):
    computed_keys = attr.attrib(default=COMPUTED_KEYS)


@attr.attrs(cmp=False)
class Variable(object):
    dimensions = attr.attrib(type=T.Sequence[str])
    data = attr.attrib(type=np.ndarray)
    attributes = attr.attrib(default={}, type=T.Mapping[str, T.Any], repr=False)

    def __eq__(self, other):
        if other.__class__ is not self.__class__:
            return NotImplemented
        equal = (self.dimensions, self.attributes) == (other.dimensions, other.attributes)
        return equal and np.array_equal(self.data, other.data)


def expand_item(item, shape):
    expanded_item = []
    for i, size in zip(item, shape):
        if isinstance(i, list):
            expanded_item.append(i)
        elif isinstance(i, np.ndarray):
            expanded_item.append(i.tolist())
        elif isinstance(i, slice):
            expanded_item.append(list(range(i.start or 0, i.stop or size, i.step or 1)))
        elif isinstance(i, int):
            expanded_item.append([i])
        else:
            TypeError("Unsupported index type %r" % type(i))
    return tuple(expanded_item)


@attr.attrs()
class OnDiskArray(object):
    stream = attr.attrib()
    shape = attr.attrib()
    offsets = attr.attrib(repr=False)
    missing_value = attr.attrib()
    geo_ndim = attr.attrib(default=1, repr=False)

    @property
    def array(self):
        if not hasattr(self, '_array'):
            self._array = self.build_array()
        return self._array

    def build_array(self):
        # type: () -> np.ndarray
        array = np.full(self.shape, fill_value=np.nan, dtype='float32')
        with open(self.stream.path) as file:
            for header_indexes, offset in self.offsets.items():
                # NOTE: fill a single field as found in the message
                message = self.stream.message_class.fromfile(file, offset=offset[0])
                values = message.message_get('values', eccodes.CODES_TYPE_DOUBLE)
                array.__getitem__(header_indexes).flat[:] = values
        array[array == self.missing_value] = np.nan
        return array

    def __getitem__(self, item):
        assert isinstance(item, tuple), "Item type must be tuple not %r" % type(item)
        assert len(item) == len(self.shape), "Item len must be %r not %r" % (self.shape, len(item))

        header_item = expand_item(item[:-self.geo_ndim], self.shape)
        array_field_shape = tuple(len(l) for l in header_item) + self.shape[-self.geo_ndim:]
        array_field = np.full(array_field_shape, fill_value=np.nan, dtype='float32')
        with open(self.stream.path) as file:
            for header_indexes, offset in self.offsets.items():
                try:
                    array_field_indexes = []
                    for it, ix in zip(header_item, header_indexes):
                        array_field_indexes.append(it.index(ix))
                except ValueError:
                    continue
                # NOTE: fill a single field as found in the message
                message = self.stream.message_class.fromfile(file, offset=offset[0])
                values = message.message_get('values', eccodes.CODES_TYPE_DOUBLE)
                array_field.__getitem__(tuple(array_field_indexes)).flat[:] = values

        array = array_field[(Ellipsis,) + item[-self.geo_ndim:]]
        array[array == self.missing_value] = np.nan
        for i, it in reversed(list(enumerate(item[:-self.geo_ndim]))):
            if isinstance(it, int):
                array = array[(slice(None, None, None),) * i + (0,)]
        return array

    @property
    def dtype(self):
        return self.array.dtype


GRID_TYPES_COORD_VAR = ('regular_ll', 'regular_gg')
GRID_TYPES_2D_AUX_COORD_VAR = ('lambert', 'albers', 'polar_stereographic')


def build_geography_coordinates(index, encode_geography, log=LOG):
    # type: (messages.Index, bool) -> T.Tuple[T.Tuple[str], T.Tuple[int], T.Dict]
    first = index.first()
    geo_coord_vars = collections.OrderedDict()
    grid_type = index.getone('gridType')
    if encode_geography and grid_type in GRID_TYPES_COORD_VAR:
        geo_dims = ('latitude', 'longitude')
        geo_shape = (index.getone('Nj'), index.getone('Ni'))
        geo_coord_vars['latitude'] = Variable(
            dimensions=('latitude',), data=np.array(first['distinctLatitudes']),
            attributes=COORD_ATTRS['latitude'],
        )
        geo_coord_vars['longitude'] = Variable(
            dimensions=('longitude',), data=np.array(first['distinctLongitudes']),
            attributes=COORD_ATTRS['longitude'],
        )
    elif encode_geography and grid_type in GRID_TYPES_2D_AUX_COORD_VAR:
        geo_dims = ('y', 'x')
        geo_shape = (index.getone('Ny'), index.getone('Nx'))
        geo_coord_vars['latitude'] = Variable(
            dimensions=('y', 'x'), data=np.array(first['latitudes']).reshape(geo_shape),
            attributes=COORD_ATTRS['latitude'],
        )
        geo_coord_vars['longitude'] = Variable(
            dimensions=('y', 'x'), data=np.array(first['longitudes']).reshape(geo_shape),
            attributes=COORD_ATTRS['longitude'],
        )
    else:
        geo_dims = ('i',)
        geo_shape = (index.getone('numberOfPoints'),)
        # add secondary coordinates if ecCodes provides them
        try:
            latitude = first['latitudes']
            geo_coord_vars['latitude'] = Variable(
                dimensions=('i',), data=np.array(latitude), attributes=COORD_ATTRS['latitude'],
            )
            longitude = first['longitudes']
            geo_coord_vars['longitude'] = Variable(
                dimensions=('i',), data=np.array(longitude), attributes=COORD_ATTRS['longitude'],
            )
        except KeyError:
            log.warning('No latitudes/longitudes provided by ecCodes for gridType = %r', grid_type)
    return geo_dims, geo_shape, geo_coord_vars


def build_valid_time(forecast_reference_time, forecast_period):
    if len(forecast_reference_time.shape) == 0 and len(forecast_period.shape) == 0:
        data = forecast_reference_time + forecast_period
        dims = ()
    elif len(forecast_reference_time.shape) > 0 and len(forecast_period.shape) == 0:
        data = forecast_reference_time + forecast_period
        dims = ('forecast_reference_time',)
    elif len(forecast_reference_time.shape) == 0 and len(forecast_period.shape) > 0:
        data = forecast_reference_time + forecast_period
        dims = ('forecast_period',)
    else:
        data = forecast_reference_time[:, None] + forecast_period[None, :]
        dims = ('forecast_reference_time', 'forecast_period')
    attrs = COORD_ATTRS['time']
    return dims, data, attrs


def build_data_var_components(
        index,
        encode_parameter=False, encode_time=False, encode_geography=False, encode_vertical=False,
        log=LOG,
):
    data_var_attrs_keys = DATA_ATTRIBUTES_KEYS[:]
    data_var_attrs_keys.extend(GRID_TYPE_MAP.get(index.getone('gridType'), []))
    data_var_attrs = enforce_unique_attributes(index, data_var_attrs_keys)
    if encode_parameter:
        data_var_attrs['standard_name'] = data_var_attrs.get('GRIB_cfName', 'undef')
        data_var_attrs['long_name'] = data_var_attrs.get('GRIB_name', 'undef')
        data_var_attrs['units'] = data_var_attrs.get('GRIB_units', 'undef')

    coords_map = HEADER_COORDINATES_MAP[:]
    if encode_time:
        coords_map.extend(REF_TIME_COORDINATE_MAP)
    else:
        coords_map.extend(DATA_TIME_COORDINATE_MAP)
    if encode_vertical and data_var_attrs['GRIB_typeOfLevel'] == 'isobaricInhPa':
        coords_map.extend(PLEV_COORDINATE_MAP)
    else:
        coords_map.extend(VERTICAL_COORDINATE_MAP)
    coord_vars = collections.OrderedDict()
    for coord_key, increasing in coords_map:
        values = sorted(index[coord_key], reverse=not increasing)
        if len(values) == 1 and values[0] == 'undef':
            log.info("missing from GRIB stream: %r" % coord_key)
            continue
        attributes = COORD_ATTRS.get(coord_key, {}).copy()
        data = np.array(values)
        dimensions = (coord_key,)
        if len(values) == 1:
            data = data[0]
            dimensions = ()
        coord_vars[coord_key] = Variable(dimensions=dimensions, data=data, attributes=attributes)

    header_dimensions = tuple(d for d, c in coord_vars.items() if c.data.size > 1)
    header_shape = tuple(coord_vars[d].data.size for d in header_dimensions)

    geo_dims, geo_shape, geo_coord_vars = build_geography_coordinates(index, encode_geography)
    dimensions = header_dimensions + geo_dims
    shape = header_shape + geo_shape
    coord_vars.update(geo_coord_vars)

    offsets = collections.OrderedDict()
    for header_values, offset in index.offsets.items():
        header_indexes = []  # type: T.List[int]
        for dim in header_dimensions:
            header_value = header_values[index.index_keys.index(dim)]
            header_indexes.append(coord_vars[dim].data.tolist().index(header_value))
        offsets[tuple(header_indexes)] = offset
    missing_value = data_var_attrs.get('missingValue', 9999)
    data = OnDiskArray(
        stream=index.stream, shape=shape, offsets=offsets, missing_value=missing_value,
        geo_ndim=len(geo_dims),
    )

    if encode_time:
        # add the valid 'time' secondary coordinate
        dims, time_data, attrs = build_valid_time(
            coord_vars['forecast_reference_time'].data, coord_vars['forecast_period'].data,
        )
        coord_vars['time'] = Variable(dimensions=dims, data=time_data, attributes=attrs)

    data_var_attrs['coordinates'] = ' '.join(coord_vars.keys())
    data_var = Variable(dimensions=dimensions, data=data, attributes=data_var_attrs)
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


def build_dataset_components(
        stream,
        encode_parameter=False, encode_time=False, encode_vertical=False, encode_geography=False,
):
    index = stream.index(ALL_KEYS)
    param_ids = index['paramId']
    dimensions = collections.OrderedDict()
    variables = collections.OrderedDict()
    for param_id, short_name, var_name in zip(param_ids, index['shortName'], index['cfVarName']):
        var_index = index.subindex(paramId=param_id)
        dims, data_var, coord_vars = build_data_var_components(
            var_index, encode_parameter, encode_time, encode_geography, encode_vertical,
        )
        if encode_parameter and var_name != 'undef':
            short_name = var_name
        vars = collections.OrderedDict([(short_name, data_var)])
        vars.update(coord_vars)
        dict_merge(dimensions, dims)
        dict_merge(variables, vars)
    attributes = enforce_unique_attributes(index, GLOBAL_ATTRIBUTES_KEYS)
    cfgrib_ver = pkg_resources.get_distribution("cfgrib").version
    eccodes_ver = eccodes.codes_get_api_version()
    attributes['history'] = 'GRIB to CDM+CF via cfgrib-%s/ecCodes-%s' % (cfgrib_ver, eccodes_ver)
    return dimensions, variables, attributes


@attr.attrs()
class Dataset(object):
    stream = attr.attrib()
    encode_parameter = attr.attrib(default=True)
    encode_time = attr.attrib(default=True)
    encode_vertical = attr.attrib(default=True)
    encode_geography = attr.attrib(default=True)

    @classmethod
    def frompath(cls, path, mode='r', **kwargs):
        return cls(stream=messages.Stream(path, mode=mode, message_class=CfMessage), **kwargs)

    def __attrs_post_init__(self):
        dims, vars, attrs = build_dataset_components(**self.__dict__)
        self.dimensions = dims  # type: T.Dict[str, T.Optional[int]]
        self.variables = vars  # type: T.Dict[str, Variable]
        self.attributes = attrs  # type: T.Dict[str, T.Any]
