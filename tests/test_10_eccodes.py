
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import int, float, bytes

import os.path

import pytest

from eccodes_grib import eccodes


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')
TEST_DATA_B = TEST_DATA.encode('ASCII')


@pytest.mark.parametrize('code, message', [
    (0, 'No error'),  # eccodes.lib.GRIB_SUCCESS
    (-43, 'End of index reached'),  # eccodes.lib.GRIB_END_OF_INDEX
])
def test_grib_get_error_message(code, message):
    result = eccodes.grib_get_error_message(code)

    assert result == message


def test_check_last():
    codes_index_new_from_file = eccodes.check_last(eccodes.lib.codes_index_new_from_file)
    codes_index_new_from_file(eccodes.ffi.NULL, TEST_DATA_B, b'')
    with pytest.raises(eccodes.EcCodesError):
        codes_index_new_from_file(eccodes.ffi.NULL, b'', b'')


def test_check_return():
    def identity(code):
        return code

    eccodes.check_return(identity)(0)
    with pytest.raises(eccodes.EcCodesError):
        eccodes.check_return(identity)(-1)


def test_codes_index_new_from_file():
    result = eccodes.codes_index_new_from_file(TEST_DATA_B, [b'gridType'])

    assert isinstance(result, eccodes.ffi.CData)
    assert "'codes_index *'" in repr(result)


def test_codes_index_get_size():
    grib_index = eccodes.codes_index_new_from_file(TEST_DATA_B, [b'gridType'])

    result = eccodes.codes_index_get_size(grib_index, b'gridType')

    assert isinstance(result, int)
    assert result == 1


@pytest.mark.parametrize('key, ktype, expected_value', [
    (b'numberOfDataPoints', int, 7320),
    (b'latitudeOfFirstGridPointInDegrees', float, 90.0),
    (b'gridType', bytes, b'regular_ll'),
])
def test_codes_index_get(key, ktype, expected_value):
    grib_index = eccodes.codes_index_new_from_file(TEST_DATA_B, [key])

    result = eccodes.codes_index_get(grib_index, key, ktype=ktype)

    assert len(result) == 1
    assert isinstance(result[0], ktype)
    assert result[0] == expected_value


@pytest.mark.parametrize('key, expected_value', [
    (b'numberOfDataPoints', [7320]),
    (b'gridType', [b'regular_ll']),
])
def test_codes_get_array(key, expected_value):
    grib = eccodes.grib_new_from_file(open(TEST_DATA))

    result = eccodes.codes_get_array(grib, key)

    assert result == expected_value


@pytest.mark.parametrize('key, expected_value', [
    (b'numberOfDataPoints', 7320),
    (b'gridType', b'regular_ll'),
])
def test_codes_get(key, expected_value):
    grib = eccodes.grib_new_from_file(open(TEST_DATA))

    result = eccodes.codes_get(grib, key)

    assert result == expected_value


@pytest.mark.parametrize('key, value', [
    (b'numberOfDataPoints', 7320),
    (b'gridType', b'regular_ll'),
])
def test_codes_index_select(key, value):
    grib_index = eccodes.codes_index_new_from_file(TEST_DATA_B, [key])

    eccodes.codes_index_select(grib_index, key, value)
    grib_handle = eccodes.codes_new_from_index(grib_index)

    result = eccodes.codes_get(grib_handle, key)

    assert result == value


def test_codes_get_length():
    grib_index = eccodes.codes_index_new_from_file(TEST_DATA_B, [b'paramId'])
    eccodes.codes_index_select(grib_index, b'paramId', 130)
    grib_handle = eccodes.codes_new_from_index(grib_index)

    result = []
    result.append(eccodes.codes_get_length(grib_handle, b'numberOfForecastsInEnsemble'))
    result.append(eccodes.codes_get_length(grib_handle, b'marsParam'))

    assert result[0] == 1025
    assert result[1] == 8


def test_codes_keys_iterator():
    grib = eccodes.grib_new_from_file(open(TEST_DATA))

    iterator = eccodes.codes_keys_iterator_new(grib)

    assert eccodes.codes_keys_iterator_next(iterator) == 1
    assert eccodes.codes_keys_iterator_get_name(iterator) == b'globalDomain'
    assert eccodes.codes_keys_iterator_next(iterator) == 1
    assert eccodes.codes_keys_iterator_get_name(iterator) == b'GRIBEditionNumber'

    eccodes.codes_keys_iterator_delete(iterator)

    iterator = eccodes.codes_keys_iterator_new(grib, namespace=b'time')

    assert eccodes.codes_keys_iterator_next(iterator) == 1
    assert eccodes.codes_keys_iterator_get_name(iterator) == b'dataDate'
    assert eccodes.codes_keys_iterator_next(iterator) == 1
    assert eccodes.codes_keys_iterator_get_name(iterator) == b'dataTime'

    eccodes.codes_keys_iterator_delete(iterator)
