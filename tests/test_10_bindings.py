
from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import bytes, float, int, str

import os.path

import pytest

from cfgrib import bindings


SAMPLE_DATA_FOLDER = os.path.join(os.path.dirname(__file__), 'sample-data')
TEST_DATA = os.path.join(SAMPLE_DATA_FOLDER, 'era5-levels-members.grib')
TEST_DATA_B = TEST_DATA.encode('ASCII')


def test_RaiseOnAttributeAccess():
    try:
        1 / 0
    except ZeroDivisionError as ex:
        res = bindings.RaiseOnAttributeAccess(ex, 'Infinity!')

    with pytest.raises(RuntimeError):
        res.non_existent_method()


@pytest.mark.parametrize('code, message', [
    (0, 'No error'),  # bindings.lib.GRIB_SUCCESS
    (-43, 'End of index reached'),  # bindings.lib.GRIB_END_OF_INDEX
])
def test_grib_get_error_message(code, message):
    res = bindings.grib_get_error_message(code)

    assert res == message


def test_check_last():
    codes_index_new_from_file = bindings.check_last(bindings.lib.codes_index_new_from_file)
    codes_index_new_from_file(bindings.ffi.NULL, TEST_DATA_B, b'')

    with pytest.raises(bindings.EcCodesError):
        codes_index_new_from_file(bindings.ffi.NULL, b'', b'')


def test_check_return():
    def identity(code):
        return code

    bindings.check_return(identity)(0)

    with pytest.raises(bindings.EcCodesError):
        bindings.check_return(identity)(-1)


def test_codes_handle_new_from_file():
    res = bindings.codes_handle_new_from_file(open(TEST_DATA))

    assert isinstance(res, bindings.ffi.CData)
    assert "'grib_handle *'" in repr(res)


def test_codes_handle_clone():
    handle = bindings.codes_handle_new_from_file(open(TEST_DATA))

    res = bindings.codes_handle_clone(handle)

    assert isinstance(res, bindings.ffi.CData)
    assert "'grib_handle *'" in repr(res)


def test_codes_handle_new_from_file_errors(tmpdir):
    empty_grib = tmpdir.join('empty.grib')
    empty_grib.ensure()

    with pytest.raises(EOFError):
        bindings.codes_handle_new_from_file(open(str(empty_grib)))

    garbage_grib = tmpdir.join('garbage.grib')
    garbage_grib.write('gargage')

    with pytest.raises(EOFError):
        bindings.codes_handle_new_from_file(open(str(garbage_grib)))

    bad_grib = tmpdir.join('bad.grib')
    bad_grib.write('GRIB')

    with pytest.raises(bindings.EcCodesError):
        bindings.codes_handle_new_from_file(open(str(bad_grib)))


@pytest.mark.parametrize('key, expected_type, expected_value', [
    (b'numberOfDataPoints', int, 7320),
    (b'latitudeOfFirstGridPointInDegrees', float, 90.0),
    (b'gridType', bytes, b'regular_ll'),
])
def test_codes_get(key, expected_type, expected_value):
    grib = bindings.codes_handle_new_from_file(open(TEST_DATA))

    result = bindings.codes_get(grib, key)

    assert isinstance(result, expected_type)
    assert result == expected_value


def test_codes_get_errors():
    grib = bindings.codes_handle_new_from_file(open(TEST_DATA))

    with pytest.raises(bindings.EcCodesError) as err:
        bindings.codes_get(grib, b'gridType', length=1)  # too short
    assert err.value.code == bindings.lib.GRIB_BUFFER_TOO_SMALL


def test_codes_index_new_from_file():
    res = bindings.codes_index_new_from_file(TEST_DATA_B, [b'gridType'])

    assert isinstance(res, bindings.ffi.CData)
    assert "'codes_index *'" in repr(res)


def test_codes_index_get_size():
    grib_index = bindings.codes_index_new_from_file(TEST_DATA_B, [b'gridType'])

    res = bindings.codes_index_get_size(grib_index, b'gridType')

    assert res == 1


@pytest.mark.parametrize('key, ktype, expected_value', [
    (b'numberOfDataPoints', int, 7320),
    (b'latitudeOfFirstGridPointInDegrees', float, 90.0),
    (b'gridType', bytes, b'regular_ll'),
])
def test_codes_index_get(key, ktype, expected_value):
    grib_index = bindings.codes_index_new_from_file(TEST_DATA_B, [key])

    res = bindings.codes_index_get(grib_index, key, ktype=ktype)

    assert len(res) == 1
    assert isinstance(res[0], ktype)
    assert res[0] == expected_value


