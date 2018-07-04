
import os.path

import numpy as np

from eccodes_grib import xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_all():
    da = xarray_store.open_dataset(TEST_DATA).data_vars['t']

    assert np.allclose(da.mean(), 262.92133)
    assert np.allclose(da.sel(level=50000).mean(), 252.22284)
    assert np.allclose(da.sel(number=slice(2, 5)).mean(), 262.92184)
    assert np.allclose(da.sel(latitude=slice(90, 40), longitude=slice(0, 33)).mean(), 250.58322)
