#
# Copyright 2017-2021 European Centre for Medium-Range Weather Forecasts (ECMWF).
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

import contextlib
import hashlib
import logging
import os
import pickle
import typing as T

import attr
import eccodes  # type: ignore
import numpy as np

from . import abc

eccodes_version = eccodes.codes_get_api_version()

LOG = logging.getLogger(__name__)
_MARKER = object()

#
# MULTI-FIELD support is very tricky. Random access via the index needs multi support to be off.
#
eccodes.codes_grib_multi_support_off()


@contextlib.contextmanager
def multi_enabled(file: T.IO[bytes]) -> T.Iterator[None]:
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


KEY_TYPES = {
    "float": float,
    "int": int,
    "str": str,
    "": None,
}


OffsetType = T.Union[int, T.Tuple[int, int]]
OffsetsType = T.List[T.Tuple[T.Tuple[T.Any, ...], T.List[OffsetType]]]


@attr.attrs(auto_attribs=True)
class Message(abc.MutableMessage):
    """Dictionary-line interface to access Message headers."""

    codes_id: int
    encoding: str = "ascii"
    errors: str = attr.attrib(
        default="warn", validator=attr.validators.in_(["ignore", "warn", "raise"])
    )

    @classmethod
    def from_file(cls, file, offset=None, **kwargs):
        # type: (T.IO[bytes], T.Optional[OffsetType], T.Any) -> Message
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
        # type: (str, T.Any) -> Message
        codes_id = eccodes.codes_new_from_samples(sample_name, eccodes.CODES_PRODUCT_GRIB)
        return cls(codes_id=codes_id, **kwargs)

    @classmethod
    def from_message(cls, message, **kwargs):
        # type: (Message, T.Any) -> Message
        codes_id = eccodes.codes_clone(message.codes_id)
        return cls(codes_id=codes_id, **kwargs)

    def __del__(self) -> None:
        eccodes.codes_release(self.codes_id)

    def message_get(self, item, key_type=None, default=_MARKER):
        # type: (str, T.Optional[type], T.Any) -> T.Any
        """Get value of a given key as its native or specified type."""
        try:
            values = eccodes.codes_get_array(self.codes_id, item, key_type)
            if values is None:
                values = ["unsupported_key_type"]
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

    def message_set(self, item: str, value: T.Any) -> None:
        arr = isinstance(value, (np.ndarray, T.Sequence)) and not isinstance(value, str)
        if arr:
            eccodes.codes_set_array(self.codes_id, item, value)
        else:
            eccodes.codes_set(self.codes_id, item, value)

    def message_grib_keys(self, namespace: T.Optional[str] = None) -> T.Iterator[str]:
        iterator = eccodes.codes_keys_iterator_new(self.codes_id, namespace=namespace)
        while eccodes.codes_keys_iterator_next(iterator):
            yield eccodes.codes_keys_iterator_get_name(iterator)
        eccodes.codes_keys_iterator_delete(iterator)

    def __getitem__(self, item: str) -> T.Any:
        key, _, key_type_text = item.partition(":")
        if key_type_text not in KEY_TYPES:
            raise ValueError("key type not supported %r" % key_type_text)
        key_type = KEY_TYPES[key_type_text]
        return self.message_get(key, key_type=key_type)

    def __setitem__(self, item: str, value: T.Any) -> None:
        try:
            return self.message_set(item, value)
        except eccodes.GribInternalError as ex:
            if self.errors == "ignore":
                pass
            elif self.errors == "raise":
                raise KeyError("failed to set key %r to %r" % (item, value))
            else:
                if isinstance(ex, eccodes.ReadOnlyError):
                    # Very noisy error when trying to set computed keys
                    pass
                else:
                    LOG.warning("failed to set key %r to %r", item, value)

    def __delitem__(self, item: str) -> None:
        raise NotImplementedError

    def __iter__(self) -> T.Iterator[str]:
        for key in self.message_grib_keys():
            yield key

    def __len__(self) -> int:
        return sum(1 for _ in self)

    def write(self, file: T.IO[bytes]) -> None:
        eccodes.codes_write(self.codes_id, file)


GetterType = T.Callable[..., T.Any]
SetterType = T.Callable[..., None]
ComputedKeysType = T.Dict[str, T.Tuple[GetterType, SetterType]]


@attr.attrs(auto_attribs=True)
class ComputedKeysMessage(Message):
    """Extension of Message class for adding computed keys."""

    computed_keys: ComputedKeysType = {}

    def __getitem__(self, item: str) -> T.Any:
        if item in self.computed_keys:
            getter, _ = self.computed_keys[item]
            return getter(self)
        else:
            return super(ComputedKeysMessage, self).__getitem__(item)

    def __iter__(self) -> T.Iterator[str]:
        seen = set()
        for key in super(ComputedKeysMessage, self).__iter__():
            yield key
            seen.add(key)
        for key in self.computed_keys:
            if key not in seen:
                yield key

    def __setitem__(self, item: str, value: T.Any) -> None:
        if item in self.computed_keys:
            _, setter = self.computed_keys[item]
            return setter(self, value)
        else:
            return super(ComputedKeysMessage, self).__setitem__(item, value)


