import os.path
import typing as T

import numpy as np
import pytest

from cfgrib import cfmessage

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, "era5-levels-members.grib")


def test_from_grib_date_time() -> None:
    message = {"dataDate": 20160706, "dataTime": 1944}
    result = cfmessage.from_grib_date_time(message)

    assert result == 1467834240


def test_to_grib_date_time() -> None:
    message = {}  # type: T.Dict[str, T.Any]
    datetime_ns = np.datetime64("2001-10-11T01:01:00", "ns")

    cfmessage.to_grib_date_time(message, datetime_ns)

    assert message["dataDate"] == 20011011
    assert message["dataTime"] == 101

    # the ends of the datetime64[ns] range are not exactly representable as float seconds
    cfmessage.to_grib_date_time(message, np.datetime64("1700-01-01T00:00", "ns"))

    assert message["dataDate"] == 17000101
    assert message["dataTime"] == 0

    cfmessage.to_grib_date_time(message, np.datetime64("2262-04-11T23:47", "ns"))

    assert message["dataDate"] == 22620411
    assert message["dataTime"] == 2347


def test_from_grib_step() -> None:
    message = {"endStep:int": 1, "stepUnits:int": 1}
    step_seconds = cfmessage.from_grib_step(message)

    assert step_seconds == 1


def test_to_grib_step() -> None:
    message = {}  # type: T.Dict[str, T.Any]
    step_ns = 3600 * 1_000_000_000

    cfmessage.to_grib_step(message, step_ns, step_unit=1)

    assert message["endStep:int"] == 1
    assert message["stepUnits:int"] == 1

    with pytest.raises(ValueError):
        cfmessage.to_grib_step(message, 0, step_unit=3)

    # a step that is not a multiple of the requested unit is an error, not truncated
    with pytest.raises(ValueError):
        cfmessage.to_grib_step(message, 1800 * 1_000_000_000, step_unit=1)

    # a step with a fraction of a second cannot be represented
    with pytest.raises(ValueError):
        cfmessage.to_grib_step(message, 1_000_000_001)


@pytest.mark.parametrize(
    "step_s,expected_step,expected_step_units",
    [
        (0, 0, 1),
        (3600, 1, 1),
        (36 * 3600, 36, 1),
        (1800, 30, 0),
        (900, 15, 0),
        (5400, 90, 0),
        (3602700, 60045, 0),
        (45, 45, 13),
        (3645, 3645, 13),
    ],
)
def test_to_grib_step_sub_hourly(
    step_s: int, expected_step: int, expected_step_units: int
) -> None:
    message = {}  # type: T.Dict[str, T.Any]

    cfmessage.to_grib_step(message, step_s * 1_000_000_000)

    assert message["endStep:int"] == expected_step
    assert message["stepUnits:int"] == expected_step_units
    # ecCodes interprets the step value in the current step units
    assert list(message) == ["stepUnits:int", "endStep:int"]
    assert cfmessage.from_grib_step(message) == step_s / 3600

    message = {}
    cfmessage.to_grib_step(message, np.timedelta64(step_s, "s"))

    assert message["endStep:int"] == expected_step
    assert message["stepUnits:int"] == expected_step_units


def test_CfMessage_step() -> None:
    message = cfmessage.CfMessage.from_sample_name("regular_ll_sfc_grib2")

    message["step"] = 3 * 3600 * 1_000_000_000

    assert message["endStep:int"] == 3
    assert message["stepUnits:int"] == 1
    assert message["step"] == 3.0

    message["step"] = np.timedelta64(90, "m")

    assert message["endStep:int"] == 90
    assert message["stepUnits:int"] == 0
    assert message["stepRange"] == "90m"
    assert message["step"] == 1.5


def test_build_valid_time() -> None:
    forecast_reference_time = np.array(0)
    forecast_period = np.array(0)

    dims, data = cfmessage.build_valid_time(forecast_reference_time, forecast_period)

    assert dims == ()
    assert data.shape == ()

    forecast_reference_time = np.array([0, 31536000])
    forecast_period = np.array(0)

    dims, data = cfmessage.build_valid_time(forecast_reference_time, forecast_period)

    assert dims == ("time",)
    assert data.shape == forecast_reference_time.shape + forecast_period.shape

    forecast_reference_time = np.array(0)
    forecast_period = np.array([0, 12, 24, 36])

    dims, data = cfmessage.build_valid_time(forecast_reference_time, forecast_period)

    assert dims == ("step",)
    assert data.shape == (4,)
    assert np.allclose((data - data[..., :1]) / 3600, forecast_period)

    forecast_reference_time = np.array([0, 31536000])
    forecast_period = np.array([0, 12, 24, 36])

    dims, data = cfmessage.build_valid_time(forecast_reference_time, forecast_period)

    assert dims == ("time", "step")
    assert data.shape == (2, 4)
    assert np.allclose((data - data[..., :1]) / 3600, forecast_period)
