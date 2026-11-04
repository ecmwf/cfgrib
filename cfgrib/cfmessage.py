#
# Copyright 2017-2021 European Centre for Medium-Range Weather Forecasts (ECMWF).
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
import typing as T

import attr
import numpy as np

from . import abc, messages

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
]  # type: T.List[T.Union[int, None]]
DEFAULT_EPOCH = datetime.datetime(1970, 1, 1)


def from_grib_date_time(message, date_key="dataDate", time_key="dataTime", epoch=DEFAULT_EPOCH):
    # type: (abc.Field, str, str, datetime.datetime) -> int
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
    message, time_ns, date_key="dataDate", time_key="dataTime", epoch=DEFAULT_EPOCH
):
    # type: (abc.MutableField, np.datetime64, str, str, datetime.datetime) -> None
    # integer arithmetic: converting the nanoseconds to a float loses the sub-second
    # precision needed to land on the right minute near the ends of the datetime64[ns] range
    time_s = int(time_ns.astype(np.int64)) // 1_000_000_000
    time = epoch + datetime.timedelta(seconds=time_s)
    datetime_iso = str(time)
    message[date_key] = int(datetime_iso[:10].replace("-", ""))
    message[time_key] = int(datetime_iso[11:16].replace(":", ""))


def from_grib_step(message, step_key="endStep:int", step_unit_key="stepUnits:int"):
    # type: (abc.Field, str, str) -> float
    step_unit = message[step_unit_key]
    to_seconds = GRIB_STEP_UNITS_TO_SECONDS[step_unit]
    if to_seconds is None:
        raise ValueError("unsupported stepUnit %r" % step_unit)
    assert isinstance(to_seconds, int)  # mypy misses this
    return int(message[step_key]) * to_seconds / 3600.0


def to_grib_step(
    message, step_ns, step_unit=None, step_key="endStep:int", step_unit_key="stepUnits:int"
):
    # type: (abc.MutableField, T.Union[int, np.timedelta64], T.Optional[int], str, str) -> None
    """
    Set the step keys of the ``message`` from a step given in nanoseconds, as found in
    the ``step`` coordinate of a cfgrib ``xr.Dataset``.

    :param message: the target GRIB message
    :param step_ns: the step in nanoseconds, as an integer or a ``np.timedelta64``
    :param step_unit: the GRIB ``stepUnits`` code to use. By default the coarsest unit
        among hours, minutes and seconds that represents the step exactly is used,
        so sub-hourly steps are not truncated to whole hours.
    :param step_key: the step key, defaults to "endStep:int"
    :param step_unit_key: the step units key, defaults to "stepUnits:int"
    """
    if isinstance(step_ns, np.timedelta64):
        step_ns_int = int(step_ns.astype("timedelta64[ns]").astype(np.int64))
    else:
        step_ns_int = int(step_ns)
    step_s, step_rest_ns = divmod(step_ns_int, 1_000_000_000)
    if step_rest_ns:
        raise ValueError("step %r ns is not a whole number of seconds" % step_ns_int)
    if step_unit is None:
        step_unit = 1 if step_s % 3600 == 0 else 0 if step_s % 60 == 0 else 13
    to_seconds = GRIB_STEP_UNITS_TO_SECONDS[step_unit]
    if to_seconds is None:
        raise ValueError("unsupported stepUnit %r" % step_unit)
    assert isinstance(to_seconds, int)  # mypy misses this
    if step_s % to_seconds:
        raise ValueError("step %r s is not a multiple of stepUnit %r" % (step_s, step_unit))
    # ecCodes interprets the step value in the current step units, so set the units first
    message[step_unit_key] = step_unit
    message[step_key] = step_s // to_seconds


def from_grib_step_units(message):
    # type: (abc.Field) -> float
    # we always index steps in hours
    return 1


def to_grib_step_units(message, step_unit=1, step_unit_key="stepUnits:int"):
    # type: (abc.MutableField, int, str) -> None
    message[step_unit_key] = step_unit


def from_grib_month(message, verifying_month_key="verifyingMonth", epoch=DEFAULT_EPOCH):
    # type: (abc.Field, str, datetime.datetime) -> int
    date = message[verifying_month_key]
    year = date // 100
    month = date % 100
    data_datetime = datetime.datetime(year, month, 1, 0, 0)
    return int((data_datetime - epoch).total_seconds())


def to_grib_dummy(message, value):
    # type: (abc.MutableField, T.Any) -> None
    pass


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
        dims = ("time",)
    elif len(time.shape) == 0 and len(step.shape) > 0:
        data = time + step_s
        dims = ("step",)
    else:
        data = time[:, None] + step_s[None, :]
        dims = ("time", "step")
    return dims, data


COMPUTED_KEYS = {
    "time": (from_grib_date_time, to_grib_date_time),
    "step": (from_grib_step, to_grib_step),
    "endStep": (from_grib_step, to_grib_step),
    "stepUnits": (from_grib_step_units, to_grib_step_units),
    "valid_time": (
        functools.partial(from_grib_date_time, date_key="validityDate", time_key="validityTime"),
        functools.partial(to_grib_date_time, date_key="validityDate", time_key="validityTime"),
    ),
    "verifying_time": (from_grib_month, to_grib_dummy),
    "indexing_time": (
        functools.partial(from_grib_date_time, date_key="indexingDate", time_key="indexingTime"),
        functools.partial(to_grib_date_time, date_key="indexingDate", time_key="indexingTime"),
    ),
    "valid_month": (
        functools.partial(
            from_grib_date_time, date_key="monthlyVerificationDate", time_key="validityTime"
        ),
        functools.partial(
            to_grib_date_time, date_key="monthlyVerificationDate", time_key="validityTime"
        ),
    ),
}  # type: messages.ComputedKeysType


@attr.attrs(auto_attribs=True)
class CfMessage(messages.ComputedKeysMessage):
    computed_keys: messages.ComputedKeysType = COMPUTED_KEYS
