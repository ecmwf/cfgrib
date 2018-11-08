
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest
xr = pytest.importorskip('xarray')  # noqa

from cfgrib import cfgrib_


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_CfGribDataStore():
    datastore = cfgrib_.CfGribDataStore(TEST_DATA, encode_cf=())
    expected = {'number': 10, 'dataDate': 2, 'dataTime': 2, 'level': 2, 'values': 7320}
    assert datastore.get_dimensions() == expected


def test_xarray_open_dataset():
    datastore = cfgrib_.CfGribDataStore(TEST_DATA, encode_cf=(), lock=cfgrib_.SerializableLock())
    res = xr.open_dataset(datastore)

    assert res.attrs['GRIB_edition'] == 1
    assert res['t'].attrs['GRIB_gridType'] == 'regular_ll'
    assert res['t'].attrs['GRIB_units'] == 'K'
    assert res['t'].dims == ('number', 'dataDate', 'dataTime', 'level', 'values')

    assert res['t'].mean() > 0.
