#
# Copyright 2017-2018 B-Open Solutions srl.
# Copyright 2017-2018 European Centre for Medium-Range Weather Forecasts (ECMWF).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import, division, print_function, unicode_literals
from builtins import int, float, bytes

import functools
import pkgutil
import typing  # noqa

import cffi
import numpy as np


ffi = cffi.FFI()
ffi.cdef(pkgutil.get_data(__name__, 'eccodes.h').decode('utf-8'))


class RaiseOnAttributeAccess(object):
    def __init__(self, message):
        self.message = message

    def __getattr__(self, attr):
        raise RuntimeError(self.message)


try:
    # Linux / Unix systems
    lib = ffi.dlopen('libeccodes.so')
except OSError:
    try:
        # MacOS systems
        lib = ffi.dlopen('libeccodes')
    except OSError:
        # lazy exception
        lib = RaiseOnAttributeAccess('libeccodes library not found on the system.')


# default encoding for ecCodes strings
ENC = 'ascii'

#
# from gribapi.py
#
CODES_PRODUCT_ANY = 0
""" Generic product kind """
CODES_PRODUCT_GRIB = 1
""" GRIB product kind """
CODES_PRODUCT_BUFR = 2
""" BUFR product kind """
CODES_PRODUCT_METAR = 3
""" METAR product kind """
CODES_PRODUCT_GTS = 4
""" GTS product kind """
CODES_PRODUCT_TAF = 5
""" TAF product kind """


#
# Helper values to discriminate key types
#
CODES_TYPE_UNDEFINED = lib.GRIB_TYPE_UNDEFINED
CODES_TYPE_LONG = lib.GRIB_TYPE_LONG
CODES_TYPE_DOUBLE = lib.GRIB_TYPE_DOUBLE
CODES_TYPE_STRING = lib.GRIB_TYPE_STRING
CODES_TYPE_BYTES = lib.GRIB_TYPE_BYTES
CODES_TYPE_SECTION = lib.GRIB_TYPE_SECTION
CODES_TYPE_LABEL = lib.GRIB_TYPE_LABEL
CODES_TYPE_MISSING = lib.GRIB_TYPE_MISSING


#
# Helper functions for error reporting
#
def grib_get_error_message(code):
    # type: (int) -> str
    message = lib.grib_get_error_message(code)
    return ffi.string(message).decode(ENC)


class EcCodesError(Exception):
    def __init__(self, code, message=None, *args):
        self.code = code
        self.eccode_message = grib_get_error_message(code)
        if message is None:
            message = '%s (%s).' % (self.eccode_message, code)
        super(EcCodesError, self).__init__(message, code, *args)


def check_last(func):

    @functools.wraps(func)
    def wrapper(*args):
        code = ffi.new('int *')
        args += (code,)
        retval = func(*args)
        if code[0] != lib.GRIB_SUCCESS:
            raise EcCodesError(code[0])
        return retval

    return wrapper


def check_return(func):

    @functools.wraps(func)
    def wrapper(*args):
        code = func(*args)
        if code != lib.GRIB_SUCCESS:
            raise EcCodesError(code)

    return wrapper


#
# CFFI reimplementation of gribapi.py functions with codes names
#
def grib_get_gaussian_latitudes(truncation):
    latitudes = ffi.new('double[]', truncation * 2)
    check_return(lib.grib_get_gaussian_latitudes)(truncation, latitudes)
    return list(latitudes)


def codes_index_new_from_file(path, keys):
    # type: (bytes, typing.Iterable[bytes]) -> cffi.FFI.CData
    keys_enc = b','.join(keys)
    return check_last(lib.codes_index_new_from_file)(ffi.NULL, path, keys_enc)


def grib_new_from_file(fileobj, headers_only=False):
    try:
        retval = check_last(lib.grib_new_from_file)(ffi.NULL, fileobj, int(headers_only))
        if retval == ffi.NULL:
            return None
        else:
            return retval
    except EcCodesError as ex:
        if ex.code == lib.GRIB_END_OF_FILE:
            raise EOFError("File object is empty: %r" % fileobj)
        raise


