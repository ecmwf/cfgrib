import os.path

import pytest

from cfgrib import bindings


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')
TEST_DATA_B = TEST_DATA.encode('ASCII')


@pytest.mark.parametrize(
    'code, message',
    [
        (0, 'No error'),  # bindings.lib.GRIB_SUCCESS
        (-43, 'End of index reached'),  # bindings.lib.GRIB_END_OF_INDEX
    ],
)
def test_grib_get_error_message(code, message):
    res = bindings.grib_get_error_message(code)

    assert res == message


def test_check_last():
    codes_handle_new_from_file = bindings.check_last(bindings.lib.codes_handle_new_from_file)
    with open(TEST_DATA) as file:
        codes_handle_new_from_file(bindings.ffi.NULL, file, bindings.CODES_PRODUCT_GRIB)

    with pytest.raises(bindings.GribInternalError):
        with open(__file__) as file:
            codes_handle_new_from_file(bindings.ffi.NULL, file, bindings.CODES_PRODUCT_GRIB)


def test_check_return():
    def identity(code):
        return code

    bindings.check_return(identity)(0)

    with pytest.raises(bindings.GribInternalError):
        bindings.check_return(identity)(-1)


def test_codes_grib_new_from_file():
    res = bindings.codes_grib_new_from_file(open(TEST_DATA))

    assert isinstance(res, bindings.ffi.CData)
    assert "'grib_handle *'" in repr(res)


def test_codes_clone():
    handle = bindings.codes_grib_new_from_file(open(TEST_DATA))

    res = bindings.codes_clone(handle)

    assert isinstance(res, bindings.ffi.CData)
    assert "'grib_handle *'" in repr(res)


def test_codes_grib_new_from_file_errors(tmpdir):
    empty_grib = tmpdir.join('empty.grib')
    empty_grib.ensure()

    with pytest.raises(EOFError):
        bindings.codes_grib_new_from_file(open(str(empty_grib)))

    garbage_grib = tmpdir.join('garbage.grib')
    garbage_grib.write('gargage')

    with pytest.raises(EOFError):
        bindings.codes_grib_new_from_file(open(str(garbage_grib)))

    bad_grib = tmpdir.join('bad.grib')
    bad_grib.write('GRIB')

    with pytest.raises(bindings.GribInternalError):
        bindings.codes_grib_new_from_file(open(str(bad_grib)))


@pytest.mark.parametrize(
    'key, expected_type, expected_value',
    [
        ('numberOfDataPoints', int, 7320),
        ('latitudeOfFirstGridPointInDegrees', float, 90.0),
        ('gridType', str, 'regular_ll'),
    ],
)
def test_codes_get(key, expected_type, expected_value):
    grib = bindings.codes_grib_new_from_file(open(TEST_DATA))

    result = bindings.codes_get(grib, key)

    assert isinstance(result, expected_type)
    assert result == expected_value


def test_codes_get_errors():
    grib = bindings.codes_grib_new_from_file(open(TEST_DATA))

    with pytest.raises(bindings.GribInternalError) as err:
        bindings.codes_get(grib, 'gridType', length=1)  # too short
    assert err.value.code == bindings.lib.GRIB_BUFFER_TOO_SMALL


@pytest.mark.parametrize(
    'key, expected_value',
    [
        ('numberOfDataPoints', [7320]),
        ('latitudeOfFirstGridPointInDegrees', [90.0]),
        ('gridType', ['regular_ll']),
    ],
)
def test_codes_get_array(key, expected_value):
    grib = bindings.codes_grib_new_from_file(open(TEST_DATA))

    result = bindings.codes_get_array(grib, key)

    assert result == expected_value


def test_codes_get_array_errors():
    grib = bindings.codes_grib_new_from_file(open(TEST_DATA))

    with pytest.raises(bindings.GribInternalError) as err:
        bindings.codes_get_array(grib, 'values', size=1)  # too short
    assert err.value.code == bindings.lib.GRIB_ARRAY_TOO_SMALL

    with pytest.raises(bindings.GribInternalError) as err:
        bindings.codes_get_array(grib, 'values', key_type=int)  # wrong type
    assert err.value.code == bindings.lib.GRIB_NOT_IMPLEMENTED


def test_codes_get_length():
    grib = bindings.codes_grib_new_from_file(open(TEST_DATA))

    res = bindings.codes_get_string_length(grib, 'numberOfForecastsInEnsemble')
    assert res == 1025

    res = bindings.codes_get_string_length(grib, 'marsParam')
    assert res == 8


def test_codes_keys_iterator():
    grib = bindings.codes_grib_new_from_file(open(TEST_DATA))

    iterator = bindings.codes_keys_iterator_new(grib)

    assert bindings.codes_keys_iterator_next(iterator) == 1
    assert bindings.codes_keys_iterator_get_name(iterator) == 'globalDomain'
    assert bindings.codes_keys_iterator_next(iterator) == 1
    assert bindings.codes_keys_iterator_get_name(iterator) == 'GRIBEditionNumber'

    bindings.codes_keys_iterator_delete(iterator)

    iterator = bindings.codes_keys_iterator_new(grib, namespace='time')

    assert bindings.codes_keys_iterator_next(iterator) == 1
    assert bindings.codes_keys_iterator_get_name(iterator) == 'dataDate'
    assert bindings.codes_keys_iterator_next(iterator) == 1
    assert bindings.codes_keys_iterator_get_name(iterator) == 'dataTime'

    bindings.codes_keys_iterator_delete(iterator)


def test_codes_get_api_version():
    res = bindings.codes_get_api_version()

    assert isinstance(res, str)
    assert res.count('.') == 2


def test_codes_new_from_samples():
    res = bindings.codes_new_from_samples('regular_ll_sfc_grib2')

    assert isinstance(res, bindings.ffi.CData)
    assert "grib_handle *'" in repr(res)


def test_codes_new_from_samples_errors():
    with pytest.raises(ValueError):
        bindings.codes_new_from_samples('non-existent')


def test_codes_set():
    message_id = bindings.codes_new_from_samples('regular_ll_sfc_grib2')

    bindings.codes_set(message_id, 'endStep', 2)
    bindings.codes_set(message_id, 'longitudeOfFirstGridPointInDegrees', 1.0)
    bindings.codes_set(message_id, 'gridType', 'regular_ll')

    with pytest.raises(TypeError):
        bindings.codes_set(message_id, 'endStep', [])


def test_codes_set_array():
    message_id = bindings.codes_new_from_samples('regular_ll_sfc_grib2')

    bindings.codes_set_array(message_id, 'values', [0.0])
    bindings.codes_set_array(message_id, 'values', [0])

    with pytest.raises(ValueError):
        bindings.codes_set_array(message_id, 'values', [])

    with pytest.raises(TypeError):
        bindings.codes_set_array(message_id, 'values', ['a'])


def test_codes_write(tmpdir):
    message_id = bindings.codes_new_from_samples('regular_ll_sfc_grib2')
    grib_file = tmpdir.join('test.grib')

    with open(str(grib_file), 'wb') as file:
        bindings.codes_write(message_id, file)

    assert grib_file.read_binary()[:4] == b'GRIB'

    with open(str(grib_file)) as file:
        bindings.codes_grib_new_from_file(file)
