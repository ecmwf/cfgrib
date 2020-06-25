#
# Copyright 2017-2020 European Centre for Medium-Range Weather Forecasts (ECMWF).
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
#   Baudouin Raoult - ECMWF - https://ecmwf.int
#   Alessandro Amici - B-Open - https://bopen.eu
#

import datetime
import functools
import logging
import typing as T  # noqa

import attr
import numpy as np  # noqa

from . import messages

LOG = logging.getLogger(__name__)

# taken from eccodes stepUnits.table
GRIB_STEP_UNITS_TO_SECONDS = [
    60,
    3600,
    86400,
    None,
    None,
    None,
    None,
    None,
    None,
    None,
    10800,
    21600,
    43200,
    1,
    900,
    1800,
]
DEFAULT_EPOCH = datetime.datetime(1970, 1, 1)


def from_grib_date_time(message, date_key='dataDate', time_key='dataTime', epoch=DEFAULT_EPOCH):
    # type: (T.Mapping, str, str, datetime.datetime) -> int
    """
    Return the number of seconds since the ``epoch`` from the values of the ``message`` keys,
    using datetime.total_seconds().

    :param message: the target GRIB message
    :param date_key: the date key, defaults to "dataDate"
    :param time_key: the time key, defaults to "dataTime"
    :param epoch: the reference datetime
    """
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
    return int((data_datetime - epoch).total_seconds())


def to_grib_date_time(
    message, time_ns, date_key='dataDate', time_key='dataTime', epoch=DEFAULT_EPOCH
):
    # type: (T.MutableMapping, np.datetime64, str, str, datetime.datetime) -> None
    time_s = int(time_ns) * 1e-9
    time = epoch + datetime.timedelta(seconds=time_s)
    datetime_iso = str(time)
    message[date_key] = int(datetime_iso[:10].replace('-', ''))
    message[time_key] = int(datetime_iso[11:16].replace(':', ''))


def from_grib_step(message, step_key='endStep', step_unit_key='stepUnits'):
    # type: (T.Mapping, str, str) -> float
    to_seconds = GRIB_STEP_UNITS_TO_SECONDS[message[step_unit_key]]
    return message[step_key] * to_seconds / 3600.0


def to_grib_step(message, step_ns, step_unit=1, step_key='endStep', step_unit_key='stepUnits'):
    # type: (T.MutableMapping, int, int, str, str) -> None
    # step_seconds = np.timedelta64(step, 's').astype(int)
    step_s = int(step_ns) * 1e-9
    to_seconds = GRIB_STEP_UNITS_TO_SECONDS[step_unit]
    if to_seconds is None:
        raise ValueError("unsupported stepUnit %r" % step_unit)
    message[step_key] = step_s / to_seconds
    message[step_unit_key] = step_unit


def from_grib_month(message, verifying_month_key='verifyingMonth', epoch=DEFAULT_EPOCH):
    date = message[verifying_month_key]
    year = date // 100
    month = date % 100
    data_datetime = datetime.datetime(year, month, 1, 0, 0)
    return int((data_datetime - epoch).total_seconds())


def build_valid_time(time, step):
    # type: (np.ndarray, np.ndarray) -> T.Tuple[T.Tuple[str, ...], np.ndarray]
    """
    Return dimensions and data of the valid_time corresponding to the given ``time`` and ``step``.
    The data is seconds from the same epoch as ``time`` and may have one or two dimensions.

    :param time: given in seconds from an epoch, as returned by ``from_grib_date_time``
    :param step: given in hours, as returned by ``from_grib_step``
    """
    step_s = step * 3600
    if len(time.shape) == 0 and len(step.shape) == 0:
        data = time + step_s
        dims = ()  # type: T.Tuple[str, ...]
    elif len(time.shape) > 0 and len(step.shape) == 0:
        data = time + step_s
        dims = ('time',)
    elif len(time.shape) == 0 and len(step.shape) > 0:
        data = time + step_s
        dims = ('step',)
    else:
        data = time[:, None] + step_s[None, :]
        dims = ('time', 'step')
    return dims, data


COMPUTED_KEYS = {
    'time': (from_grib_date_time, to_grib_date_time),
    'step': (from_grib_step, to_grib_step),
    'valid_time': (
        functools.partial(from_grib_date_time, date_key='validityDate', time_key='validityTime'),
        functools.partial(to_grib_date_time, date_key='validityDate', time_key='validityTime'),
    ),
    'verifying_time': (from_grib_month, None),
    'indexing_time': (
        functools.partial(from_grib_date_time, date_key='indexingDate', time_key='indexingTime'),
        functools.partial(to_grib_date_time, date_key='indexingDate', time_key='indexingTime'),
    ),
}


@attr.attrs()
class CfMessage(messages.ComputedKeysMessage):
    computed_keys = attr.attrib(default=COMPUTED_KEYS)
