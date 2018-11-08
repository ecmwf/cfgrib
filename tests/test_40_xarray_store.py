
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest
xr = pytest.importorskip('xarray')  # noqa

from cfgrib import eccodes
from cfgrib import xarray_store


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')
TEST_CORRUPTED = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-corrupted.grib')
TEST_DATASETS = os.path.join(SAMPLE_DATA_FOLDER, 't_on_different_level_types.grib')
TEST_IGNORE = os.path.join(SAMPLE_DATA_FOLDER, 'uv_on_different_levels.grib')


def test_open_dataset():
    res = xarray_store.open_dataset(TEST_DATA)

    assert res.attrs['GRIB_edition'] == 1

    var = res['t']
    assert var.attrs['GRIB_gridType'] == 'regular_ll'
    assert var.attrs['units'] == 'K'
    assert var.dims == \
        ('number', 'time', 'isobaricInhPa', 'latitude', 'longitude')

    assert var.mean() > 0.

    with pytest.warns(FutureWarning):
        xarray_store.open_dataset(TEST_DATA, filter_by_keys={'typeOfLevel': 'isobaricInhPa'})

    with pytest.raises(ValueError):
        xarray_store.open_dataset(TEST_IGNORE)

    res = xarray_store.open_dataset(TEST_IGNORE, backend_kwargs={'errors': 'ignore'})

    assert 'isobaricInhPa' in res.dims


def test_open_dataset_corrupted():
    res = xarray_store.open_dataset(TEST_CORRUPTED)

    assert res.attrs['GRIB_edition'] == 1
    assert len(res.data_vars) == 1

    with pytest.raises(eccodes.EcCodesError):
        xarray_store.open_dataset(TEST_CORRUPTED, backend_kwargs={'grib_errors': 'strict'})


def test_open_dataset_encode_cf_time():
    backend_kwargs = {'encode_cf': ('time',)}
    res = xarray_store.open_dataset(TEST_DATA, backend_kwargs=backend_kwargs)

    assert res.attrs['GRIB_edition'] == 1
    assert res['t'].attrs['GRIB_gridType'] == 'regular_ll'
    assert res['t'].attrs['GRIB_units'] == 'K'
    assert res['t'].dims == ('number', 'time', 'level', 'values')

    assert res['t'].mean() > 0.


def test_open_dataset_encode_cf_vertical():
    backend_kwargs = {'encode_cf': ('vertical',)}
    res = xarray_store.open_dataset(TEST_DATA, backend_kwargs=backend_kwargs)

    var = res['t']
    assert var.dims == ('number', 'dataDate', 'dataTime', 'isobaricInhPa', 'values')

    assert var.mean() > 0.


def test_open_dataset_encode_cf_geography():
    backend_kwargs = {'encode_cf': ('geography',)}
    res = xarray_store.open_dataset(TEST_DATA, backend_kwargs=backend_kwargs)

    assert res.attrs['GRIB_edition'] == 1

    var = res['t']
    assert var.attrs['GRIB_gridType'] == 'regular_ll'
    assert var.attrs['GRIB_units'] == 'K'
    assert var.dims == ('number', 'dataDate', 'dataTime', 'level', 'latitude', 'longitude')

    assert var.mean() > 0.


def test_open_dataset_eccodes():
    res = xarray_store.open_dataset(TEST_DATA)

    assert res.attrs['GRIB_edition'] == 1

    var = res['t']
    assert var.attrs['GRIB_gridType'] == 'regular_ll'
    assert var.attrs['units'] == 'K'
    assert var.dims == ('number', 'time', 'isobaricInhPa', 'latitude', 'longitude')

    assert var.mean() > 0.


def test_open_datasets():
    res = xarray_store.open_datasets(TEST_DATASETS)

    assert len(res) > 1
    assert res[0].attrs['GRIB_edition'] == 1
