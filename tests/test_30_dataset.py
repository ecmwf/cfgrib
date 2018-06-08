
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest

from eccodes_grib import messages
from eccodes_grib import dataset

SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_from_grib_date_time():
    datein = 20160706
    timein = 1944
    result = dataset.from_grib_date_time(datein, timein)

    assert result == 1467834240


def test_dict_merge():
    master = {'one': 1}
    dataset.dict_merge(master, {'two': 2})
    assert master == {'one': 1, 'two': 2}
    dataset.dict_merge(master, {'two': 2})
    assert master == {'one': 1, 'two': 2}

    with pytest.raises(ValueError):
        dataset.dict_merge(master, {'two': 3})


def test_build_data_var_components():
    index = messages.Stream(path=TEST_DATA).index(dataset.ALL_KEYS).subindex(paramId=130)
    dims, data_var, coord_vars = dataset.build_data_var_components(path=TEST_DATA, index=index)
    assert dims == {'number': 10, 'dataDate': 2, 'dataTime': 2, 'topLevel': 2, 'i': 7320}
    assert data_var.data.shape == (10, 2, 2, 2, 7320)

    assert data_var.data[:].mean() > 0.  # equivalent ot not np.isnan without importing numpy


def test_Dataset():
    res = dataset.Dataset.fromstream(TEST_DATA)
    assert 'eccodesGribVersion' in res.attributes
    assert res.attributes['edition'] == 1
    assert len(res.variables) == 9
    assert tuple(res.dimensions.keys()) == ('number', 'topLevel', 'dataDate', 'dataTime', 'i')


def test_Dataset_encode():
    res = dataset.Dataset.fromstream(TEST_DATA, encode_datetime=True)
    assert 'eccodesGribVersion' in res.attributes
    assert res.attributes['edition'] == 1
    assert len(res.variables) == 8
    assert tuple(res.dimensions.keys()) == ('number', 'topLevel', 'ref_time', 'i')
