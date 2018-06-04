
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest

from eccodes_grib import dataset

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_dict_merge():
    master = {'one': 1}
    dataset.dict_merge(master, {'two': 2})
    assert master == {'one': 1, 'two': 2}
    dataset.dict_merge(master, {'two': 2})
    assert master == {'one': 1, 'two': 2}

    with pytest.raises(ValueError):
        dataset.dict_merge(master, {'two': 3})


def test_DataVariable():
    res = dataset.DataVariable.fromstream(path=TEST_DATA, paramId=130, name='tas')
    assert res.name == 'tas'
    assert res.dimensions == ('number', 'dataDate', 'dataTime', 'topLevel', 'i')
    assert res.shape == (10, 2, 2, 2, 7320)

    assert res.shape == res[:].shape
    assert res.size == res[:].size

    assert res[:].mean() > 0.  # equivalent ot not np.isnan without importing numpy


def test_Dataset():
    res = dataset.Dataset.fromstream(TEST_DATA)
    assert 'eccodesGribVersion' in res.attributes
    assert res.attributes['edition'] == 1
    assert len(res.variables) == 8
