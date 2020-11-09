#
# Copyright 2017-2020 European Centre for Medium-Range Weather Forecasts (ECMWF).
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
#
# Authors:
#   Alessandro Amici - B-Open - https://bopen.eu
#

import os
import functools
import logging
import pkgutil
import typing as T  # noqa

import cffi

LOG = logging.getLogger(__name__)


ffi = cffi.FFI()
ffi.cdef(
    pkgutil.get_data(__name__, 'grib_api.h').decode('utf-8')
    + pkgutil.get_data(__name__, 'eccodes.h').decode('utf-8')
)


LIBNAMES = ["eccodes", "libeccodes.so", "libeccodes"]

try:
    import ecmwflibs
    LIBNAMES.insert(0, ecmwflibs.find("eccodes"))
except Exception:
    pass

if os.environ.get("ECCODES_DIR"):
    eccdir = os.environ["ECCODES_DIR"]
    LIBNAMES.insert(0, os.path.join(eccdir, "lib/libeccodes.so"))
    LIBNAMES.insert(0, os.path.join(eccdir, "lib64/libeccodes.so"))

for libname in LIBNAMES:
    try:
        lib = ffi.dlopen(libname)
        LOG.debug("ecCodes library found using name '%s'.", libname)
        break
    except OSError:
        raise RuntimeError(f"ecCodes library not found using {LIBNAMES}")


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

# Constants for 'missing'
GRIB_MISSING_DOUBLE = -1e100
GRIB_MISSING_LONG = 2147483647

CODES_MISSING_DOUBLE = GRIB_MISSING_DOUBLE
CODES_MISSING_LONG = GRIB_MISSING_LONG

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

KEYTYPES = {1: int, 2: float, 3: str}

CODES_KEYS_ITERATOR_ALL_KEYS = 0
CODES_KEYS_ITERATOR_SKIP_READ_ONLY = 1 << 0
CODES_KEYS_ITERATOR_SKIP_OPTIONAL = 1 << 1
CODES_KEYS_ITERATOR_SKIP_EDITION_SPECIFIC = 1 << 2
CODES_KEYS_ITERATOR_SKIP_CODED = 1 << 3
CODES_KEYS_ITERATOR_SKIP_COMPUTED = 1 << 4
CODES_KEYS_ITERATOR_SKIP_DUPLICATES = 1 << 5
CODES_KEYS_ITERATOR_SKIP_FUNCTION = 1 << 6
CODES_KEYS_ITERATOR_DUMP_ONLY = 1 << 7


#
# Helper functions for error reporting
#
def grib_get_error_message(code):
    # type: (int) -> str
    message = lib.grib_get_error_message(code)
    return ffi.string(message).decode(ENC)


class GribInternalError(Exception):
    def __init__(self, code, message=None, *args):
        self.code = code
        self.eccode_message = grib_get_error_message(code)
        if message is None:
            message = '%s (%s).' % (self.eccode_message, code)
        super(GribInternalError, self).__init__(message, code, *args)


class KeyValueNotFoundError(GribInternalError):
    """Key/value not found."""


class ReadOnlyError(GribInternalError):
    """Value is read only."""


class FileNotFoundError(GribInternalError):
    """File not found."""


ERROR_MAP = {-18: ReadOnlyError, -10: KeyValueNotFoundError, -7: FileNotFoundError}


def check_last(func):
    @functools.wraps(func)
    def wrapper(*args):
        code = ffi.new('int *')
        args += (code,)
        retval = func(*args)
        if code[0] != lib.GRIB_SUCCESS:
            if code[0] in ERROR_MAP:
                raise ERROR_MAP[code[0]](code[0])
            else:
                raise GribInternalError(code[0])
        return retval

    return wrapper


def check_return(func):
    @functools.wraps(func)
    def wrapper(*args):
        code = func(*args)
        if code != lib.GRIB_SUCCESS:
            if code in ERROR_MAP:
                raise ERROR_MAP[code](code)
            else:
                raise GribInternalError(code)

    return wrapper