@attr.attrs(auto_attribs=True)
class FileStream(T.Iterable[Message]):
    """Iterator-like access to a filestream of Messages."""

    path: str
    message_class: T.Type[Message] = attr.attrib(default=Message, repr=False)
    errors: str = attr.attrib(
        default="warn", validator=attr.validators.in_(["ignore", "warn", "raise"])
    )

    def __iter__(self) -> T.Iterator[Message]:
        with open(self.path, "rb") as file:
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
                        if self.errors == "ignore":
                            pass
                        elif self.errors == "raise":
                            raise
                        else:
                            LOG.exception("skipping corrupted Message")

    def message_from_file(self, file, offset=None, **kwargs):
        # type: (T.IO[bytes], T.Optional[OffsetType], T.Any) -> Message
        return self.message_class.from_file(file, offset, **kwargs)

    def first(self) -> Message:
        for message in self:
            return message
        raise ValueError("index has no message")

    def index(self, index_keys, indexpath="{path}.{short_hash}.idx"):
        # type: (T.Sequence[str], str) -> FileIndex
        return FileIndex.from_indexpath_or_filestream(self, index_keys, indexpath)


@contextlib.contextmanager
def compat_create_exclusive(path):
    # type: (str) -> T.Generator[T.IO[bytes], None, None]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    with open(fd, mode="wb") as file:
        try:
            yield file
        except Exception:
            file.close()
            os.unlink(path)
            raise


ALLOWED_PROTOCOL_VERSION = "1"


@attr.attrs(auto_attribs=True)
class FileIndex(abc.Index[OffsetType, Message]):
    filestream: FileStream
    index_keys: T.List[str]
    offsets: OffsetsType = attr.attrib(repr=False)
    filter_by_keys: T.Dict[str, T.Any] = {}
    index_protocol_version: str = ALLOWED_PROTOCOL_VERSION

    @classmethod
    def from_filestream(cls, filestream, index_keys):
        # type: (FileStream, T.Sequence[str]) -> FileIndex
        offsets = {}  # type: T.Dict[T.Tuple[T.Any, ...], T.List[T.Union[int, T.Tuple[int, int]]]]
        index_keys = list(index_keys)
        count_offsets = {}  # type: T.Dict[int, int]
        header_values_cache = {}  # type: T.Dict[T.Tuple[T.Any, type], T.Any]
        for message in filestream:
            header_values = []
            for key in index_keys:
                try:
                    value = message[key]
                except:
                    value = "undef"
                if isinstance(value, (np.ndarray, list)):
                    value = tuple(value)
                # NOTE: the following ensures that values of the same type that evaluate equal are
                #   exactly the same object. The optimisation is especially useful for strings and
                #   it also reduces the on-disk size of the index in a backward compatible way.
                value = header_values_cache.setdefault((value, type(value)), value)
                header_values.append(value)
            offset = message.message_get("offset", int)
            if offset in count_offsets:
                count_offsets[offset] += 1
                offset_field = (offset, count_offsets[offset])
            else:
                count_offsets[offset] = 0
                offset_field = offset
            offsets.setdefault(tuple(header_values), []).append(offset_field)
        self = cls(filestream=filestream, index_keys=index_keys, offsets=list(offsets.items()))
        # record the index protocol version in the instance so it is dumped with pickle
        return self

    @classmethod
    def from_indexpath(cls, indexpath):
        # type: (str) -> FileIndex
        with open(indexpath, "rb") as file:
            index = pickle.load(file)
            if not isinstance(index, cls):
                raise ValueError("on-disk index not of expected type {cls}")
            if index.index_protocol_version != ALLOWED_PROTOCOL_VERSION:
                raise ValueError("protocol versione to allowed {index.index_protocol_version}")
            return index

    @classmethod
    def from_indexpath_or_filestream(
        cls, filestream, index_keys, indexpath="{path}.{short_hash}.idx", log=LOG
    ):
        # type: (FileStream, T.Sequence[str], str, logging.Logger) -> FileIndex

        # Reading and writing the index can be explicitly suppressed by passing indexpath==''.
        if not indexpath:
            return cls.from_filestream(filestream, index_keys)

        hash = hashlib.md5(repr(index_keys).encode("utf-8")).hexdigest()
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
                if (
                    getattr(self, "index_keys", None) == index_keys
                    and getattr(self, "filestream", None) == filestream
                    and getattr(self, "index_protocol_version", None) == ALLOWED_PROTOCOL_VERSION
                ):
                    return self
                else:
                    log.warning("Ignoring index file %r incompatible with GRIB file", indexpath)
            else:
                log.warning("Ignoring index file %r older than GRIB file", indexpath)
        except Exception:
            log.exception("Can't read index file %r", indexpath)

        return cls.from_filestream(filestream, index_keys)

    def __iter__(self) -> T.Iterator[str]:
        return iter(self.index_keys)

    def __len__(self) -> int:
        return len(self.index_keys)

    @property
    def header_values(self) -> T.Dict[str, T.List[T.Any]]:
        if not hasattr(self, "_header_values"):
            all_header_values = {}  # type: T.Dict[str, T.Dict[T.Any, None]]
            for header_values, _ in self.offsets:
                for i, value in enumerate(header_values):
                    values = all_header_values.setdefault(self.index_keys[i], {})
                    if value not in values:
                        values[value] = None
            self._header_values = {k: list(v) for k, v in all_header_values.items()}
        return self._header_values

    def __getitem__(self, item: str) -> T.List[T.Any]:
        return self.header_values[item]

    def getone(self, item):
        # type: (str) -> T.Any
        values = self[item]
        if len(values) != 1:
            raise ValueError("not one value for %r: %r" % (item, len(values)))
        return values[0]

    def subindex(self, filter_by_keys={}, **query):
        # type: (T.Mapping[str, T.Any], T.Any) -> FileIndex
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

    def first(self) -> Message:
        with open(self.filestream.path, "rb") as file:
            first_offset = self.offsets[0][1][0]
            return self.filestream.message_from_file(file, offset=first_offset)
