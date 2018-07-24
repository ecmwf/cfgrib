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
import functools
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
    'forecast_reference_time': (from_grib_date_time, None),
    'forecast_period': (from_grib_step, None),
    'time': (functools.partial(from_grib_date_time, keys=('validityDate', 'validityTime')), None),
    'air_pressure': (from_grib_pl_level, None),
}


@attr.attrs()
class CfMessage(messages.ComputedKeysMessage):
    computed_keys = attr.attrib(default=COMPUTED_KEYS)
