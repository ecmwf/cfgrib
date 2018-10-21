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
import typing as T

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

DATA_ATTRIBUTES_KEYS = [
    'paramId', 'shortName', 'units', 'name', 'cfName', 'cfVarName',
    'dataType', 'missingValue', 'numberOfPoints',
    'totalNumber',
    'typeOfLevel', 'NV',
    'stepUnits', 'stepType',
    'gridType', 'gridDefinitionDescription',
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
    'reduced_gg': ['N'],  # FIXME: no 'pl' because messages.FileIndex doesn't support lists
    'sh': ['M', 'K', 'J'],
}
GRID_TYPE_KEYS = list(set(k for _, ks in GRID_TYPE_MAP.items() for k in ks))

HEADER_COORDINATES_MAP = [
    ('number', True),
]
VERTICAL_COORDINATE_MAP = [
    ('level', False),
]
PLEV_TYPE_OF_LEVELS = ('isobaricInhPa', 'isobaricInPa')
PLEV_COORDINATE_MAP = [
    ('isobaricInhPa', False),
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

FLAVOURS = {
    'eccodes': {
        'encode_parameter': False,
        'encode_time': False,
        'encode_vertical': False,
        'encode_geography': False,
    },
    'ecmwf': {
        'encode_parameter': True,
        'encode_time': True,
        'encode_vertical': True,
        'encode_geography': True,
    },
}


class DatasetBuildError(ValueError):
    def __str__(self):
        return str(self.args[0])


def enforce_unique_attributes(index, attributes_keys, filter_by_keys={}):
    # type: (messages.FileIndex, T.Sequence[str], dict) -> T.Dict[str, T.Any]
    attributes = collections.OrderedDict()  # type: T.Dict[str, T.Any]
    for key in attributes_keys:
        values = index[key]
        if len(values) > 1:
            error_message = "multiple values for unique key, try re-open the file with one of:"
            fbks = []
            for value in values:
                fbk = {key: value}
                fbk.update(filter_by_keys)
                fbks.append(fbk)
                error_message += "\n    filter_by_keys=%r" % fbk
            raise DatasetBuildError(error_message, fbks)
        if values and values[0] not in ('undef', 'unknown'):
            attributes['GRIB_' + key] = values[0]
    return attributes


@attr.attrs(cmp=False)
class Variable(object):
    dimensions = attr.attrib(type=T.Tuple[str, ...])
    data = attr.attrib(type=np.ndarray)
    attributes = attr.attrib(default={}, type=T.Dict[str, T.Any], repr=False)

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
    shape = attr.attrib(type=T.Tuple[int, ...])
    offsets = attr.attrib(repr=False, type=T.Dict[T.Tuple[T.Any, ...], T.List[int]])
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
                message = self.stream.message_from_file(file, offset=offset[0])
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
                message = self.stream.message_from_file(file, offset=offset[0])
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


def build_geography_coordinates(
        index,  # type: messages.FileIndex
        encode_geography,  # type: bool
        log=LOG,  # type: logging.Logger
):
    # type: (...) -> T.Tuple[T.Tuple[str, ...], T.Tuple[int, ...], T.Dict[str, Variable]]
    first = index.first()
    geo_coord_vars = collections.OrderedDict()  # type: T.Dict[str, Variable]
    grid_type = index.getone('gridType')
    if encode_geography and grid_type in GRID_TYPES_COORD_VAR:
        geo_dims = ('latitude', 'longitude')  # type: T.Tuple[str, ...]
        geo_shape = (index.getone('Nj'), index.getone('Ni'))  # type: T.Tuple[int, ...]
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


def do_encode_first(data_var_attrs, coords_map, encode_parameter, encode_time, encode_vertical):
    if encode_parameter:
        if 'GRIB_cfName' in data_var_attrs:
            data_var_attrs['standard_name'] = data_var_attrs['GRIB_cfName']
        if 'GRIB_name' in data_var_attrs:
            data_var_attrs['long_name'] = data_var_attrs['GRIB_name']
        if 'GRIB_units' in data_var_attrs:
            data_var_attrs['units'] = data_var_attrs['GRIB_units']
    if encode_time:
        coords_map.extend(REF_TIME_COORDINATE_MAP)
    else:
        coords_map.extend(DATA_TIME_COORDINATE_MAP)
    if encode_vertical and data_var_attrs.get('GRIB_typeOfLevel') in PLEV_TYPE_OF_LEVELS:
        coords_map.extend(PLEV_COORDINATE_MAP)
    else:
        coords_map.extend(VERTICAL_COORDINATE_MAP)


def build_data_var_components(
        index,
        encode_parameter=False, encode_time=False, encode_geography=False, encode_vertical=False,
        filter_by_keys={}, log=LOG,
):
    data_var_attrs_keys = DATA_ATTRIBUTES_KEYS[:]
    data_var_attrs_keys.extend(GRID_TYPE_MAP.get(index.getone('gridType'), []))
    data_var_attrs = enforce_unique_attributes(index, data_var_attrs_keys, filter_by_keys)
    coords_map = HEADER_COORDINATES_MAP[:]

    do_encode_first(data_var_attrs, coords_map, encode_parameter, encode_time, encode_vertical)

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
        stream=index.filestream, shape=shape, offsets=offsets, missing_value=missing_value,
        geo_ndim=len(geo_dims),
    )

    if 'time' in coord_vars and encode_time:
        # add the 'valid_time' secondary coordinate
        step_data = coord_vars['step'].data if 'data' in coord_vars else np.array(0.)
        dims, time_data = cfmessage.build_valid_time(
            coord_vars['time'].data, step_data,
        )
        attrs = cfmessage.COORD_ATTRS['valid_time']
        coord_vars['valid_time'] = Variable(dimensions=dims, data=time_data, attributes=attrs)

    if 'level' in coord_vars and encode_vertical and 'GRIB_typeOfLevel' in data_var_attrs:
        type_of_level = data_var_attrs['GRIB_typeOfLevel']
        coord_vars = collections.OrderedDict(
            (type_of_level if k == 'level' else k, v) for k, v in coord_vars.items()
        )
        if 'level' in dimensions:
            dimensions = tuple(type_of_level if d == 'level' else d for d in dimensions)

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
            raise DatasetBuildError("key present and new value is different: "
                                    "key=%r value=%r new_value=%r" % (key, master[key], value))


