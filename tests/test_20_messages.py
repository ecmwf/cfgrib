
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest

from eccodes_grib import messages


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members-many_vars.grib')


def test_Message():
    with open(TEST_DATA) as file:
        res = messages.Message.fromfile(file)

    assert res['paramId'] == 129
    assert list(res)[0] == 'globalDomain'
    assert 'paramId' in res
    assert len(res) == 192

    with pytest.raises(KeyError):
        res['non-existent-key']

    list(res.items())


def test_Index():
    res = messages.Index(TEST_DATA, ['paramId'])
    assert res.get('paramId') == ['129', '130']
    assert sum(1 for _ in res.select(paramId='130')) == 80
    assert len(res) == 1
    assert list(res) == ['paramId']

    with pytest.raises(KeyError):
        res['non-existent-key']

    with pytest.raises(ValueError):
        list(res.select())


def test_Stream():
    res = messages.Stream(TEST_DATA)
    leader = res.first()
    assert len(leader) == 192
    assert sum(1 for _ in res) == leader['count']
