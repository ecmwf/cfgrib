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

import collections
import contextlib
import hashlib
import io
import logging
import os
import pickle
import typing as T

import attr
import numpy as np

try:
    # select between using the external ecCodes bindings or the internal implementation
    if int(os.environ.get('CFGRIB_USE_EXTERNAL_ECCODES_BINDINGS', '0')):
        import eccodes
    else:
        from . import bindings as eccodes
except RuntimeError as exc:
    # hide the pyeccodes import error from the majority of the users
    # that have problems with the ecCodes bindings
    try:
        import pyeccodes.compat as eccodes
    except ImportError:
        raise exc

eccodes_version = eccodes.codes_get_api_version()

LOG = logging.getLogger(__name__)
_MARKER = object()

#
# MULTI-FIELD support is very tricky. Random access via the index needs multi support to be off.
#
eccodes.codes_grib_multi_support_off()


@contextlib.contextmanager
def multi_enabled(file):
    """Context manager that enables MULTI-FIELD support in ecCodes from a clean state"""
    eccodes.codes_grib_multi_support_on()
    #
    # Explicitly reset the multi_support global state that gets confused by random access
    #
    # @alexamici: I'm note sure this is thread-safe. See :#141
    #
    eccodes.codes_grib_multi_support_reset_file(file)
    try:
        yield
    except Exception:
        eccodes.codes_grib_multi_support_off()
        raise
    eccodes.codes_grib_multi_support_off()


@attr.attrs()
class Message(collections.abc.MutableMapping):
    """Dictionary-line interface to access Message headers."""

    codes_id = attr.attrib()
    encoding = attr.attrib(default='ascii', type=str)
    errors = attr.attrib(
        default='warn', validator=attr.validators.in_(['ignore', 'warn', 'raise'])
    )

    @classmethod
    def from_file(cls, file, offset=None, **kwargs):
        # type: (T.IO[bytes], int, T.Any) -> Message
        field_in_message = 0
        if isinstance(offset, tuple):
            offset, field_in_message = offset
        if offset is not None:
            file.seek(offset)
        codes_id = None
        if field_in_message == 0:
            codes_id = eccodes.codes_grib_new_from_file(file)
        else:
            # MULTI-FIELD is enabled only when accessing additional fields
            with multi_enabled(file):
                for _ in range(field_in_message + 1):
                    codes_id = eccodes.codes_grib_new_from_file(file)

        if codes_id is None:
            raise EOFError("End of file: %r" % file)
        return cls(codes_id=codes_id, **kwargs)

    @classmethod
    def from_sample_name(cls, sample_name, **kwargs):
        codes_id = eccodes.codes_new_from_samples(sample_name, eccodes.CODES_PRODUCT_GRIB)
        return cls(codes_id=codes_id, **kwargs)

    @classmethod
    def from_message(cls, message, **kwargs):
        codes_id = eccodes.codes_clone(message.codes_id)
        return cls(codes_id=codes_id, **kwargs)

    def __del__(self):
        eccodes.codes_release(self.codes_id)

    def message_get(self, item, key_type=None, default=_MARKER):
        # type: (str, type, T.Any) -> T.Any
        """Get value of a given key as its native or specified type."""
        try:
            values = eccodes.codes_get_array(self.codes_id, item, key_type)
            if values is None:
                values = ['unsupported_key_type']
        except eccodes.KeyValueNotFoundError:
            if default is _MARKER:
                raise KeyError(item)
            else:
                return default
        if len(values) == 1:
            if isinstance(values, np.ndarray):
                values = values.tolist()
            return values[0]
        return values

    def message_set(self, item, value):
        # type: (str, T.Any) -> None
        set_array = isinstance(value, T.Sequence) and not isinstance(value, (str, bytes))
        if set_array:
            eccodes.codes_set_array(self.codes_id, item, value)
        else:
            eccodes.codes_set(self.codes_id, item, value)

    def message_grib_keys(self, namespace=None):
        # type: (str) -> T.Generator[str, None, None]
        iterator = eccodes.codes_keys_iterator_new(self.codes_id, namespace=namespace)
        while eccodes.codes_keys_iterator_next(iterator):
            yield eccodes.codes_keys_iterator_get_name(iterator)
        eccodes.codes_keys_iterator_delete(iterator)

    def message_bufr_keys(self):
        # type: () -> T.Generator[str, None, None]
        iterator = eccodes.codes_bufr_keys_iterator_new(self.codes_id)
        while eccodes.codes_bufr_keys_iterator_next(iterator):
            yield eccodes.codes_bufr_keys_iterator_get_name(iterator)
        eccodes.codes_bufr_keys_iterator_delete(iterator)

    def __getitem__(self, item):
        # type: (str) -> T.Any
        return self.message_get(item)

    def __setitem__(self, item, value):
        # type: (str, T.Any) -> None
        try:
            return self.message_set(item, value)
        except eccodes.GribInternalError as ex:
            if self.errors == 'ignore':
                pass
            elif self.errors == 'raise':
                raise KeyError("failed to set key %r to %r" % (item, value))
            else:
                if isinstance(ex, eccodes.ReadOnlyError):
                    # Very noisy error when trying to set computed keys
                    pass
                else:
                    LOG.warning("failed to set key %r to %r", item, value)

    def __delitem__(self, item):
        raise NotImplementedError

    def __iter__(self):
        # type: () -> T.Generator[str, None, None]
        for key in self.message_grib_keys():
            yield key

    def __len__(self):
        # type: () -> int
        return sum(1 for _ in self)

    def write(self, file):
        eccodes.codes_write(self.codes_id, file)