#
# CFFI reimplementation of gribapi.py functions with codes names
#
def codes_grib_new_from_file(fileobj, product_kind=CODES_PRODUCT_GRIB, context=None):
    if context is None:
        context = ffi.NULL
    try:
        retval = check_last(lib.codes_handle_new_from_file)(context, fileobj, product_kind)
        if retval == ffi.NULL:
            raise EOFError("End of file: %r" % fileobj)
        else:
            return retval
    except GribInternalError as ex:
        if ex.code == lib.GRIB_END_OF_FILE:
            raise EOFError("End of file: %r" % fileobj)
        raise


codes_new_from_file = codes_grib_new_from_file


def codes_clone(handle):
    # type: (cffi.FFI.CData) -> cffi.FFI.CData
    cloned_handle = lib.codes_handle_clone(handle)
    if cloned_handle is ffi.NULL:
        raise GribInternalError(lib.GRIB_NULL_POINTER)
    return cloned_handle


codes_release = lib.codes_handle_delete


_codes_get_size = check_return(lib.codes_get_size)


def codes_get_size(handle, key):
    # type: (cffi.FFI.CData, str) -> int
    """
    Get the number of coded value from a key.
    If several keys of the same name are present, the total sum is returned.

    :param bytes key: the keyword to get the size of

    :rtype: int
    """
    size = ffi.new('size_t *')
    _codes_get_size(handle, key.encode(ENC), size)
    return size[0]


_codes_get_length = check_return(lib.codes_get_length)


def codes_get_string_length(handle, key):
    # type: (cffi.FFI.CData, str) -> int
    """
    Get the length of the string representation of the key.
    If several keys of the same name are present, the maximum length is returned.

    :param bytes key: the keyword to get the string representation size of.

    :rtype: int
    """
    size = ffi.new('size_t *')
    _codes_get_length(handle, key.encode(ENC), size)
    return size[0]


_codes_get_bytes = check_return(lib.codes_get_bytes)


def codes_get_bytes_array(handle, key, size):
    # type: (cffi.FFI.CData, str, int) -> T.List[int]
    """
    Get unsigned chars array values from a key.

    :param bytes key: the keyword whose value(s) are to be extracted

    :rtype: List(int)
    """
    values = ffi.new('unsigned char[]', size)
    size_p = ffi.new('size_t *', size)
    _codes_get_bytes(handle, key.encode(ENC), values, size_p)
    return list(values)


_codes_get_long_array = check_return(lib.codes_get_long_array)


def codes_get_long_array(handle, key, size):
    # type: (cffi.FFI.CData, str, int) -> T.List[int]
    """
    Get long array values from a key.

    :param bytes key: the keyword whose value(s) are to be extracted

    :rtype: List(int)
    """
    values = ffi.new('long[]', size)
    size_p = ffi.new('size_t *', size)
    _codes_get_long_array(handle, key.encode(ENC), values, size_p)
    return list(values)


_codes_get_double_array = check_return(lib.codes_get_double_array)


def codes_get_double_array(handle, key, size):
    # type: (cffi.FFI.CData, str, int) -> T.List[float]
    """
    Get double array values from a key.

    :param bytes key: the keyword whose value(s) are to be extracted

    :rtype: T.List(float)
    """
    values = ffi.new('double[]', size)
    size_p = ffi.new('size_t *', size)
    _codes_get_double_array(handle, key.encode(ENC), values, size_p)
    return list(values)


_codes_get_string_array = check_return(lib.codes_get_string_array)


def codes_get_string_array(handle, key, size, length=None):
    # type: (cffi.FFI.CData, str, int, int) -> T.List[bytes]
    """
    Get string array values from a key.

    :param bytes key: the keyword whose value(s) are to be extracted

    :rtype: T.List[bytes]
    """
    if length is None:
        length = codes_get_string_length(handle, key)
    values_keepalive = [ffi.new('char[]', length) for _ in range(size)]
    values = ffi.new('char*[]', values_keepalive)
    size_p = ffi.new('size_t *', size)
    _codes_get_string_array(handle, key.encode(ENC), values, size_p)
    return [ffi.string(values[i]).decode(ENC) for i in range(size_p[0])]


