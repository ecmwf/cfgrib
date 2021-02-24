import os
from distutils.version import LooseVersion

import pytest

try:
    import xarray as xr

    has_xarray = True
except:
    has_xarray = False

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, "regular_ll_sfc.grib")


@pytest.mark.skipif(
    not (has_xarray and (LooseVersion(xr.__version__) >= "0.18")),
    reason="required xarray >= 0.18",
)
def test_plugin():
    engines = xr.backends.list_engines()
    cfgrib_entrypoint = engines["cfgrib"]
    assert cfgrib_entrypoint.__module__ == "cfgrib.xarray_entrypoint"


@pytest.mark.skipif(
    not has_xarray,
    reason="required xarray",
)
def test_xr_open_dataset():
    expected = {
        "latitude": 37,
        "longitude": 72,
    }

    ds = xr.open_dataset(TEST_DATA, engine="cfgrib")
    assert ds.dims == expected
    assert list(ds.data_vars) == ["skt"]


@pytest.mark.skipif(
    not (has_xarray and (LooseVersion(xr.__version__) >= "0.18")),
    reason="required xarray >= 0.18",
)
def test_read():
    expected = {
        "latitude": 37,
        "longitude": 72,
    }
    import cfgrib.xarray_entrypoint

    opener = cfgrib.xarray_entrypoint.CfgribfBackendEntrypoint()
    ds = opener.open_dataset(TEST_DATA)
    assert ds.dims == expected
    assert list(ds.data_vars) == ["skt"]