@attr.attrs()
class ComputedKeysMessage(Message):
    """Extension of Message class for adding computed keys."""

    computed_keys = attr.attrib(
        default={},
        type=T.Dict[str, T.Tuple[T.Callable[[Message], T.Any], T.Callable[[Message], T.Any]]],
    )

    def __getitem__(self, item):
        if item in self.computed_keys:
            getter, _ = self.computed_keys[item]
            return getter(self)
        else:
            return super(ComputedKeysMessage, self).__getitem__(item)

    def __iter__(self):
        seen = set()
        for key in super(ComputedKeysMessage, self).__iter__():
            yield key
            seen.add(key)
        for key in self.computed_keys:
            if key not in seen:
                yield key

    def __setitem__(self, item, value):
        if item in self.computed_keys:
            _, setter = self.computed_keys[item]
            return setter(self, value)
        else:
            return super(ComputedKeysMessage, self).__setitem__(item, value)


@attr.attrs()
class FileStream(collections.abc.Iterable):
    """Iterator-like access to a filestream of Messages."""

    path = attr.attrib(type=str)
    message_class = attr.attrib(default=Message, type=Message, repr=False)
    errors = attr.attrib(
        default='warn', validator=attr.validators.in_(['ignore', 'warn', 'raise'])
    )

    def __iter__(self):
        # type: () -> T.Generator[Message, None, None]
        with open(self.path, 'rb') as file:
            # enable MULTI-FIELD support on sequential reads (like when building the index)
            with multi_enabled(file):
                valid_message_found = False
                while True:
                    try:
                        yield self.message_from_file(file, errors=self.errors)
                        valid_message_found = True
                    except EOFError:
                        if not valid_message_found:
                            raise EOFError("No valid message found in file: %r" % self.path)
                        break
                    except Exception:
                        if self.errors == 'ignore':
                            pass
                        elif self.errors == 'raise':
                            raise
                        else:
                            LOG.exception("skipping corrupted Message")

    def message_from_file(self, file, offset=None, **kwargs):
        return self.message_class.from_file(file, offset, **kwargs)

    def first(self):
        # type: () -> Message
        return next(iter(self))

    def index(self, index_keys, indexpath='{path}.{short_hash}.idx'):
        # type: (T.List[str], str) -> FileIndex
        return FileIndex.from_indexpath_or_filestream(self, index_keys, indexpath)


@contextlib.contextmanager
def compat_create_exclusive(path, *args, **kwargs):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with io.open(fd, mode='wb', *args, **kwargs) as file:
        try:
            yield file
        except Exception:
            file.close()
            os.unlink(path)
            raise


