
import numpy as np
import pytest
import xarray as xr

from cfgrib import xarray_store


@pytest.fixture()
def canonic_dataarray():
    da = xr.DataArray(
        np.arange(20.).reshape((4, 5)),
        coords=[np.linspace(90., -90., 4), np.linspace(0., 360., 5, endpoint=False)],
        dims=['latitude', 'longitude'],
    )
    return da


def test_canonical_dataarray_to_grib_with_grik_keys(canonic_dataarray, tmpdir):
    out_path = tmpdir.join('res.grib')
    grib_keys = {
        'gridType': 'regular_ll',
        'typeOfLevel': 'surface',
    }
    with open(str(out_path), 'wb') as file:
        xarray_store.canonical_dataarray_to_grib(file, canonic_dataarray, grib_keys=grib_keys)


def test_canonical_dataarray_to_grib_detect_grik_keys(canonic_dataarray, tmpdir):
    out_path = tmpdir.join('res.grib')
    with open(str(out_path), 'wb') as file:
        xarray_store.canonical_dataarray_to_grib(file, canonic_dataarray)


def test_canonical_dataarray_to_grib_conflicting_detect_grik_keys(canonic_dataarray, tmpdir):
    out_path = tmpdir.join('res.grib')
    grib_keys = {
        'gridType': 'reduced_ll',
    }
    with open(str(out_path), 'wb') as file:
        with pytest.raises(ValueError):
            xarray_store.canonical_dataarray_to_grib(file, canonic_dataarray, grib_keys=grib_keys)
