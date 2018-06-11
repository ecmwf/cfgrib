
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest

from eccodes_grib import messages
from eccodes_grib import dataset

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_from_grib_date_time():
    message = {
        'dataDate': 20160706,
        'dataTime': 1944,
    }
    result = dataset.from_grib_date_time(message)

    assert result == 1467834240


def test_dict_merge():
    master = {'one': 1}
    dataset.dict_merge(master, {'two': 2})
    assert master == {'one': 1, 'two': 2}
    dataset.dict_merge(master, {'two': 2})
    assert master == {'one': 1, 'two': 2}

    with pytest.raises(ValueError):
        dataset.dict_merge(master, {'two': 3})


def test_build_data_var_components_no_encode():
    index = messages.Stream(path=TEST_DATA).index(dataset.ALL_KEYS).subindex(paramId=130)
    dims, data_var, coord_vars = dataset.build_data_var_components(
        path=TEST_DATA, index=index, encode_time=False, encode_geography=False,
    )
    assert dims == {'number': 10, 'dataDate': 2, 'dataTime': 2, 'topLevel': 2, 'i': 7320}
    assert data_var.data.shape == (10, 2, 2, 2, 7320)

    # equivalent to not np.isnan without importing numpy
    assert data_var.data[:].mean() > 0.


def test_build_data_var_components_encode_geography():
    index = messages.Stream(path=TEST_DATA).index(dataset.ALL_KEYS).subindex(paramId=130)
    dims, data_var, coord_vars = dataset.build_data_var_components(
        path=TEST_DATA, index=index, encode_time=False, encode_geography=True,
    )
    assert dims == \
        {'number': 10, 'dataDate': 2, 'dataTime': 2, 'topLevel': 2, 'lat': 61, 'lon': 120}
    assert data_var.data.shape == (10, 2, 2, 2, 61, 120)

    # equivalent to not np.isnan without importing numpy
    assert data_var.data[:].mean() > 0.


def test_Dataset():
    res = dataset.Dataset.fromstream(TEST_DATA, encode_time=False, encode_geography=False)
    assert 'eccodesGribVersion' in res.attributes
    assert res.attributes['edition'] == 1
    assert tuple(res.dimensions.keys()) == ('number', 'topLevel', 'dataDate', 'dataTime', 'i')
    assert len(res.variables) == 9


def test_Dataset_encode_time():
    res = dataset.Dataset.fromstream(TEST_DATA, encode_time=True, encode_geography=False)
    assert 'eccodesGribVersion' in res.attributes
    assert res.attributes['edition'] == 1
    assert tuple(res.dimensions.keys()) == ('number', 'topLevel', 'forecast_reference_time', 'i')
    assert len(res.variables) == 8

    # equivalent to not np.isnan without importing numpy
    assert res.variables['t'].data[:].mean() > 0.


def test_Dataset_encode_geography():
    res = dataset.Dataset.fromstream(TEST_DATA, encode_time=False, encode_geography=True)
    assert 'eccodesGribVersion' in res.attributes
    assert res.attributes['edition'] == 1
    assert tuple(res.dimensions.keys()) == \
        ('number', 'topLevel', 'dataDate', 'dataTime', 'lat', 'lon')
    assert len(res.variables) == 9

    # equivalent to not np.isnan without importing numpy
    assert res.variables['t'].data[:].mean() > 0.


def test_Dataset_encode_time_encode_geography():
    res = dataset.Dataset.fromstream(TEST_DATA, encode_time=True, encode_geography=True)
    assert 'eccodesGribVersion' in res.attributes
    assert res.attributes['edition'] == 1
    assert tuple(res.dimensions.keys()) == \
        ('number', 'topLevel', 'forecast_reference_time', 'lat', 'lon')
    assert len(res.variables) == 8

    # equivalent to not np.isnan without importing numpy
    assert res.variables['t'].data[:].mean() > 0.