def codes_new_from_file(fileobj, product_kind, headers_only=False):
    if product_kind == CODES_PRODUCT_GRIB:
        return grib_new_from_file(fileobj, headers_only)
    if product_kind == CODES_PRODUCT_BUFR:
        raise NotImplemented("Support for BUFR not yet implemented.")
    if product_kind == CODES_PRODUCT_METAR:
        raise NotImplemented("Support for METAR not yet implemented.")
    if product_kind == CODES_PRODUCT_GTS:
        raise NotImplemented("Support for GTS not yet implemented.")
    if product_kind == CODES_PRODUCT_ANY:
        raise NotImplemented("Support not yet implemented for this filetype.")
    raise Exception("Invalid product kind: " + product_kind)


codes_index_delete = lib.codes_index_delete


def codes_new_from_index(indexid):
    # type: (cffi.FFI.CData) -> cffi.FFI.CData
    return check_last(lib.codes_handle_new_from_index)(indexid)


def codes_new_from_samples(samplename, product_kind):
    # type: (bytes, int) -> cffi.FFI.CData
    if product_kind != CODES_PRODUCT_GRIB:
        raise NotImplemented("Support implemented only for GRIB.")
    return lib.codes_grib_handle_new_from_samples(ffi.NULL, samplename)


def codes_index_get_size(indexid, key):
    # type: (cffi.FFI.CData, bytes) -> int
    """
    Get the number of coded value from a key.
    If several keys of the same name are present, the total sum is returned.

    :param str key: the keyword to get the size of

    :rtype: int
    """
    size = ffi.new('size_t *')
    codes_index_get_size = check_return(lib.codes_index_get_size)
    codes_index_get_size(indexid, key, size)
    return size[0]


def codes_index_get_long(indexid, key):
    # type: (cffi.FFI.CData, bytes) -> typing.List[int]
    """
    Get the list of integer values associated to a key.
    The index must be created with such a key (possibly together with other
    keys).

    :param str key: the keyword whose list of values has to be retrieved

    :rtype: List(int)
    """
    size = codes_index_get_size(indexid, key)
    values = ffi.new('long[]', size)
    size_p = ffi.new('size_t *', size)
    check_return(lib.codes_index_get_long)(indexid, key, values, size_p)
    return list(values)


def codes_index_get_double(indexid, key):
    # type: (cffi.FFI.CData, bytes) -> typing.List[float]
    """
    Get the list of double values associated to a key.
    The index must be created with such a key (possibly together with other
    keys).

    :param str key: the keyword whose list of values has to be retrieved

    :rtype: List(int)
    """
    size = codes_index_get_size(indexid, key)
    values = ffi.new('double[]', size)
    size_p = ffi.new('size_t *', size)
    check_return(lib.codes_index_get_double)(indexid, key, values, size_p)
    return list(values)


def codes_index_get_string(indexid, key):
    # type: (cffi.FFI.CData, bytes) -> typing.List[str]
    """
    Get the list of string values associated to a key.
    The index must be created with such a key (possibly together with other
    keys).

    :param str key: the keyword whose list of values has to be retrieved

    :rtype: List(int)
    """
    size = codes_index_get_size(indexid, key)
    values = ffi.new('const char*[]', size)
    size_p = ffi.new('size_t *', size)
    codes_index_get_string = check_return(lib.codes_index_get_string)
    codes_index_get_string(indexid, key, values, size_p)
    return [ffi.string(value) for value in values]


def codes_index_get(indexid, key, ktype=bytes):
    # type: (cffi.FFI.CData, bytes, type) -> np.ndarray
    result = None  # type: np.ndarray
    if ktype is int:
        result = codes_index_get_long(indexid, key)
    elif ktype is float:
        result = codes_index_get_double(indexid, key)
    elif ktype is bytes:
        result = codes_index_get_string(indexid, key)

    return result


def codes_index_select_long(indexid, key, value):
    # type: (cffi.FFI.CData, bytes, int) -> None
    """
    Properly fix the index on a specific integer value of key. The key must
    be one of those the index has been endowed with.

    :param str key: the key to select
    :param int value: the value which has to be selected to use the index
    """
    codes_index_select_long = check_return(lib.codes_index_select_long)
    codes_index_select_long(indexid, key, value)