@attr.attrs()
class FileIndex(collections.abc.Mapping):
    allowed_protocol_version = '1'
    filestream = attr.attrib(type=FileStream)
    index_keys = attr.attrib(type=T.List[str])
    offsets = attr.attrib(repr=False, type=T.List[T.Tuple[T.Tuple[T.Any, ...], T.List[int]]])
    filter_by_keys = attr.attrib(default={}, type=T.Dict[str, T.Any])

    @classmethod
    def from_filestream(cls, filestream, index_keys):
        offsets = collections.OrderedDict()
        count_offsets = {}  # type: T.Dict[int, int]
        header_values_cache = {}
        for message in filestream:
            header_values = []
            for key in index_keys:
                try:
                    value = message[key]
                except:
                    value = 'undef'
                if isinstance(value, (np.ndarray, list)):
                    value = tuple(value)
                # NOTE: the following ensures that values of the same type that evaluate equal are
                #   exactly the same object. The optimisation is especially useful for strings and
                #   it also reduces the on-disk size of the index in a backward compatible way.
                value = header_values_cache.setdefault((value, type(value)), value)
                header_values.append(value)
            offset = message.message_get('offset', int)
            if offset in count_offsets:
                count_offsets[offset] += 1
                offset_field = (offset, count_offsets[offset])
            else:
                count_offsets[offset] = 0
                offset_field = offset
            offsets.setdefault(tuple(header_values), []).append(offset_field)
        self = cls(filestream=filestream, index_keys=index_keys, offsets=list(offsets.items()))
        # record the index protocol version in the instance so it is dumped with pickle
        self.index_protocol_version = cls.allowed_protocol_version
        return self

    @classmethod
    def from_indexpath(cls, indexpath):
        with io.open(indexpath, 'rb') as file:
            return pickle.load(file)

    @classmethod
    def from_indexpath_or_filestream(
        cls, filestream, index_keys, indexpath='{path}.{short_hash}.idx', log=LOG
    ):
        # type: (FileStream, T.List[str], str, logging.Logger) -> FileIndex

        # Reading and writing the index can be explicitly suppressed by passing indexpath==''.
        if not indexpath:
            return cls.from_filestream(filestream, index_keys)

        hash = hashlib.md5(repr(index_keys).encode('utf-8')).hexdigest()
        indexpath = indexpath.format(path=filestream.path, hash=hash, short_hash=hash[:5])
        try:
            with compat_create_exclusive(indexpath) as new_index_file:
                self = cls.from_filestream(filestream, index_keys)
                pickle.dump(self, new_index_file)
                return self
        except FileExistsError:
            pass
        except Exception:
            log.exception("Can't create file %r", indexpath)

        try:
            index_mtime = os.path.getmtime(indexpath)
            filestream_mtime = os.path.getmtime(filestream.path)
            if index_mtime >= filestream_mtime:
                self = cls.from_indexpath(indexpath)
                allowed_protocol_version = self.allowed_protocol_version
                if (
                    getattr(self, 'index_keys', None) == index_keys
                    and getattr(self, 'filestream', None) == filestream
                    and getattr(self, 'index_protocol_version', None) == allowed_protocol_version
                ):
                    return self
                else:
                    log.warning("Ignoring index file %r incompatible with GRIB file", indexpath)
            else:
                log.warning("Ignoring index file %r older than GRIB file", indexpath)
        except Exception:
            log.exception("Can't read index file %r", indexpath)

        return cls.from_filestream(filestream, index_keys)

    def __iter__(self):
        return iter(self.index_keys)

    def __len__(self):
        return len(self.index_keys)

    @property
    def header_values(self):
        if not hasattr(self, '_header_values'):
            self._header_values = {}
            for header_values, _ in self.offsets:
                for i, value in enumerate(header_values):
                    values = self._header_values.setdefault(self.index_keys[i], [])
                    if value not in values:
                        values.append(value)
        return self._header_values

    def __getitem__(self, item):
        # type: (str) -> list
        return self.header_values[item]

    def getone(self, item):
        values = self[item]
        if len(values) != 1:
            raise ValueError("not one value for %r: %r" % (item, len(values)))
        return values[0]

    def subindex(self, filter_by_keys={}, **query):
        query.update(filter_by_keys)
        raw_query = [(self.index_keys.index(k), v) for k, v in query.items()]
        offsets = []
        for header_values, offsets_values in self.offsets:
            for idx, val in raw_query:
                if header_values[idx] != val:
                    break
            else:
                offsets.append((header_values, offsets_values))
        index = type(self)(
            filestream=self.filestream,
            index_keys=self.index_keys,
            offsets=offsets,
            filter_by_keys=query,
        )
        return index

    def first(self):
        with open(self.filestream.path, 'rb') as file:
            first_offset = self.offsets[0][1][0]
            return self.filestream.message_from_file(file, offset=first_offset)
