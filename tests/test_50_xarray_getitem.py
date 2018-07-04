
import os.path

from eccodes_grib import xarray_store

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_all():
    da = xarray_store.open_dataset(TEST_DATA).data_vars['t']
    va = da.values[:]

    assert va.shape == (10, 4, 2, 61, 120)

    assert da.mean() == va.mean()

    assert da.isel(level=1).mean() == va[:, :, 1].mean()
    assert da.sel(level=50000).mean() == va[:, :, 1].mean()

    assert da.isel(number=slice(2, 6)).mean() == va[2:6].mean()
    assert da.isel(number=slice(2, 6, 2)).mean() == va[2:6:2].mean()
    # NOTE:  label based indexing in xarray is inclusive of both the start and stop bounds.
    assert da.sel(number=slice(2, 6)).mean() == va[2:7].mean()
    assert da.sel(number=slice(2, 6, 2)).mean() == va[2:7:2].mean()

    assert da.isel(number=[2, 3, 4, 5]).mean() == va[[2, 3, 4, 5]].mean()
    assert da.isel(number=[4, 3, 2, 5]).mean() == va[[4, 3, 2, 5]].mean()
    assert da.sel(number=[2, 3, 4, 5]).mean() == va[[2, 3, 4, 5]].mean()
    assert da.sel(number=[4, 3, 2, 5]).mean() == va[[4, 3, 2, 5]].mean()

    assert da.isel(latitude=slice(20, 30), longitude=slice(0, 33)).mean() == va[..., 20:30, :33].mean()
    assert da.sel(latitude=slice(90, 0), longitude=slice(0, 180)).mean() == va[..., :31, :61].mean()