def codes_index_select_double(indexid, key, value):
    # type: (cffi.FFI.CData, bytes, float) -> None
    """
    Properly fix the index on a specific float value of key. The key must
    be one of those the index has been endowed with.

    :param str key: the key to select
    :param float value: the value which has to be selected to use the index
    """
    codes_index_select_double = check_return(lib.codes_index_select_double)
    codes_index_select_double(indexid, key, value)


def codes_index_select_string(indexid, key, value):
    # type: (cffi.FFI.CData, bytes, bytes) -> None
    """
    Properly fix the index on a specific string value of key. The key must
    be one of those the index has been endowed with.

    :param str key: the key to select
    :param str value: the value which has to be selected to use the index
    """
    codes_index_select_string = check_return(lib.codes_index_select_string)
    codes_index_select_string(indexid, key, value)


def codes_index_select(indexid, key, value):
    # type: (cffi.FFI.CData, bytes, typing.Any) -> None
    """
    Select the message subset with key==value.

    :param indexid: id of an index created from a file.
        The index must have been created with the key in argument.
    :param str key: key to be selected
    :param str value: value of the key to select
    """
    if isinstance(value, (int, np.integer)):
        codes_index_select_long(indexid, key, value)
    elif isinstance(value, float) or isinstance(value, np.float64):
        codes_index_select_double(indexid, key, value)
    elif isinstance(value, bytes):
        codes_index_select_string(indexid, key, value)
    else:
        raise RuntimeError("Key value not recognised: %r %r (type %r)" % (key, value, type(value)))


def codes_get_size(handle, key):
    # type: (cffi.FFI.CData, bytes) -> int
    """
    Get the number of coded value from a key.
    If several keys of the same name are present, the total sum is returned.

    :param str key: the keyword to get the size of

    :rtype: int
    """
    size = ffi.new('size_t *')
    codes_get_size = check_return(lib.codes_get_size)
    codes_get_size(handle, key, size)
    return size[0]


def codes_get_length(handle, key):
    # type: (cffi.FFI.CData, bytes) -> int
    """
    Get the length of the string representation of the key.
    If several keys of the same name are present, the maximum length is returned.

    :param str key: the keyword to get the string representation size of.

    :rtype: int
    """
    size = ffi.new('size_t *')
    codes_get_length = check_return(lib.codes_get_length)
    codes_get_length(handle, key, size)
    return size[0]


def codes_get_bytes_array(handle, key):
    # type: (cffi.FFI.CData, bytes) -> typing.List[int]
    """
    Get unsigned chars array values from a key.

    :param str key: the keyword whose value(s) are to be extracted

    :rtype: List(int)
    """
    size = codes_get_size(handle, key)
    values = ffi.new('unsigned char[]', size)
    size_p = ffi.new('size_t *', size)
    codes_get_bytes = check_return(lib.codes_get_bytes)
    codes_get_bytes(handle, key, values, size_p)
    return list(values)


def codes_get_long_array(handle, key):
    # type: (cffi.FFI.CData, bytes) -> typing.List[int]
    """
    Get long array values from a key.

    :param str key: the keyword whose value(s) are to be extracted

    :rtype: List(int)
    """
    size = codes_get_size(handle, key)
    values = ffi.new('long[]', size)
    size_p = ffi.new('size_t *', size)
    codes_get_long_array = check_return(lib.codes_get_long_array)
    codes_get_long_array(handle, key, values, size_p)
    return list(values)


def codes_get_double_array(handle, key):
    # type: (cffi.FFI.CData, bytes) -> typing.List[float]
    """
    Get double array values from a key.

    :param str key: the keyword whose value(s) are to be extracted

    :rtype: typing.List(float)
    """
    size = codes_get_size(handle, key)
    values = ffi.new('double[]', size)
    size_p = ffi.new('size_t *', size)
    codes_get_double_array = check_return(lib.codes_get_double_array)
    codes_get_double_array(handle, key, values, size_p)
    return list(values)


