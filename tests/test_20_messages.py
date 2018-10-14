
from __future__ import absolute_import, division, print_function, unicode_literals

import os.path

import pytest

from cfgrib import eccodes
from cfgrib import messages


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')


def test_Message():
    with open(TEST_DATA) as file:
        res = messages.Message.from_file(file)

    assert res.message_get('paramId') == 129
    assert res['paramId'] == 129
    assert list(res)[0] == 'globalDomain'
    assert list(res.message_iterkeys('time'))[0] == 'dataDate'
    assert 'paramId' in res
    assert len(res) > 100

    with pytest.raises(KeyError):
        res['non-existent-key']

    assert res.message_get('non-existent-key', default=1) == 1

    list(res.items())

    with open(TEST_DATA) as file:
        with pytest.raises(EOFError):
            while True:
                messages.Message.from_file(file)


def test_ComputedKeysMessage():
    computed_keys = {
        'ref_time': (lambda m: str(m['dataDate']) + str(m['dataTime']), None),
        'error_key': (lambda m: 1 / 0, None),
        'centre': (lambda m: -1, None),
    }
    with open(TEST_DATA) as file:
        res = messages.ComputedKeysMessage.from_file(file, computed_keys=computed_keys)

    assert res['paramId'] == 129
    assert res['ref_time'] == '201701010'
    assert len(res) > 100
    assert res['centre'] == -1

    with pytest.raises(ZeroDivisionError):
        res['error_key']


def test_make_message_schema():
    with open(TEST_DATA) as file:
        message = messages.Message.from_file(file)

    res = messages.make_message_schema(message, ['paramId', 'shortName', 'values', 'non-existent'])

    assert res['paramId'] == (eccodes.CODES_TYPE_LONG, 1)
    assert res['shortName'] == (eccodes.CODES_TYPE_STRING, 1, 256)
    assert res['values'] == (eccodes.CODES_TYPE_DOUBLE, 7320)
    assert res['non-existent'] == ()


def test_FileIndex():
    res = messages.FileIndex.from_filestream(messages.FileStream(TEST_DATA), ['paramId'])
    assert res['paramId'] == [129, 130]
    assert len(res) == 1
    assert list(res) == ['paramId']
    assert res.first()

    with pytest.raises(ValueError):
        res.getone('paramId')

    with pytest.raises(KeyError):
        res['non-existent-key']

    subres = res.subindex(paramId=130)

    assert subres.get('paramId') == [130]
    assert subres.getone('paramId') == 130
    assert len(subres) == 1


def test_FileIndex_errors():
    class MyMessage(messages.ComputedKeysMessage):
        computed_keys = {
            'error_key': lambda m: 1 / 0,
        }
    stream = messages.FileStream(TEST_DATA, message_class=MyMessage)
    res = messages.FileIndex.from_filestream(stream, ['paramId', 'error_key'])
    assert res['paramId'] == [129, 130]
    assert len(res) == 2
    assert list(res) == ['paramId', 'error_key']
    assert res['error_key'] == ['undef']


def test_FileStream():
    res = messages.FileStream(TEST_DATA)
    leader = res.first()
    assert len(leader) > 100
    assert sum(1 for _ in res) == leader['count']
    assert len(res.index(['paramId'])) == 1
