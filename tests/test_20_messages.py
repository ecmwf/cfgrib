
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest

from eccodes_grib import eccodes
from eccodes_grib import messages


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


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

    with open(TEST_DATA) as file:
        res = messages.Message.fromfile(file, offset=0)

    assert res['paramId'] == 129
    assert res.message_get('non-existent-key', default=1) == 1


def test_Message_extra_keys():
    extra_keys = {
        'ref_time': lambda m: str(m['dataDate']) + str(m['dataTime']),
        'error_key': lambda m: 1 / 0,
    }
    with open(TEST_DATA) as file:
        res = messages.Message.fromfile(file, extra_keys=extra_keys)

    assert res['paramId'] == 129
    assert res['ref_time'] == '201701010'
    assert list(res)[0] == 'globalDomain'
    assert 'paramId' in res
    assert len(res) == 194

    with pytest.raises(KeyError):
        res['non-existent-key']

    with pytest.raises(KeyError):
        res['error_key']


def test_EcCodesIndex():
    res = messages.EcCodesIndex(TEST_DATA, ['paramId'])
    assert res.get('paramId') == [129, 130]
    assert sum(1 for _ in res.select(paramId='130')) == 80
    assert sum(1 for _ in res.select(paramId=130)) == 80
    assert len(res) == 1
    assert list(res) == ['paramId']

    with pytest.raises(KeyError):
        res['non-existent-key']

    with pytest.raises(ValueError):
        list(res.select())


def test_make_message_schema():
    with open(TEST_DATA) as file:
        message = messages.Message.fromfile(file)

    res = messages.make_message_schema(message, ['paramId', 'shortName', 'values', 'non-existent'])

    assert res['paramId'] == (eccodes.CODES_TYPE_LONG, 1)
    assert res['shortName'] == (eccodes.CODES_TYPE_STRING, 1, 256)
    assert res['values'] == (eccodes.CODES_TYPE_DOUBLE, 7320)
    assert res['non-existent'] == ()


def test_Index():
    res = messages.Index.fromstream(messages.Stream(TEST_DATA), ['paramId'])
    assert res.get('paramId') == [129, 130]
    assert len(res) == 1
    assert list(res) == ['paramId']
    assert res.first()

    with pytest.raises(ValueError):
        res.getone('paramId')

    with pytest.raises(KeyError):
        res['non-existent-key']


def test_Index_subindex():
    index = messages.Index.fromstream(messages.Stream(TEST_DATA), ['paramId'])
    assert index.get('paramId') == [129, 130]

    res = index.subindex(paramId=130)

    assert res.get('paramId') == [130]
    assert res.getone('paramId') == 130
    assert len(res) == 1


def test_Stream():
    res = messages.Stream(TEST_DATA)
    leader = res.first()
    assert len(leader) == 192
    assert sum(1 for _ in res) == leader['count']
    assert len(res.index(['paramId'])) == 1