def codes_get_string_array(handle, key):
    # type: (cffi.FFI.CData, bytes) -> typing.List[bytes]
    """
    Get string array values from a key.

    :param str key: the keyword whose value(s) are to be extracted

    :rtype: typing.List(str)
    """
    size = codes_get_size(handle, key)
    length = codes_get_length(handle, key)
    values = ffi.new('char*[]', size)
    length_p = ffi.new('size_t *', length)
    codes_get_string_array = check_return(lib.codes_get_string_array)
    codes_get_string_array(handle, key, values, length_p)
    return [ffi.string(values[i]) for i in range(length_p[0])]


def codes_get_bytes(handle, key, strict=True):
    # type: (cffi.FFI.CData, bytes, bool) -> int
    """
    Get unsigned char element from a key.
    It may or may not fail in case there are more than one key in a message.
    Outputs the last element.

    :param str key: the keyword to select the value of
    :param bool strict: flag to select if the method should fail in case of
        more than one key in single message

    :rtype: int
    """
    values = codes_get_bytes_array(handle, key)
    if len(values) == 0:
        raise ValueError('No value for key %r' % key)
    elif len(values) > 1 and strict:
        raise ValueError('More than one value for key %r: %r' % (key, values))
    return values[-1]


def codes_get_long(handle, key, strict=True):
    # type: (cffi.FFI.CData, bytes, bool) -> int
    """
    Get long element from a key.
    It may or may not fail in case there are more than one key in a message.
    Outputs the last element.

    :param str key: the keyword to select the value of
    :param bool strict: flag to select if the method should fail in case of
        more than one key in single message

    :rtype: int
    """
    values = codes_get_long_array(handle, key)
    if len(values) == 0:
        raise ValueError('No value for key %r' % key)
    elif len(values) > 1 and strict:
        raise ValueError('More than one value for key %r: %r' % (key, values))
    return values[-1]


def codes_get_double(handle, key, strict=True):
    # type: (cffi.FFI.CData, bytes, bool) -> float
    """
    Get double element from a key.
    It may or may not fail in case there are more than one key in a message.
    Outputs the last element.

    :param str key: the keyword to select the value of
    :param bool strict: flag to select if the method should fail in case of
        more than one key in single message

    :rtype: float
    """
    values = codes_get_double_array(handle, key)
    if len(values) == 0:
        raise ValueError('No value for key %r' % key)
    elif len(values) > 1 and strict:
        raise ValueError('More than one value for key %r: %r' % (key, values))
    return values[-1]


def codes_get_string(handle, key, strict=True):
    # type: (cffi.FFI.CData, bytes, bool) -> bytes
    """
    Get string element from a key.
    It may or may not fail in case there are more than one key in a message.
    Outputs the last element.

    :param str key: the keyword to select the value of
    :param bool strict: flag to select if the method should fail in case of
        more than one key in single message

    :rtype: float
    """
    values = codes_get_string_array(handle, key)
    if len(values) == 0:
        raise ValueError('No value for key %r' % key)
    elif len(values) > 1 and strict:
        raise ValueError('More than one value for key %r: %r' % (key, values))
    return values[-1]


def codes_get_native_type(handle, key):
    # type: (cffi.FFI.CData, bytes) -> int
    grib_type = ffi.new('int *')
    codes_get_native_type = check_return(lib.codes_get_native_type)
    codes_get_native_type(handle, key, grib_type)
    return grib_type[0]


def codes_get_array(handle, key, key_type=None):
    # type: (cffi.FFI.CData, bytes, int) -> typing.Any
    if key_type is None:
        key_type = codes_get_native_type(handle, key)

    if key_type == CODES_TYPE_LONG:
        return codes_get_long_array(handle, key)
    elif key_type == CODES_TYPE_DOUBLE:
        return codes_get_double_array(handle, key)
    elif key_type == CODES_TYPE_STRING:
        return codes_get_string_array(handle, key)
    elif key_type == CODES_TYPE_BYTES:
        return codes_get_bytes_array(handle, key)
    else:
        raise RuntimeError("Unknown GRIB key type: %r" % key_type)


