import os
from distutils.version import LooseVersion

import pytest
import xarray as xr

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "sample-data")
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, "example.grib")


@pytest.mark.skipif(
    LooseVersion(xr.__version__) < "0.18",
    reason="xarray new backend interface available for xarray version >= 0.18",
)
def test_plugin():
    engines = xr.backends.list_engines()
    cfgrib_entrypoint = engines["cfgrib"]
    assert cfgrib_entrypoint.__module__ == "cfgrib.xarray_entrypoint"


def test_xr_open_dataset():
    expected = {
        "number": 2,
        "time": 3,
        "isobaricInhPa": 2,
        "latitude": 3,
        "longitude": 4,
    }

    ds = xr.open_dataset(TEST_DATA, engine="cfgrib")
    assert ds.dims == expected
    assert list(ds.data_vars) == ["z", "t"]
    assert ds["z"].min() == 12660.0


@pytest.mark.skipif(
    LooseVersion(xr.__version__) < "0.18",
    reason="xarray new backend interface available for xarray version >= 0.18",
)
def test_read():
    expected = {
        "number": 2,
        "time": 3,
        "isobaricInhPa": 2,
        "latitude": 3,
        "longitude": 4,
    }
    import cfgrib.xarray_entrypoint

    opener = cfgrib.xarray_entrypoint.CfgribfBackendEntrypoint()
    ds = opener.open_dataset(TEST_DATA)
    assert ds.dims == expected
    assert list(ds.data_vars) == ["z", "t"]
    assert ds["z"].min() == 12660.0