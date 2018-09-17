
import numpy as np
import pandas as pd
import pytest
import xarray as xr

from cfgrib import xarray_to_grib


@pytest.fixture()
def canonic_da():
    da = xr.DataArray(
        np.zeros((4, 2, 3, 5, 6)),
        coords=[
            pd.date_range('2018-01-01T00:00', '2018-01-02T12:00', periods=4),
            pd.timedelta_range(0, '12h', periods=2),
            [1000., 850., 500.],
            np.linspace(90., -90., 5),
            np.linspace(0., 360., 6, endpoint=False),
        ],
        dims=['time', 'step', 'air_pressure', 'latitude', 'longitude'],
    )
    return da


def test_canonical_dataarray_to_grib_with_grik_keys(canonic_da, tmpdir):
    out_path = tmpdir.join('res.grib')
    grib_keys = {
        'gridType': 'regular_ll',
    }
    with open(str(out_path), 'wb') as file:
        xarray_to_grib.canonical_dataarray_to_grib(file, canonic_da, grib_keys=grib_keys)


def test_canonical_dataarray_to_grib_detect_grik_keys(canonic_da, tmpdir):
    out_path = tmpdir.join('res.grib')
    with open(str(out_path), 'wb') as file:
        xarray_to_grib.canonical_dataarray_to_grib(file, canonic_da)


def test_canonical_dataarray_to_grib_conflicting_detect_grik_keys(canonic_da, tmpdir):
    out_path = tmpdir.join('res.grib')
    grib_keys = {
        'gridType': 'reduced_ll',
    }
    with open(str(out_path), 'wb') as file:
        with pytest.raises(ValueError):
            xarray_to_grib.canonical_dataarray_to_grib(file, canonic_da, grib_keys=grib_keys)
