
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest
import numpy as np

from cfgrib import cfmessage
from cfgrib import messages
from cfgrib import dataset

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_dict_merge():
    master = {'one': 1}
    dataset.dict_merge(master, {'two': 2})
    assert master == {'one': 1, 'two': 2}
    dataset.dict_merge(master, {'two': 2})
    assert master == {'one': 1, 'two': 2}

    with pytest.raises(dataset.DatasetBuildError):
        dataset.dict_merge(master, {'two': 3})


def test_build_data_var_components_no_encode():
    index = messages.FileStream(path=TEST_DATA).index(dataset.ALL_KEYS).subindex(paramId=130)
    dims, data_var, coord_vars = dataset.build_data_var_components(index=index)
    assert dims == {'number': 10, 'dataDate': 2, 'dataTime': 2, 'level': 2, 'i': 7320}
    assert data_var.data.shape == (10, 2, 2, 2, 7320)

    # equivalent to not np.isnan without importing numpy
    assert data_var.data[:, :, :, :, :].mean() > 0.


def test_build_data_var_components_encode_geography():
    stream = messages.FileStream(path=TEST_DATA, message_class=cfmessage.CfMessage)
    index = stream.index(dataset.ALL_KEYS).subindex(paramId=130)
    dims, data_var, coord_vars = dataset.build_data_var_components(
        index=index, encode_geography=True,
    )
    assert dims == {
        'number': 10, 'dataDate': 2, 'dataTime': 2,
        'level': 2, 'latitude': 61, 'longitude': 120,
    }
    assert data_var.data.shape == (10, 2, 2, 2, 61, 120)

    # equivalent to not np.isnan without importing numpy
    assert data_var.data[:, :, :, :, :, :].mean() > 0.


def test_Dataset():
    res = dataset.Dataset.from_path(TEST_DATA)
    assert 'history' in res.attributes
    assert res.attributes['GRIB_edition'] == 1
    assert tuple(res.dimensions.keys()) == \
        ('number', 'time', 'isobaricInhPa', 'latitude', 'longitude')
    assert len(res.variables) == 9


def test_Dataset_no_encode():
    res = dataset.Dataset.from_path(
        TEST_DATA, encode_time=False, encode_vertical=False, encode_geography=False,
    )
    assert 'history' in res.attributes
    assert res.attributes['GRIB_edition'] == 1
    assert tuple(res.dimensions.keys()) == ('number', 'dataDate', 'dataTime', 'level', 'i')
    assert len(res.variables) == 9


def test_Dataset_encode_time():
    res = dataset.Dataset.from_path(TEST_DATA, encode_vertical=False, encode_geography=False)
    assert 'history' in res.attributes
    assert res.attributes['GRIB_edition'] == 1
    assert tuple(res.dimensions.keys()) == ('number', 'time', 'level', 'i')
    assert len(res.variables) == 9

    # equivalent to not np.isnan without importing numpy
    assert res.variables['t'].data[:, :, :, :].mean() > 0.


def test_Dataset_encode_geography():
    res = dataset.Dataset.from_path(TEST_DATA, encode_time=False, encode_vertical=False)
    assert 'history' in res.attributes
    assert res.attributes['GRIB_edition'] == 1
    assert tuple(res.dimensions.keys()) == \
        ('number', 'dataDate', 'dataTime', 'level', 'latitude', 'longitude')
    assert len(res.variables) == 9

    # equivalent to not np.isnan without importing numpy
    assert res.variables['t'].data[:, :, :, :, :, :].mean() > 0.


def test_Dataset_encode_vertical():
    res = dataset.Dataset.from_path(TEST_DATA, encode_time=False, encode_geography=False)
    assert 'history' in res.attributes
    assert res.attributes['GRIB_edition'] == 1
    assert tuple(res.dimensions.keys()) == ('number', 'dataDate', 'dataTime', 'isobaricInhPa', 'i')
    assert len(res.variables) == 9

    # equivalent to not np.isnan without importing numpy
    assert res.variables['t'].data[:, :, :, :, :].mean() > 0.


def test_Dataset_reguler_gg_surface():
    path = os.path.join(SAMPLE_DATA_FOLDER, 'regular_gg_sfc.grib')
    res = dataset.Dataset.from_path(path)

    assert res.dimensions == {'latitude': 96, 'longitude': 192}
    assert np.allclose(res.variables['latitude'].data[:2], [88.57216851, 86.72253095])
