
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import xarray as xr

from eccodes_grib import xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members-one_var.grib')


def test_GribDataStore():
    datastore = xarray_store.GribDataStore.fromstream(TEST_DATA)
    ds = xr.open_dataset(datastore)
    print(ds)