@pytest.mark.parametrize('key, expected_value', [
    (b'numberOfDataPoints', [7320]),
    (b'latitudeOfFirstGridPointInDegrees', [90.0]),
    (b'gridType', [b'regular_ll']),
])
def test_codes_get_array(key, expected_value):
    grib = bindings.codes_handle_new_from_file(open(TEST_DATA))

    result = bindings.codes_get_array(grib, key)

    assert result == expected_value


def test_codes_get_array_errors():
    grib = bindings.codes_handle_new_from_file(open(TEST_DATA))

    with pytest.raises(bindings.EcCodesError) as err:
        bindings.codes_get_array(grib, b'values', size=1)  # too short
    assert err.value.code == bindings.lib.GRIB_ARRAY_TOO_SMALL

    with pytest.raises(bindings.EcCodesError) as err:
        bindings.codes_get_array(grib, b'values', key_type=bindings.CODES_TYPE_LONG)  # wrong type
    assert err.value.code == bindings.lib.GRIB_NOT_IMPLEMENTED


@pytest.mark.parametrize('key, value', [
    (b'numberOfDataPoints', 7320),
    (b'gridType', b'regular_ll'),
])
def test_codes_index_select(key, value):
    grib_index = bindings.codes_index_new_from_file(TEST_DATA_B, [key])

    bindings.codes_index_select(grib_index, key, value)
    grib_handle = bindings.codes_new_from_index(grib_index)

    result = bindings.codes_get(grib_handle, key)

    assert result == value


def test_codes_get_length():
    grib_index = bindings.codes_index_new_from_file(TEST_DATA_B, [b'paramId'])
    bindings.codes_index_select(grib_index, b'paramId', 130)
    grib_handle = bindings.codes_new_from_index(grib_index)

    result = []
    result.append(bindings.codes_get_length(grib_handle, b'numberOfForecastsInEnsemble'))
    result.append(bindings.codes_get_length(grib_handle, b'marsParam'))

    assert result[0] == 1025
    assert result[1] == 8


def test_codes_keys_iterator():
    grib = bindings.codes_handle_new_from_file(open(TEST_DATA))

    iterator = bindings.codes_keys_iterator_new(grib)

    assert bindings.codes_keys_iterator_next(iterator) == 1
    assert bindings.codes_keys_iterator_get_name(iterator) == b'globalDomain'
    assert bindings.codes_keys_iterator_next(iterator) == 1
    assert bindings.codes_keys_iterator_get_name(iterator) == b'GRIBEditionNumber'

    bindings.codes_keys_iterator_delete(iterator)

    iterator = bindings.codes_keys_iterator_new(grib, namespace=b'time')

    assert bindings.codes_keys_iterator_next(iterator) == 1
    assert bindings.codes_keys_iterator_get_name(iterator) == b'dataDate'
    assert bindings.codes_keys_iterator_next(iterator) == 1
    assert bindings.codes_keys_iterator_get_name(iterator) == b'dataTime'

    bindings.codes_keys_iterator_delete(iterator)


def test_codes_get_api_version():
    res = bindings.codes_get_api_version()

    assert isinstance(res, str)
    assert res.count('.') == 2


def test_codes_new_from_samples():
    res = bindings.codes_new_from_samples(b'regular_ll_sfc_grib2')

    assert isinstance(res, bindings.ffi.CData)
    assert "grib_handle *'" in repr(res)


def test_codes_new_from_samples_errors():
    with pytest.raises(ValueError):
        bindings.codes_new_from_samples(b'non-existent')


def test_codes_set():
    message_id = bindings.codes_new_from_samples(b'regular_ll_sfc_grib2')

    bindings.codes_set(message_id, b'endStep', 2)
    bindings.codes_set(message_id, b'longitudeOfFirstGridPointInDegrees', 1.)
    bindings.codes_set(message_id, b'gridType', b'regular_ll')

    with pytest.raises(TypeError):
        bindings.codes_set(message_id, b'endStep', [])


def test_codes_set_array():
    message_id = bindings.codes_new_from_samples(b'regular_ll_sfc_grib2')

    bindings.codes_set_array(message_id, b'values', [0.])
    bindings.codes_set_array(message_id, b'values', [0])

    with pytest.raises(ValueError):
        bindings.codes_set_array(message_id, b'values', [])

    with pytest.raises(TypeError):
        bindings.codes_set_array(message_id, b'values', ['a'])


def test_codes_write(tmpdir):
    message_id = bindings.codes_new_from_samples(b'regular_ll_sfc_grib2')
    grib_file = tmpdir.join('test.grib')

    with open(str(grib_file), 'wb') as file:
        bindings.codes_write(message_id, file)

    assert grib_file.read_binary()[:4] == b'GRIB'

    with open(str(grib_file)) as file:
        bindings.codes_handle_new_from_file(file)
