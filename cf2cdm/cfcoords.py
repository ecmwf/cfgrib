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

from __future__ import absolute_import, division, print_function, unicode_literals

import functools
import typing as T  # noqa

import xarray as xr  # noqa

from . import cfunits


COORD_MODEL = {}  # type: T.Dict[str, T.Dict[str, T.Any]]
COORD_TRANSLATORS = {}  # type: T.Dict[str, T.Callable]


def match_values(match_value_func, mapping):
    # type: (T.Callable[[T.Any], bool], T.Dict[str, T.Any]) -> T.List[str]
    matched_names = []
    for name, value in mapping.items():
        if match_value_func(value):
            matched_names.append(name)
    return matched_names


def coord_translator(
        default_out_name, default_units, is_cf_type, cf_type, data, coord_model=COORD_MODEL
):
    # type: (str, str, T.Callable, str, xr.DataArray, dict) -> xr.DataArray
    out_name = coord_model.get(cf_type, {}).get('out_name', default_out_name)
    units = coord_model.get(cf_type, {}).get('units', default_units)
    matches = match_values(is_cf_type, data.coords)
    if len(matches) > 1:
        raise ValueError("found more than one CF coordinate with type %r." % cf_type)
    if not matches:
        return data
    match = matches[0]
    for name in data.coords:
        if name == out_name and name != match:
            raise ValueError("found non CF compliant coordinate with type %r." % cf_type)
    data = data.rename({match: out_name})
    coord = data.coords[out_name]
    if 'units' in coord.attrs:
        data.coords[out_name] = cfunits.convert_units(coord, units, coord.attrs['units'])
        data.coords[out_name].attrs['untis'] = units
    return data


VALID_LAT_UNITS = ['degrees_north', 'degree_north', 'degree_N', 'degrees_N', 'degreeN', 'degreesN']


def is_latitude(coord):
    # type: (xr.Coordinate) -> bool
    return coord.attrs.get('units') in VALID_LAT_UNITS


COORD_TRANSLATORS['latitude'] = functools.partial(
    coord_translator, 'latitude', 'degrees_north', is_latitude,
)


VALID_LON_UNITS = ['degrees_east', 'degree_east', 'degree_E', 'degrees_E', 'degreeE', 'degreesE']


def is_longitude(coord):
    # type: (xr.Coordinate) -> bool
    return coord.attrs.get('units') in VALID_LON_UNITS


COORD_TRANSLATORS['longitude'] = functools.partial(
    coord_translator, 'longitude', 'degrees_east', is_longitude,
)


def is_forecast_reference_time(coord):
    # type: (xr.Coordinate) -> bool
    return coord.attrs.get('standard_name') == 'forecast_reference_time'


TIME_CF_UNITS = 'seconds since 1970-01-01T00:00:00+00:00'


COORD_TRANSLATORS['forecast_reference_time'] = functools.partial(
    coord_translator, 'time', TIME_CF_UNITS, is_forecast_reference_time,
)


def is_forecast_period(coord):
    # type: (xr.Coordinate) -> bool
    return coord.attrs.get('standard_name') == 'forecast_period'


COORD_TRANSLATORS['forecast_period'] = functools.partial(
    coord_translator, 'step', 'h', is_forecast_period,
)


def is_valid_time(coord):
    # type: (xr.Coordinate) -> bool
    if coord.attrs.get('standard_name') == 'time':
        return True
    elif str(coord.dtype) == 'datetime64[ns]' and 'standard_name' not in coord.attrs:
        return True
    return False


COORD_TRANSLATORS['valid_time'] = functools.partial(
    coord_translator, 'valid_time', TIME_CF_UNITS, is_valid_time,
)


def is_vertical_pressure(coord):
    # type: (xr.Coordinate) -> bool
    return cfunits.are_convertible(coord.attrs.get('units', ''), 'Pa')


COORD_TRANSLATORS['vertical_pressure'] = functools.partial(
    coord_translator, 'level', 'hPa', is_vertical_pressure,
)


def is_realization(coord):
    # type: (xr.Coordinate) -> bool
    return coord.attrs.get('standard_name') == 'realization'


COORD_TRANSLATORS['realization'] = functools.partial(
    coord_translator, 'number', '1', is_realization,
)


def translate_coords(data, coord_model=COORD_MODEL, coord_translators=COORD_TRANSLATORS):
    # type: (xr.Dataset, T.Dict, T.Dict) -> xr.Dataset
    for cf_name, translator in coord_translators.items():
        data = translator(cf_name, data, coord_model=coord_model)
    return data


def ensure_valid_time_present(data, valid_time_name='valid_time'):
    # type: (xr.Dataset, str) -> T.Tuple[str, str, str]
    valid_times = match_values(is_valid_time, data.coords)
    times = match_values(is_forecast_reference_time, data.coords)
    steps = match_values(is_forecast_period, data.coords)
    time = step = ''
    if not valid_times:
        if not times:
            raise ValueError("not enough information to ensure a 'valid_time'.")
        valid_time = valid_time_name
        time = times[0]
        if steps:
            step = steps[0]
            data.coords[valid_time] = data.coords[time] + data.coords[step]
        else:
            data.coords[valid_time] = data.coords[time]
        data.coords[valid_time].attrs['standard_name'] = 'time'
    else:
        valid_time = valid_times[0]
    return valid_time, time, step


def ensure_valid_time(data):
    # type: (xr.Dataset) -> xr.Dataset
    valid_time, time, step = ensure_valid_time_present(data)
    if valid_time not in data.dims:
        if data.coords[time].size == data.coords[valid_time].size:
            return data.swap_dims({time: valid_time})
        if data.coords[step].size == data.coords[step].size:
            return data.swap_dims({step: valid_time})
    return data