def build_dataset_components(
        stream,
        encode_parameter=True, encode_time=True, encode_vertical=True, encode_geography=True,
        filter_by_keys={}, log=LOG,
):
    filter_by_keys = dict(filter_by_keys)
    index = stream.index(ALL_KEYS).subindex(filter_by_keys)
    param_ids = index['paramId']
    dimensions = collections.OrderedDict()
    variables = collections.OrderedDict()
    for param_id, short_name, var_name in zip(param_ids, index['shortName'], index['cfVarName']):
        var_index = index.subindex(paramId=param_id)
        dims, data_var, coord_vars = build_data_var_components(
            var_index, encode_parameter, encode_time, encode_geography, encode_vertical,
            filter_by_keys,
        )
        if encode_parameter and var_name not in ('undef', 'unknown'):
            short_name = var_name
        vars = collections.OrderedDict([(short_name, data_var)])
        vars.update(coord_vars)
        try:
            dict_merge(dimensions, dims)
            dict_merge(variables, vars)
        except ValueError:
            log.exception("skipping variable with paramId==%r shortName=%r", param_id, short_name)
    attributes = enforce_unique_attributes(index, GLOBAL_ATTRIBUTES_KEYS, filter_by_keys)
    cfgrib_ver = pkg_resources.get_distribution("cfgrib").version
    eccodes_ver = eccodes.codes_get_api_version()
    encoding = {
        'source': stream.path,
        'filter_by_keys': filter_by_keys,
        'encode_parameter': encode_parameter,
        'encode_time': encode_time,
        'encode_vertical': encode_vertical,
        'encode_geography': encode_geography,
    }
    open_text = ', '.join('%s=%r' % it for it in encoding.items())
    attributes['history'] = 'GRIB to CDM+CF via ' \
        'cfgrib-%s/ecCodes-%s with %s' % (cfgrib_ver, eccodes_ver, open_text)
    return dimensions, variables, attributes, encoding


@attr.attrs()
class Dataset(object):
    """
    Map a GRIB file to the NetCDF Common Data Model with CF Conventions.
    """
    dimensions = attr.attrib(type=T.Dict[str, int])
    variables = attr.attrib(type=T.Dict[str, Variable])
    attributes = attr.attrib(type=T.Dict[str, T.Any])
    encoding = attr.attrib(type=T.Dict[str, T.Any])

    @classmethod
    def from_path(cls, path, mode='r', errors='ignore', flavour_name='ecmwf', **kwargs):
        """Open a GRIB file as a ``Dataset``."""
        flavour_kwargs = FLAVOURS[flavour_name].copy()
        flavour_kwargs.update(kwargs)
        stream = messages.FileStream(path, message_class=cfmessage.CfMessage, errors=errors)
        return cls(*build_dataset_components(stream, **flavour_kwargs))


def open_file(path, **kwargs):
    """Open a GRIB file as a ``cfgrib.Dataset``."""
    return Dataset.from_path(path, **kwargs)
