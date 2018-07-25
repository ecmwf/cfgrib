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
from builtins import str  # noqa

import datetime
import logging
import typing as T  # noqa

import attr

from . import messages

LOG = logging.getLogger(__name__)

# taken from eccodes stepUnits.table
GRIB_STEP_UNITS_TO_SECONDS = [
    60, 3600, 86400, None, None, None, None, None, None, None,
    10800, 21600, 43200, 1, 900, 1800,
]

COORD_ATTRS = {
    'time': {
        'units': 'seconds since 1970-01-01T00:00:00+00:00', 'calendar': 'proleptic_gregorian',
        'standard_name': 'forecast_reference_time', 'long_name': 'initial time of forecast',
    },
    'step': {
        'units': 'hours',
        'standard_name': 'forecast_period', 'long_name': 'time since forecast_reference_time',
    },
    'valid_time': {
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
        'units': 'hPa', 'positive': 'down',
        'standard_name': 'air_pressure', 'long_name': 'pressure',
    },
}


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


def to_grib_date_time(message, data_datetime_ns, keys=('dataDate', 'dataTime')):
    # type: (T.MutableMapping, int, T.Tuple[str, str]) -> None
    # np.datetime64(d, 'ns')- np.timedelta64(np.datetime64(d, 'ns').tolist(), 'ns')
    data_datetime_s = int(data_datetime_ns) * 1e-9
    data_datetime = datetime.datetime(1970, 1, 1) + datetime.timedelta(seconds=data_datetime_s)
    datetime_iso = str(data_datetime)
    date_key, time_key = keys
    message[date_key] = int(datetime_iso[:10].replace('-', ''))
    message[time_key] = int(datetime_iso[11:16].replace(':', ''))


def from_grib_step(message, step_key='endStep', step_unit_key='stepUnits'):
    # type: (T.Mapping, str, str) -> float
    to_seconds = GRIB_STEP_UNITS_TO_SECONDS[message[step_unit_key]]
    return message[step_key] * to_seconds / 3600.


def to_grib_step(message, step_ns, step_unit=1, step_key='endStep', step_unit_key='stepUnits'):
    # type: (T.MutableMapping, int, int, str, str) -> None
    # step_seconds = np.timedelta64(step, 's').astype(int)
    step_s = int(step_ns) * 1e-9
    to_seconds = GRIB_STEP_UNITS_TO_SECONDS[step_unit]
    message[step_key] = step_s / to_seconds
    message[step_unit_key] = step_unit


def from_grib_pl_level(message, level_key='topLevel'):
    # type: (T.Mapping, str) -> float
    type_of_level = message['typeOfLevel']
    if type_of_level == 'isobaricInhPa':
        coord = float(message[level_key])
    elif type_of_level == 'isobaricInPa':
        coord = message[level_key] / 100.
    else:
        raise ValueError("Unsupported value of typeOfLevel: %r" % type_of_level)
    return coord


def to_grib_pl_level(message, coord, level_key='topLevel'):
    # type: (T.MutableMapping, float, str) -> None
    # ecCodes accepts floats in hPa and correctly encodes them to int in isobaricInPa if needed
    message['typeOfLevel'] = 'isobaricInhPa'
    message[level_key] = coord


COMPUTED_KEYS = {
    'time': (from_grib_date_time, to_grib_date_time),
    'step': (from_grib_step, to_grib_step),
    'air_pressure': (from_grib_pl_level, to_grib_pl_level),
}


@attr.attrs()
class CfMessage(messages.ComputedKeysMessage):
    computed_keys = attr.attrib(default=COMPUTED_KEYS)
