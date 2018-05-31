
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest

from eccodes_grib import messages


TEST_DATA = os.path.join(os.path.dirname(__file__), 'sample-data', 'ERA5_levels.grib')


def test_Message():
    with open(TEST_DATA) as file:
        res = messages.Message(file)

    assert res['paramId'] == 130
    assert list(res)[0] == 'globalDomain'
    assert 'paramId' in res
    assert len(res) == 192

    list(res.items())


def test_Index():
    res = messages.Index(TEST_DATA, ['paramId'])
    assert res.get('paramId') == ['130', '131', '132']
    assert sum(1 for _ in res.select({'paramId': '130'})) == 24

    with pytest.raises(ValueError):
        list(res.select({}))


def test_Stream():
    res = messages.Stream(TEST_DATA)
    assert len(res.first()) == 192
    assert sum(1 for _ in res) == 72
