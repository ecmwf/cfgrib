
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import xarray as xr

from eccodes_grib import xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_GribDataStore():
    datastore = xarray_store.GribDataStore.fromstream(TEST_DATA, flavour='eccodes')
    expected = {'number': 10, 'dataDate': 2, 'dataTime': 2, 'topLevel': 2, 'i': 7320}
    assert datastore.get_dimensions() == expected


def test_xarray_open_dataset():
    datastore = xarray_store.GribDataStore.fromstream(TEST_DATA, flavour='eccodes')
    res = xr.open_dataset(datastore)

    assert res.attrs['edition'] == 1
    assert res['t'].attrs['gridType'] == 'regular_ll'
    assert res['t'].attrs['units'] == 'K'
    assert res['t'].dims == ('number', 'dataDate', 'dataTime', 'topLevel', 'i')

    assert res['t'].mean() > 0.


def test_xarray_open_dataset_encode_time():
    datastore = xarray_store.GribDataStore.fromstream(
        TEST_DATA, extra_config={'encode_geography': False},
    )
    res = xr.open_dataset(datastore)

    assert res.attrs['edition'] == 1
    assert res['t'].attrs['gridType'] == 'regular_ll'
    assert res['t'].attrs['units'] == 'K'
    assert res['t'].dims == ('number', 'forecast_reference_time', 'topLevel', 'i')

    assert res['t'].mean() > 0.


def test_xarray_open_dataset_encode_time_and_geography():
    datastore = xarray_store.GribDataStore.fromstream(TEST_DATA)
    res = xr.open_dataset(datastore)

    assert res.attrs['edition'] == 1

    var = res['t']
    assert var.attrs['gridType'] == 'regular_ll'
    assert var.attrs['units'] == 'K'
    assert var.dims == ('number', 'forecast_reference_time', 'topLevel', 'latitude', 'longitude')

    assert var.mean() > 0.
