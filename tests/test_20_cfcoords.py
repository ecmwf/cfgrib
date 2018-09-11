
from __future__ import absolute_import, division, print_function, unicode_literals

import numpy as np
import pytest
import xarray as xr

from cf2cdm import cfcoords


@pytest.fixture
def dataarray1():
    latitude = [0., 0.5]
    longitude = [10., 10.5]
    time = ['2017-12-01T00:00:00', '2017-12-01T12:00:00', '2017-12-02T00:00:00']
    level = [950, 500]
    data = xr.DataArray(
        np.zeros((2, 2, 3, 2), dtype='float32'),
        coords=[
            ('lat', latitude, {'units': 'degrees_north'}),
            ('lon', longitude, {'units': 'degrees_east'}),
            ('ref_time', np.array(time, dtype=np.datetime64),
                {'standard_name': 'forecast_reference_time'}),
            ('level', np.array(level), {'units': 'hPa'}),
        ])
    return data


@pytest.fixture
def dataarray2():
    latitude = [0., 0.5]
    longitude = [10., 10.5]
    time = ['2017-12-01T00:00:00', '2017-12-01T12:00:00', '2017-12-02T00:00:00']
    level = [950, 500]
    data = xr.DataArray(
        np.zeros((2, 2, 3, 2), dtype='float32'),
        coords=[
            ('lat', latitude, {'units': 'degrees_north'}),
            ('lon', longitude, {'units': 'degrees_east'}),
            ('time', np.array(time, dtype=np.datetime64)),
            ('level', np.array(level), {'units': 'hPa'}),
        ])
    return data


@pytest.fixture
def dataarray3():
    latitude = [0., 0.5]
    longitude = [10., 10.5]
    step = [0, 24, 48]
    time = ['2017-12-01T00:00:00']
    level = [950, 500]
    data = xr.DataArray(
        np.zeros((2, 2, 3, 1, 2), dtype='float32'),
        coords=[
            ('lat', latitude, {'units': 'degrees_north'}),
            ('lon', longitude, {'units': 'degrees_east'}),
            ('step', np.array(step, dtype=np.timedelta64), {'standard_name': 'forecast_period'}),
            ('ref_time', np.array(time, dtype=np.datetime64),
                {'standard_name': 'forecast_reference_time'}),
            ('level', np.array(level), {'units': 'hPa'}),
        ])

    return data


def test_match_values():
    mapping = {'callable': len, 'int': 1}
    res = cfcoords.match_values(callable, mapping)

    assert res == ['callable']


def test_coord_translator(dataarray1):
    res = cfcoords.coord_translator('level', 'hPa', lambda x: False, 'level', dataarray1)
    assert dataarray1.equals(res)

    with pytest.raises(ValueError):
        cfcoords.coord_translator('level', 'hPa', lambda x: True, 'level', dataarray1)

    res = cfcoords.coord_translator('level', 'hPa', cfcoords.is_vertical_pressure, 'level', dataarray1)
    assert dataarray1.equals(res)

    with pytest.raises(ValueError):
        cfcoords.coord_translator('level', 'hPa', cfcoords.is_latitude, 'level', dataarray1)

    res = cfcoords.coord_translator('level', 'Pa', cfcoords.is_vertical_pressure, 'level', dataarray1)
    assert not dataarray1.equals(res)

    res = cfcoords.coord_translator('step', 'h', cfcoords.is_forecast_period, 'step', dataarray1)
    assert dataarray1.equals(res)


def test_translate_coords(dataarray1, dataarray2):
    result = cfcoords.translate_coords(dataarray1)

    assert 'latitude' in result.coords
    assert 'longitude' in result.coords
    assert 'time' in result.coords

    result = cfcoords.translate_coords(dataarray2)

    assert 'latitude' in result.coords
    assert 'longitude' in result.coords
    assert 'valid_time' in result.coords


def test_ensure_valid_time(dataarray1, dataarray3):
    result1 = cfcoords.ensure_valid_time(dataarray1.squeeze())
    result2 = cfcoords.ensure_valid_time(result1)

    assert 'valid_time' in result1.coords
    assert result2 is result1

    result1 = cfcoords.ensure_valid_time(dataarray3.squeeze())
    result2 = cfcoords.ensure_valid_time(result1)

    assert 'valid_time' in result1.coords
    assert result2 is result1
