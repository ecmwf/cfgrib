import os

import pytest

xr = pytest.importorskip(
    "xarray", minversion="0.17.1.dev0", reason="required xarray>=0.18"
)  # noqa

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, "regular_ll_sfc.grib")


def test_plugin() -> None:
    engines = xr.backends.list_engines()
    cfgrib_entrypoint = engines["cfgrib"]
    assert cfgrib_entrypoint.__module__ == "cfgrib.xarray_plugin"


def test_xr_open_dataset() -> None:
    expected = {
        "latitude": 37,
        "longitude": 72,
    }

    ds = xr.open_dataset(TEST_DATA, engine="cfgrib")
    assert ds.dims == expected
    assert list(ds.data_vars) == ["skt"]


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