def codes_get_long(handle, key):
    # type: (cffi.FFI.CData, str) -> int
    value = ffi.new('long *')
    _codes_get_long = check_return(lib.codes_get_long)
    _codes_get_long(handle, key.encode(ENC), value)
    return value[0]


def codes_get_double(handle, key):
    # type: (cffi.FFI.CData, str) -> int
    value = ffi.new('double *')
    _codes_get_long = check_return(lib.codes_get_double)
    _codes_get_long(handle, key.encode(ENC), value)
    return value[0]


def codes_get_string(handle, key, length=None):
    # type: (cffi.FFI.CData, str, int) -> str
    """
    Get string element from a key.
    It may or may not fail in case there are more than one key in a message.
    Outputs the last element.

    :param bytes key: the keyword to select the value of
    :param int length: (optional) length of the string

    :rtype: bytes
    """
    if length is None:
        length = codes_get_string_length(handle, key)
    values = ffi.new('char[]', length)
    length_p = ffi.new('size_t *', length)
    _codes_get_string = check_return(lib.codes_get_string)
    _codes_get_string(handle, key.encode(ENC), values, length_p)
    return ffi.string(values, length_p[0]).decode(ENC)


_codes_get_native_type = check_return(lib.codes_get_native_type)


def codes_get_native_type(handle, key):
    # type: (cffi.FFI.CData, str) -> int
    grib_type = ffi.new('int *')
    _codes_get_native_type(handle, key.encode(ENC), grib_type)
    return KEYTYPES.get(grib_type[0], grib_type[0])


def codes_get_array(handle, key, key_type=None, size=None, length=None, log=LOG):
    # type: (cffi.FFI.CData, str, int, int, int, logging.Logger) -> T.Any
    if key_type is None:
        key_type = codes_get_native_type(handle, key)
    if size is None:
        size = codes_get_size(handle, key)

    if key_type == int:
        return codes_get_long_array(handle, key, size)
    elif key_type == float:
        return codes_get_double_array(handle, key, size)
    elif key_type == str:
        return codes_get_string_array(handle, key, size, length=length)
    elif key_type == CODES_TYPE_BYTES:
        return codes_get_bytes_array(handle, key, size)
    else:
        log.warning("Unknown GRIB key type: %r", key_type)


def codes_get(handle, key, key_type=None, length=None, log=LOG):
    # type: (cffi.FFI.CData, str, int, int, logging.Logger) -> T.Any
    if key_type is None:
        key_type = codes_get_native_type(handle, key)

    if key_type == int:
        return codes_get_long(handle, key)
    elif key_type == float:
        return codes_get_double(handle, key)
    elif key_type == str:
        return codes_get_string(handle, key, length=length)
    else:
        log.warning("Unknown GRIB key type: %r", key_type)


def codes_keys_iterator_new(handle, flags=CODES_KEYS_ITERATOR_ALL_KEYS, namespace=None):
    # type: (cffi.FFI.CData, int, str) -> cffi.FFI.CData
    if namespace is None:
        bnamespace = ffi.NULL
    else:
        bnamespace = namespace.encode(ENC)

    codes_keys_iterator_new = lib.codes_keys_iterator_new
    return codes_keys_iterator_new(handle, flags, bnamespace)


def codes_keys_iterator_next(iterator_id):
    return lib.codes_keys_iterator_next(iterator_id)


def codes_keys_iterator_get_name(iterator):
    ret = lib.codes_keys_iterator_get_name(iterator)
    return ffi.string(ret).decode(ENC)


def codes_keys_iterator_delete(iterator_id):
    codes_keys_iterator_delete = check_return(lib.codes_keys_iterator_delete)
    codes_keys_iterator_delete(iterator_id)


def codes_get_api_version():
    """
    Get the API version.

    Returns the version of the API as a string in the format "major.minor.revision".
    """
    ver = lib.codes_get_api_version()
    patch = ver % 100
    ver = ver // 100
    minor = ver % 100
    major = ver // 100

    return "%d.%d.%d" % (major, minor, patch)


