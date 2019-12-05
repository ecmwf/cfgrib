import sys

import numpy as np
import pytest

xr = pytest.importorskip('xarray')  # noqa

from cf2cdm import cfcoords


@pytest.fixture
def da1():
    latitude = [0.5, 0.0]
    longitude = [10.0, 10.5]
    time = ['2017-12-01T00:00:00', '2017-12-01T12:00:00', '2017-12-02T00:00:00']
    level = [950, 500]
    data = xr.DataArray(
        np.zeros((2, 2, 3, 2), dtype='float32'),
        coords=[
            ('lat', latitude, {'units': 'degrees_north'}),
            ('lon', longitude, {'units': 'degrees_east'}),
            (
                'ref_time',
                np.array(time, dtype=np.datetime64),
                {'standard_name': 'forecast_reference_time'},
            ),
            ('level', np.array(level), {'units': 'hPa'}),
        ],
    )
    return data


@pytest.fixture
def da2():
    latitude = [0.5, 0.0]
    longitude = [10.0, 10.5]
    time = ['2017-12-01T00:00:00', '2017-12-01T12:00:00', '2017-12-02T00:00:00']
    level = [950, 500]
    data = xr.DataArray(
        np.zeros((2, 2, 3, 2), dtype='float32'),
        coords=[
            ('lat', latitude, {'units': 'degrees_north'}),
            ('lon', longitude, {'units': 'degrees_east'}),
            ('time', np.array(time, dtype=np.datetime64)),
            ('level', np.array(level), {'units': 'hPa'}),
        ],
    )
    return data


@pytest.fixture
def da3():
    latitude = [0.5, 0.0]
    longitude = [10.0, 10.5]
    step = [0, 24, 48]
    time = ['2017-12-01T00:00:00', '2017-12-01T12:00:00']
    level = [950, 500]
    data = xr.DataArray(
        np.zeros((2, 2, 3, 2, 2), dtype='float32'),
        coords=[
            ('lat', latitude, {'units': 'degrees_north'}),
            ('lon', longitude, {'units': 'degrees_east'}),
            ('step', np.array(step, dtype=np.timedelta64), {'standard_name': 'forecast_period'}),
            (
                'ref_time',
                np.array(time, dtype=np.datetime64),
                {'standard_name': 'forecast_reference_time'},
            ),
            ('time', np.array(level), {'units': 'hPa'}),
        ],
    )

    return data


def test_match_values():
    mapping = {'callable': len, 'int': 1}
    res = cfcoords.match_values(callable, mapping)

    assert res == ['callable']


def test_translate_coord_direction(da1):
    res = cfcoords.translate_coord_direction(da1, 'lat', 'increasing')
    assert res.lat.values[-1] > res.lat.values[0]

    res = cfcoords.translate_coord_direction(da1, 'lat', 'decreasing')
    assert res.lat.values[-1] < res.lat.values[0]

    res = cfcoords.translate_coord_direction(da1, 'lon', 'decreasing')
    assert res.lon.values[-1] < res.lon.values[0]

    res = cfcoords.translate_coord_direction(da1, 'lon', 'increasing')
    assert res.lon.values[-1] > res.lon.values[0]

    res = cfcoords.translate_coord_direction(da1.isel(lon=0), 'lon', 'increasing')
    assert len(res.lon.shape) == 0

    with pytest.raises(ValueError):
        cfcoords.translate_coord_direction(da1, 'lat', 'wrong')


def test_coord_translator(da1):
    res = cfcoords.coord_translator('level', 'hPa', 'decreasing', lambda x: False, 'lvl', da1)
    assert da1.equals(res)

    with pytest.raises(ValueError):
        cfcoords.coord_translator('level', 'hPa', 'decreasing', lambda x: True, 'lvl', da1)

    res = cfcoords.coord_translator('level', 'hPa', 'decreasing', cfcoords.is_isobaric, 'lvl', da1)
    assert da1.equals(res)

    with pytest.raises(ValueError):
        cfcoords.coord_translator('level', 'hPa', 'decreasing', cfcoords.is_latitude, 'lvl', da1)

    res = cfcoords.coord_translator('level', 'Pa', 'decreasing', cfcoords.is_isobaric, 'lvl', da1)
    assert not da1.equals(res)

    res = cfcoords.coord_translator('step', 'h', 'increasing', cfcoords.is_step, 'step', da1)
    assert da1.equals(res)


def test_translate_coords(da1, da2, da3):
    res = cfcoords.translate_coords(da1)

    assert 'latitude' in res.coords
    assert 'longitude' in res.coords
    assert 'time' in res.coords

    res = cfcoords.translate_coords(da2)

    assert 'latitude' in res.coords
    assert 'longitude' in res.coords
    assert 'valid_time' in res.coords

    res = cfcoords.translate_coords(da3, errors='ignore')
    assert 'latitude' in res.coords
    assert 'longitude' in res.coords


@pytest.mark.skipif(sys.version_info < (3, 6), reason="test needs stable dict's")
def test_translate_coords_errors(da3):
    cfcoords.translate_coords(da3)
    cfcoords.translate_coords(da3, errors='ignore')
    with pytest.raises(RuntimeError):
        cfcoords.translate_coords(da3, errors='raise')

    DATA_MODEL = {'config': {'preferred_time_dimension': 'valid_time'}}
    cfcoords.translate_coords(da3, DATA_MODEL)

    da3_fail = da3.drop('time')
    cfcoords.translate_coords(da3_fail, DATA_MODEL)
    cfcoords.translate_coords(da3_fail, DATA_MODEL, errors='ignore')


def test_ensure_valid_time(da1, da3):
    res1 = cfcoords.ensure_valid_time(da1.squeeze())
    res2 = cfcoords.ensure_valid_time(res1)

    assert 'valid_time' in res1.coords
    assert res2 is res1

    res1 = cfcoords.ensure_valid_time(da3.isel(ref_time=0).squeeze())
    res2 = cfcoords.ensure_valid_time(res1)

    assert 'valid_time' in res1.coords
    assert res2 is res1

    res1 = cfcoords.ensure_valid_time(da3.squeeze())
    assert 'valid_time' in res1.coords

    with pytest.raises(ValueError):
        cfcoords.ensure_valid_time(da3.mean(dim='ref_time').squeeze())
