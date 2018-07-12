
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import int, float, bytes

import os.path

import pytest

from cfgrib import eccodes


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')
TEST_DATA_B = TEST_DATA.encode('ASCII')


@pytest.mark.parametrize('code, message', [
    (0, 'No error'),  # eccodes.lib.GRIB_SUCCESS
    (-43, 'End of index reached'),  # eccodes.lib.GRIB_END_OF_INDEX
])
def test_grib_get_error_message(code, message):
    res = eccodes.grib_get_error_message(code)

    assert res == message


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
    res = eccodes.codes_index_new_from_file(TEST_DATA_B, [b'gridType'])

    assert isinstance(res, eccodes.ffi.CData)
    assert "'codes_index *'" in repr(res)


@pytest.mark.parametrize('key, expected_value', [
    (b'numberOfDataPoints', 7320),
    (b'gridType', b'regular_ll'),
])
def test_codes_handle_new_from_file(key, expected_value):
    grib = eccodes.codes_handle_new_from_file(open(TEST_DATA))

    result = eccodes.codes_get(grib, key)

    assert result == expected_value


def test_codes_handle_new_from_file_errors():
    grib = eccodes.codes_handle_new_from_file(open(TEST_DATA))

    with pytest.raises(eccodes.EcCodesError) as err:
        eccodes.codes_get(grib, b'gridType', length=1)  # too short
    assert err.value.code == eccodes.lib.GRIB_BUFFER_TOO_SMALL


def test_codes_index_get_size():
    grib_index = eccodes.codes_index_new_from_file(TEST_DATA_B, [b'gridType'])

    res = eccodes.codes_index_get_size(grib_index, b'gridType')

    assert res == 1


@pytest.mark.parametrize('key, ktype, expected_value', [
    (b'numberOfDataPoints', int, 7320),
    (b'latitudeOfFirstGridPointInDegrees', float, 90.0),
    (b'gridType', bytes, b'regular_ll'),
])
def test_codes_index_get(key, ktype, expected_value):
    grib_index = eccodes.codes_index_new_from_file(TEST_DATA_B, [key])

    res = eccodes.codes_index_get(grib_index, key, ktype=ktype)

    assert len(res) == 1
    assert isinstance(res[0], ktype)
    assert res[0] == expected_value


@pytest.mark.parametrize('key, expected_value', [
    (b'numberOfDataPoints', [7320]),
    (b'gridType', [b'regular_ll']),
])
def test_codes_get_array(key, expected_value):
    grib = eccodes.codes_handle_new_from_file(open(TEST_DATA))

    result = eccodes.codes_get_array(grib, key)

    assert result == expected_value


def test_codes_get_array_errors():
    grib = eccodes.codes_handle_new_from_file(open(TEST_DATA))

    with pytest.raises(eccodes.EcCodesError) as err:
        eccodes.codes_get_array(grib, b'values', size=1)  # too short
    assert err.value.code == eccodes.lib.GRIB_ARRAY_TOO_SMALL

    with pytest.raises(eccodes.EcCodesError) as err:
        eccodes.codes_get_array(grib, b'values', key_type=eccodes.CODES_TYPE_LONG)  # wrong type
    assert err.value.code == eccodes.lib.GRIB_NOT_IMPLEMENTED


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
    grib = eccodes.codes_handle_new_from_file(open(TEST_DATA))

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
