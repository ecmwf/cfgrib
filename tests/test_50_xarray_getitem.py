
import os.path

import numpy as np

from eccodes_grib import xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_all():
    da = xarray_store.open_dataset(TEST_DATA).data_vars['t']

    assert np.allclose(da.mean(), 262.92133)