def codes_get(handle, key, key_type=None, strict=True):
    # type: (cffi.FFI.CData, bytes, int, bool) -> typing.Any
    if key_type is None:
        key_type = codes_get_native_type(handle, key)

    if key_type == CODES_TYPE_LONG:
        return codes_get_long(handle, key, strict)
    elif key_type == CODES_TYPE_DOUBLE:
        return codes_get_double(handle, key, strict)
    elif key_type == CODES_TYPE_STRING:
        return codes_get_string(handle, key, strict)
    elif key_type == CODES_TYPE_BYTES:
        return codes_get_bytes(handle, key)
    else:
        raise RuntimeError("Unknown GRIB key type: %r" % key_type)


def codes_keys_iterator_new(handle, namespace=None):
    if namespace is not None:
        raise NotImplemented("Namespace support not implemented")

    codes_keys_iterator_new = lib.codes_keys_iterator_new
    return codes_keys_iterator_new(handle, 0, ffi.NULL)


def codes_keys_iterator_next(iterator_id):
    return lib.codes_keys_iterator_next(iterator_id)


def codes_keys_iterator_get_name(iterator):
    ret = lib.codes_keys_iterator_get_name(iterator)
    return ffi.string(ret)


def codes_keys_iterator_delete(iterator_id):
    codes_keys_iterator_delete = check_return(lib.codes_keys_iterator_delete)
    codes_keys_iterator_delete(iterator_id)


def codes_grib_get_data(message_id):
    # type: (cffi.FFI.CData) -> typing.Iterable[typing.Tuple[float, float, float]]
    """
    Retrieves the field values in each message and outputs three lists of
    equal length containing, for each index, the latitude, longitude and
    field value.
    """
    size = codes_get(message_id, b'numberOfPoints')
    latitude = ffi.new('double[]', size)
    longitude = ffi.new('double[]', size)
    data = ffi.new('double[]', size)
    codes_grib_get_data = check_return(lib.codes_grib_get_data)
    codes_grib_get_data(message_id, latitude, longitude, data)
    return zip(latitude, longitude, data)


def codes_set_long(msgid, key, value):
    # type: (cffi.FFI.CData, bytes, int) -> None
    codes_set_long = check_return(lib.codes_set_long)
    codes_set_long(msgid, key, value)


def codes_set_double(msgid, key, value):
    # type: (cffi.FFI.CData, bytes, float) -> None
    codes_set_double = check_return(lib.codes_set_double)
    codes_set_double(msgid, key, value)


def codes_set_string(msgid, key, value):
    # type: (cffi.FFI.CData, bytes, bytes) -> None
    size = ffi.new('size_t *', len(value))
    codes_set_string = check_return(lib.codes_set_string)
    codes_set_string(msgid, key, value, size)


def codes_set(msgid, key, value):
    """"""
    if isinstance(value, (int, np.integer)):
        codes_set_long(msgid, key, value)
    elif isinstance(value, float):
        codes_set_double(msgid, key, value)
    elif isinstance(value, bytes):
        codes_set_string(msgid, key, value)
    else:
        raise TypeError('Unsupported type %r' % type(value))


def codes_set_double_array(msgid, key, values):
    # type: (cffi.FFI.CData, bytes, typing.List[float]) -> None
    size = len(values)
    c_values = ffi.new("double []", values)
    codes_set_double_array = check_return(lib.codes_set_double_array)
    codes_set_double_array(msgid, key, c_values, size)


def codes_set_array(msgid, key, values):
    # type: (cffi.FFI.CData, bytes, typing.List[typing.Any]) -> None
    if len(values) > 0:
        if isinstance(values[0], float):
            codes_set_double_array(msgid, key, values)
        else:
            raise NotImplemented
    else:
        raise ValueError("Cannot provide an empty list.")


def codes_write(handle, outfile):
    # type: (cffi.FFI.CData, typing.BinaryIO) -> None
    """
    Write a coded message to a file. If the file does not exist, it is created.

    :param str path: (optional) the path to the GRIB file;
        defaults to the one of the open index.
    """
    mess = ffi.new('const void **')
    mess_len = ffi.new('size_t*')
    codes_get_message = check_return(lib.codes_get_message)
    codes_get_message(handle, mess, mess_len)
    message = ffi.buffer(mess[0], size=mess_len[0])
    outfile.write(message)
