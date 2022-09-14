import os

import numpy as np
import pytest

xr = pytest.importorskip(
    "xarray", minversion="0.17.1.dev0", reason="required xarray>=0.18"
)  # noqa

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, "regular_ll_sfc.grib")
TEST_DATA_MISSING_VALS = os.path.join(SAMPLE_DATA_FOLDER, "fields_with_missing_values.grib")


def test_plugin() -> None:
    engines = xr.backends.list_engines()
    cfgrib_entrypoint = engines["cfgrib"]
    assert cfgrib_entrypoint.__module__ == "cfgrib.xarray_plugin"


def test_xr_open_dataset_file() -> None:
    expected = {
        "latitude": 37,
        "longitude": 72,
    }

    ds = xr.open_dataset(TEST_DATA, engine="cfgrib")
    assert ds.dims == expected
    assert list(ds.data_vars) == ["skt"]


def test_xr_open_dataset_dict() -> None:
    fieldset = {
        -10: {
            "gridType": "regular_ll",
            "Nx": 2,
            "Ny": 3,
            "distinctLatitudes": [-10.0, 0.0, 10.0],
            "distinctLongitudes": [0.0, 10.0],
            "paramId": 167,
            "shortName": "2t",
            "values": [[1, 2], [3, 4], [5, 6]],
        }
    }

    ds = xr.open_dataset(fieldset, engine="cfgrib")

    assert ds.dims == {"latitude": 3, "longitude": 2}
    assert list(ds.data_vars) == ["2t"]


def test_xr_open_dataset_list() -> None:
    fieldset = [
        {
            "gridType": "regular_ll",
            "Nx": 2,
            "Ny": 3,
            "distinctLatitudes": [-10.0, 0.0, 10.0],
            "distinctLongitudes": [0.0, 10.0],
            "paramId": 167,
            "shortName": "2t",
            "values": [[1, 2], [3, 4], [5, 6]],
        }
    ]

    ds = xr.open_dataset(fieldset, engine="cfgrib")

    assert ds.dims == {"latitude": 3, "longitude": 2}
    assert list(ds.data_vars) == ["2t"]

    ds_empty = xr.open_dataset([], engine="cfgrib")

    assert ds_empty.equals(xr.Dataset())


def test_read() -> None:
    expected = {
        "latitude": 37,
        "longitude": 72,
    }
    import cfgrib.xarray_plugin

    opener = cfgrib.xarray_plugin.CfGribBackend()
    ds = opener.open_dataset(TEST_DATA)
    assert ds.dims == expected
    assert list(ds.data_vars) == ["skt"]


def test_xr_open_dataset_file_missing_vals() -> None:
    ds = xr.open_dataset(TEST_DATA_MISSING_VALS, engine="cfgrib")
    t2 = ds["t2m"]
    assert np.isclose(np.nanmean(t2.values[0, :, :]), 268.375)
    assert np.isclose(np.nanmean(t2.values[1, :, :]), 270.716)