def portable_handle_new_from_samples(samplename, product_kind):
    #
    # re-implement codes_grib_handle_new_from_samples in a portable way.
    # imports are here not to pollute the head of the file with (hopefully!) temporary stuff
    #
    import os.path
    import platform

    handle = ffi.NULL
    if platform.platform().startswith('Windows'):
        samples_folder = ffi.string(lib.codes_samples_path(ffi.NULL)).decode('utf-8')
        sample_path = os.path.join(samples_folder, samplename + '.tmpl')
        try:
            with open(sample_path, 'rb') as file:
                handle = codes_grib_new_from_file(file, product_kind)
        except Exception:
            logging.exception("creating empty message from sample failed")
    return handle


def codes_new_from_samples(samplename, product_kind=CODES_PRODUCT_GRIB):
    # type: (str, int) -> cffi.FFI.CData

    # work around an ecCodes bug on Windows, hopefully this will go away soon
    handle = portable_handle_new_from_samples(samplename, product_kind)
    if handle != ffi.NULL:
        return handle
    # end of work-around

    if product_kind == CODES_PRODUCT_GRIB:
        handle = lib.codes_grib_handle_new_from_samples(ffi.NULL, samplename.encode(ENC))
    elif product_kind == CODES_PRODUCT_BUFR:
        handle = lib.codes_bufr_handle_new_from_samples(ffi.NULL, samplename.encode(ENC))
    else:
        raise NotImplementedError("product kind not supported: %r" % product_kind)
    if handle == ffi.NULL:
        raise ValueError("sample not found: %r" % samplename)
    return handle


def codes_set_long(handle, key, value):
    # type: (cffi.FFI.CData, str, int) -> None
    codes_set_long = check_return(lib.codes_set_long)
    codes_set_long(handle, key.encode(ENC), value)


def codes_set_double(handle, key, value):
    # type: (cffi.FFI.CData, str, float) -> None
    codes_set_double = check_return(lib.codes_set_double)
    codes_set_double(handle, key.encode(ENC), value)


def codes_set_string(handle, key, value):
    # type: (cffi.FFI.CData, str, str) -> None
    size = ffi.new('size_t *', len(value))
    codes_set_string = check_return(lib.codes_set_string)
    codes_set_string(handle, key.encode(ENC), value.encode(ENC), size)


def codes_set(handle, key, value):
    """"""
    if isinstance(value, int):
        codes_set_long(handle, key, value)
    elif isinstance(value, float):
        codes_set_double(handle, key, value)
    elif isinstance(value, str):
        codes_set_string(handle, key, value)
    else:
        raise TypeError("Unsupported type %r" % type(value))


def codes_set_double_array(handle, key, values):
    # type: (cffi.FFI.CData, str, T.List[float]) -> None
    size = len(values)
    c_values = ffi.new("double []", values)
    codes_set_double_array = check_return(lib.codes_set_double_array)
    codes_set_double_array(handle, key.encode(ENC), c_values, size)


def codes_set_long_array(handle, key, values):
    # type: (cffi.FFI.CData, str, T.List[int]) -> None
    size = len(values)
    c_values = ffi.new("long []", values)
    codes_set_long_array = check_return(lib.codes_set_long_array)
    codes_set_long_array(handle, key.encode(ENC), c_values, size)


def codes_set_array(handle, key, values):
    # type: (cffi.FFI.CData, str, T.List[T.Any]) -> None
    if len(values) > 0:
        if isinstance(values[0], float):
            codes_set_double_array(handle, key, values)
        elif isinstance(values[0], int):
            codes_set_long_array(handle, key, values)
        else:
            raise TypeError("Unsupported value type: %r" % type(values[0]))
    else:
        raise ValueError("Cannot set an empty list.")


def codes_grib_multi_support_on(context=None):
    if context is None:
        context = ffi.NULL
    lib.codes_grib_multi_support_on(context)


def codes_grib_multi_support_off(context=None):
    if context is None:
        context = ffi.NULL
    lib.codes_grib_multi_support_off(context)


def codes_grib_multi_support_reset_file(file):
    context = lib.codes_context_get_default()
    return lib.codes_grib_multi_support_reset_file(context, file)


def codes_write(handle, outfile):
    # type: (cffi.FFI.CData, T.BinaryIO) -> None
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
