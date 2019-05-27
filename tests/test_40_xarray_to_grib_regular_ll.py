import numpy as np
import pytest

pd = pytest.importorskip('pandas')  # noqa
xr = pytest.importorskip('xarray')  # noqa

from cfgrib import xarray_to_grib


@pytest.fixture()
def canonic_da():
    da = xr.DataArray(
        np.zeros((4, 2, 3, 5, 6)),
        coords=[
            pd.date_range('2018-01-01T00:00', '2018-01-02T12:00', periods=4),
            pd.timedelta_range(0, '12h', periods=2),
            [1000.0, 850.0, 500.0],
            np.linspace(90.0, -90.0, 5),
            np.linspace(0.0, 360.0, 6, endpoint=False),
        ],
        dims=['time', 'step', 'isobaricInhPa', 'latitude', 'longitude'],
    )
    return da


def test_canonical_dataarray_to_grib_with_grib_keys(canonic_da, tmpdir):
    out_path = tmpdir.join('res.grib')
    grib_keys = {'gridType': 'regular_ll'}
    with open(str(out_path), 'wb') as file:
        xarray_to_grib.canonical_dataarray_to_grib(canonic_da, file, grib_keys=grib_keys)


def test_canonical_dataarray_to_grib_detect_grib_keys(canonic_da, tmpdir):
    out_path = tmpdir.join('res.grib')
    with open(str(out_path), 'wb') as file:
        xarray_to_grib.canonical_dataarray_to_grib(canonic_da, file)


def test_canonical_dataarray_to_grib_conflicting_detect_grib_keys(canonic_da, tmpdir):
    out_path = tmpdir.join('res.grib')
    grib_keys = {'gridType': 'reduced_ll'}
    with open(str(out_path), 'wb') as file:
        with pytest.raises(ValueError):
            xarray_to_grib.canonical_dataarray_to_grib(canonic_da, file, grib_keys=grib_keys)


def test_canonical_dataset_to_grib(canonic_da, tmpdir):
    out_path = tmpdir.join('res.grib')
    canonic_ds = canonic_da.to_dataset(name='t')
    with pytest.warns(FutureWarning):
        xarray_to_grib.canonical_dataset_to_grib(canonic_ds, str(out_path))

    xarray_to_grib.canonical_dataset_to_grib(canonic_ds, str(out_path), no_warn=True)


def test_to_grib(canonic_da, tmpdir):
    out_path = tmpdir.join('res.grib')
    canonic_ds = canonic_da.to_dataset(name='t')
    with pytest.warns(FutureWarning):
        xarray_to_grib.to_grib(canonic_ds, str(out_path))
