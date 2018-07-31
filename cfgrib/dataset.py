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
import logging
import pkg_resources
import typing as T  # noqa

import attr
import numpy as np

from . import cfmessage
from . import eccodes
from . import messages

LOG = logging.getLogger(__name__)

#
# Edition-independent keys in ecCodes namespaces. Documented in:
#   https://software.ecmwf.int/wiki/display/ECC/GRIB%3A+Namespaces
#
GLOBAL_ATTRIBUTES_KEYS = ['edition', 'centre', 'centreDescription', 'subCentre']

# NOTE: 'dataType' may have multiple values for the same variable, i.e. ['an', 'fc']
DATA_ATTRIBUTES_KEYS = [
    'paramId', 'shortName', 'units', 'name', 'cfName', 'cfVarName', 'missingValue',
    'totalNumber', 'gridType', 'gridDefinitionDescription', 'numberOfPoints',
    'stepUnits', 'stepType', 'typeOfLevel', 'NV',
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
    'reduced_gg': ['N'],  # FIXME: we don't read 'pl' because messages.Index doesn't support lists
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
    ('time', True),
    ('step', True),
]

ALL_MAPS = [
    HEADER_COORDINATES_MAP, VERTICAL_COORDINATE_MAP, PLEV_COORDINATE_MAP, DATA_TIME_COORDINATE_MAP,
    REF_TIME_COORDINATE_MAP,
]
ALL_HEADER_DIMS = [k for m in ALL_MAPS for k, _ in m]

ALL_KEYS = GLOBAL_ATTRIBUTES_KEYS + DATA_ATTRIBUTES_KEYS + GRID_TYPE_KEYS + ALL_HEADER_DIMS


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
        if values and values[0] not in ('undef', 'unknown'):
            attributes['GRIB_' + key] = values[0]
    return attributes


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
            attributes=cfmessage.COORD_ATTRS['latitude'],
        )
        geo_coord_vars['longitude'] = Variable(
            dimensions=('longitude',), data=np.array(first['distinctLongitudes']),
            attributes=cfmessage.COORD_ATTRS['longitude'],
        )
    elif encode_geography and grid_type in GRID_TYPES_2D_AUX_COORD_VAR:
        geo_dims = ('y', 'x')
        geo_shape = (index.getone('Ny'), index.getone('Nx'))
        geo_coord_vars['latitude'] = Variable(
            dimensions=('y', 'x'), data=np.array(first['latitudes']).reshape(geo_shape),
            attributes=cfmessage.COORD_ATTRS['latitude'],
        )
        geo_coord_vars['longitude'] = Variable(
            dimensions=('y', 'x'), data=np.array(first['longitudes']).reshape(geo_shape),
            attributes=cfmessage.COORD_ATTRS['longitude'],
        )
    else:
        geo_dims = ('i',)
        geo_shape = (index.getone('numberOfPoints'),)
        # add secondary coordinates if ecCodes provides them
        try:
            latitude = first['latitudes']
            geo_coord_vars['latitude'] = Variable(
                dimensions=('i',), data=np.array(latitude),
                attributes=cfmessage.COORD_ATTRS['latitude'],
            )
            longitude = first['longitudes']
            geo_coord_vars['longitude'] = Variable(
                dimensions=('i',), data=np.array(longitude),
                attributes=cfmessage.COORD_ATTRS['longitude'],
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
        dims = ('time',)
    elif len(forecast_reference_time.shape) == 0 and len(forecast_period.shape) > 0:
        data = forecast_reference_time + forecast_period
        dims = ('step',)
    else:
        data = forecast_reference_time[:, None] + forecast_period[None, :]
        dims = ('time', 'step')
    attrs = cfmessage.COORD_ATTRS['valid_time']
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
        if data_var_attrs.get('GRIB_cfName'):
            data_var_attrs['standard_name'] = data_var_attrs['GRIB_cfName']
        data_var_attrs['long_name'] = data_var_attrs['GRIB_name']
        data_var_attrs['units'] = data_var_attrs['GRIB_units']

    coords_map = HEADER_COORDINATES_MAP[:]
    if encode_time:
        coords_map.extend(REF_TIME_COORDINATE_MAP)
    else:
        coords_map.extend(DATA_TIME_COORDINATE_MAP)
    if encode_vertical and data_var_attrs['GRIB_typeOfLevel'] in ('isobaricInhPa', 'isobaricInPa'):
        coords_map.extend(PLEV_COORDINATE_MAP)
    else:
        coords_map.extend(VERTICAL_COORDINATE_MAP)
    coord_vars = collections.OrderedDict()
    for coord_key, increasing in coords_map:
        values = sorted(index[coord_key], reverse=not increasing)
        if len(values) == 1 and values[0] == 'undef':
            log.info("missing from GRIB stream: %r" % coord_key)
            continue
        attributes = cfmessage.COORD_ATTRS.get(coord_key, {}).copy()
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
            coord_vars['time'].data, coord_vars['step'].data,
        )
        coord_vars['valid_time'] = Variable(dimensions=dims, data=time_data, attributes=attrs)

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
        filter_by_keys={},
):
    index = stream.index(ALL_KEYS).subindex(filter_by_keys)
    param_ids = index['paramId']
    dimensions = collections.OrderedDict()
    variables = collections.OrderedDict()
    for param_id, short_name, var_name in zip(param_ids, index['shortName'], index['cfVarName']):
        var_index = index.subindex(paramId=param_id)
        dims, data_var, coord_vars = build_data_var_components(
            var_index, encode_parameter, encode_time, encode_geography, encode_vertical,
        )
        if encode_parameter and var_name not in ('undef', 'unknown'):
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
    filter_by_keys = attr.attrib(default={}, type=T.Dict[str, T.Any])

    @classmethod
    def frompath(cls, path, mode='r', errors='ignore', **kwargs):
        stream = messages.Stream(path, mode, message_class=cfmessage.CfMessage, errors=errors)
        return cls(stream=stream, **kwargs)

    def __attrs_post_init__(self):
        dims, vars, attrs = build_dataset_components(**self.__dict__)
        self.dimensions = dims  # type: T.Dict[str, T.Optional[int]]
        self.variables = vars  # type: T.Dict[str, Variable]
        self.attributes = attrs  # type: T.Dict[str, T.Any]
