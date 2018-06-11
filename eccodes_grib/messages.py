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
from builtins import bytes, isinstance, str, type

import collections
import logging
import typing as T  # noqa

import attr

from . import eccodes


LOG = logging.getLogger(__name__)
_MARKER = object()


@attr.attrs()
class Message(collections.Mapping):
    codes_id = attr.attrib()
    encoding = attr.attrib(default='ascii', type=str)
    extra_keys = attr.attrib(default={}, type=T.Mapping[str, T.Callable[['Message'], T.Any]])

    @classmethod
    def fromfile(cls, file, offset=None, **kwargs):
        if offset is not None:
            file.seek(offset)
        codes_id = eccodes.codes_new_from_file(file, eccodes.CODES_PRODUCT_GRIB)
        if codes_id is None:
            raise EOFError("end-of-file reached.")
        return cls(codes_id=codes_id, **kwargs)

    def __del__(self):
        eccodes.codes_handle_delete(self.codes_id)

    def message_get(self, item, key_type=None, size=None, length=None, default=_MARKER):
        # type: (str, int, int, int, T.Any) -> T.Any
        """Get value of a given key as its native or specified type."""
        key = item.encode(self.encoding)
        try:
            values = eccodes.codes_get_array(self.codes_id, key, key_type, size, length)
        except eccodes.EcCodesError as ex:
            if ex.code == eccodes.lib.GRIB_NOT_FOUND:
                if default is _MARKER:
                    raise KeyError(item)
                else:
                    return default
            else:
                raise
        if values and isinstance(values[0], bytes):
            values = [v.decode(self.encoding) for v in values]
        if len(values) == 1:
            return values[0]
        return values

    def message_iterkeys(self, namespace=None):
        # type: (str) -> T.Generator[str, None, None]
        if namespace is not None:
            bnamespace = namespace.encode(self.encoding)
        else:
            bnamespace = None
        iterator = eccodes.codes_keys_iterator_new(self.codes_id, namespace=bnamespace)
        while eccodes.codes_keys_iterator_next(iterator):
            yield eccodes.codes_keys_iterator_get_name(iterator).decode(self.encoding)
        eccodes.codes_keys_iterator_delete(iterator)

    def __getitem__(self, item):
        # type: (str) -> T.Any
        if item in self.extra_keys:
            try:
                return self.extra_keys[item](self)
            except:
                raise KeyError(item)
        else:
            return self.message_get(item)

    def __iter__(self):
        # type: () -> T.Generator[str, None, None]
        for key in self.message_iterkeys():
            yield key
        for key in self.extra_keys:
            yield key

    def __len__(self):
        # type: () -> int
        return sum(1 for _ in self)


def make_message_schema(message, schema_keys, log=LOG):
    schema = collections.OrderedDict()
    for key in schema_keys:
        bkey = key.encode(message.encoding)
        try:
            key_type = eccodes.codes_get_native_type(message.codes_id, bkey)
        except eccodes.EcCodesError as ex:
            if ex.code != eccodes.lib.GRIB_NOT_FOUND:
                log.exception("key %r failed", key)
            schema[key] = ()
            continue
        size = eccodes.codes_get_size(message.codes_id, bkey)
        if key_type == eccodes.CODES_TYPE_STRING:
            length = eccodes.codes_get_length(message.codes_id, bkey)
            schema[key] = (key_type, size, length)
        else:
            schema[key] = (key_type, size)
    return schema


@attr.attrs()
class Index(collections.Mapping):
    path = attr.attrib(type=str)
    index_keys = attr.attrib(type=T.List[str])
    offsets = attr.attrib(repr=False)

    @classmethod
    def fromstream(cls, stream, index_keys):
        schema = make_message_schema(stream.first(), index_keys)
        offsets = collections.OrderedDict()
        for message in stream:
            header_values = []
            for key, args in schema.items():
                # Note: optimisation
                # value = message.message_get(key, *args, default='undef')
                value = message.get(key, 'undef')
                header_values.append(value)
            offset = message.message_get('offset', eccodes.CODES_TYPE_LONG)
            offsets.setdefault(tuple(header_values), []).append(offset)
        return cls(path=stream.path, index_keys=index_keys, offsets=offsets)

    def __iter__(self):
        return iter(self.index_keys)

    def __len__(self):
        return len(self.index_keys)

    @property
    def header_values(self):
        if not hasattr(self, '_header_values'):
            self._header_values = {}
            for header_values in self.offsets:
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

    def subindex(self, dict_query={}, **query):
        query.update(dict_query)
        raw_query = [(self.index_keys.index(k), v) for k, v in query.items()]
        offsets = collections.OrderedDict()
        for header_values in self.offsets:
            for idx, val in raw_query:
                if header_values[idx] != val:
                    break
            else:
                offsets[header_values] = self.offsets[header_values]
        return type(self)(path=self.path, index_keys=self.index_keys, offsets=offsets)


@attr.attrs()
class EcCodesIndex(collections.Mapping):
    path = attr.attrib(type=str)
    index_keys = attr.attrib(type=T.List[str])
    codes_index = attr.attrib(default=None)
    encoding = attr.attrib(default='ascii', type=str)

    def __iter__(self):
        return iter(self.index_keys)

    def __len__(self):
        return len(self.index_keys)

    def __attrs_post_init__(self):
        bindex_keys = [key.encode(self.encoding) for key in self.index_keys]
        bpath = self.path.encode(self.encoding)
        self.codes_index = eccodes.codes_index_new_from_file(bpath, bindex_keys)

    def __del__(self):
        eccodes.codes_index_delete(self.codes_index)

    def __getitem__(self, item):
        # type: (str) -> list
        key = item.encode(self.encoding)
        try:
            bvalues = eccodes.codes_index_get_autotype(self.codes_index, key)
        except eccodes.EcCodesError:
            raise KeyError(item)
        values = []
        for value in bvalues:
            if isinstance(value, bytes):
                value = value.decode(self.encoding)
            values.append(value)
        return values

    def select(self, dict_query={}, **query):
        # type: (T.Mapping[str, T.Any], T.Any) -> T.Generator[Message, None, None]
        query.update(dict_query)
        if set(query) != set(self.index_keys):
            raise ValueError("all index keys must have a value.")
        for key, value in query.items():
            bkey = key.encode(self.encoding)
            if isinstance(value, str):
                value = value.encode(self.encoding)
            eccodes.codes_index_select(self.codes_index, bkey, value)
        while True:
            try:
                codes_id = eccodes.codes_new_from_index(self.codes_index)
                yield Message(codes_id=codes_id, encoding=self.encoding)
            except eccodes.EcCodesError as ex:
                if ex.code == eccodes.lib.GRIB_END_OF_INDEX:
                    break
                else:
                    raise


@attr.attrs()
class Stream(collections.Iterable):
    path = attr.attrib(type=str)
    mode = attr.attrib(default='r', type=str)
    encoding = attr.attrib(default='ascii', type=str)
    message_factory = attr.attrib(default=Message.fromfile, type=T.Callable[..., Message])

    def __iter__(self):
        # type: () -> T.Generator[Message, None, None]
        with open(self.path, self.mode) as file:
            while True:
                try:
                    yield self.message_factory(file=file, encoding=self.encoding)
                except EOFError:
                    break

    def first(self):
        # type: () -> Message
        return next(iter(self))

    def index(self, index_keys):
        return Index.fromstream(stream=self, index_keys=index_keys)
