import os.path

import pytest

xr = pytest.importorskip('xarray')  # noqa

from cfgrib import xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


@pytest.mark.parametrize('cache', [True, False])
def test_all(cache):
    da = xarray_store.open_dataset(TEST_DATA, cache=cache).data_vars['t']
    va = da.values[:]

    assert va.shape == (10, 4, 2, 61, 120)

    assert da.mean() == va.mean()


@pytest.mark.parametrize('cache', [True, False])
def test_getitem_int(cache):
    da = xarray_store.open_dataset(TEST_DATA, cache=cache).data_vars['t']
    va = da.values[:]

    assert da.isel(isobaricInhPa=1).values.shape == va[:, :, 1].shape
    assert da.isel(isobaricInhPa=1).mean() == va[:, :, 1].mean()
    assert da.sel(isobaricInhPa=500).mean() == va[:, :, 1].mean()


@pytest.mark.parametrize('cache', [True, False])
def test_getitem_slice(cache):
    da = xarray_store.open_dataset(TEST_DATA, cache=cache).data_vars['t']
    va = da.values[:]

    assert da.isel(number=slice(2, 6)).mean() == va[2:6].mean()
    assert da.isel(number=slice(2, 6, 2)).mean() == va[2:6:2].mean()
    # NOTE: label based indexing in xarray is inclusive of both the start and stop bounds.
    assert da.sel(number=slice(2, 6)).mean() == va[2:7].mean()
    assert da.sel(number=slice(2, 6, 2)).mean() == va[2:7:2].mean()


@pytest.mark.parametrize('cache', [True, False])
def test_getitem_list(cache):
    da = xarray_store.open_dataset(TEST_DATA, cache=cache).data_vars['t']
    va = da.values[:]

    assert da.isel(number=[2, 3, 4, 5]).mean() == va[[2, 3, 4, 5]].mean()
    assert da.isel(number=[4, 3, 2, 5]).mean() == va[[4, 3, 2, 5]].mean()
    assert da.sel(number=[2, 3, 4, 5]).mean() == va[[2, 3, 4, 5]].mean()
    assert da.sel(number=[4, 3, 2, 5]).mean() == va[[4, 3, 2, 5]].mean()


@pytest.mark.parametrize('cache', [True, False])
def test_getitem_latlon(cache):
    da = xarray_store.open_dataset(TEST_DATA, cache=cache).data_vars['t']
    va = da.values[:]

    assert da.isel(latitude=slice(0, 3), longitude=slice(0, 33)).mean() == va[..., :3, :33].mean()
    assert da.sel(latitude=slice(90, 0), longitude=slice(0, 90)).mean() == va[..., :31, :31].mean()
