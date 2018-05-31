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
from builtins import bytes

import collections
import typing as T  # noqa

import attr

from . import eccodes


@attr.attrs()
class Message(collections.Mapping):
    file = attr.attrib(default=None)
    codes_index = attr.attrib(default=None)
    offset = attr.attrib(default=None)
    path = attr.attrib(default=None)
    key_encoding = attr.attrib(default='ascii')
    value_encoding = attr.attrib(default='ascii')

    def __attrs_post_init__(self):
        if self.file:
            self.offset = self.file.tell()
            self.path = self.file.name
            self.codes_id = eccodes.codes_new_from_file(self.file, eccodes.CODES_PRODUCT_GRIB)
            if self.codes_id is None:
                raise EOFError("end-of-file reached.")
            self.file = None
        elif self.codes_index:
            self.codes_id = eccodes.codes_new_from_index(self.codes_index)
        else:
            raise ValueError("creating an empty message is not supported.")


    def __del__(self):
        eccodes.codes_handle_delete(self.codes_id)

    def message_get(self, item, key_type=None, strict=True):
        # type: (str, int, bool) -> T.Any
        """Get value of a given key as its native or specified type."""
        key = item.encode(self.key_encoding)
        size = eccodes.codes_get_size(self.codes_id, key)
        ret = None
        if size > 1:
            ret = eccodes.codes_get_array(self.codes_id, key, key_type=key_type)
        elif size == 1:
            ret = eccodes.codes_get(self.codes_id, key, key_type=key_type, strict=strict)
        return ret

    def message_iterkeys(self, namespace=None):
        # type: (str) -> T.Generator[bytes, None, None]
        bnamespace = namespace.encode(self.key_encoding) if namespace else namespace
        iterator = eccodes.codes_keys_iterator_new(self.codes_id, namespace=bnamespace)
        while eccodes.codes_keys_iterator_next(iterator):
            yield eccodes.codes_keys_iterator_get_name(iterator)
        eccodes.codes_keys_iterator_delete(iterator)

    def __getitem__(self, item):
        # type: (str) -> T.Any
        value = self.message_get(item)
        if isinstance(value, bytes):
            return value.decode(self.value_encoding)
        elif isinstance(value, list) and value and isinstance(value[0], bytes):
            return [v.decode(self.value_encoding) for v in value]
        else:
            return value

    def __iter__(self):
        # type: () -> T.Generator[str, None, None]
        for key in self.message_iterkeys():
            yield key.decode(self.key_encoding)

    def __len__(self):
        # type: () -> int
        return sum(1 for _ in self)


@attr.attrs()
class Index(collections.Mapping):
    path = attr.attrib()
    keys = attr.attrib()
    codes_index = attr.attrib(default=None)
    key_encoding = attr.attrib(default='ascii')
    value_encoding = attr.attrib(default='ascii')

    def __attrs_post_init__(self):
        bkeys = [key.encode(self.key_encoding) for key in self.keys]
        bpath = self.path.encode(self.key_encoding)
        self.codes_index = eccodes.codes_index_new_from_file(bpath, bkeys)

    def __del__(self):
        eccodes.codes_index_delete(self.codes_index)

    def __getitem__(self, item):
        # type: (str) -> list
        key = item.encode(self.key_encoding)
        bvalues = eccodes.codes_index_get(self.codes_index, key)
        values = []
        for value in bvalues:
            if isinstance(value, bytes):
                value = value.decode(self.value_encoding)
            values.append(value)
        return values

    def __iter__(self):
        return self.keys

    def __len__(self):
        return len(self.keys)

    def select(self, query):
        # type: (T.Dict[str, T.Any]) -> T.Generator[Message, None, None]
        if set(query) != set(self.keys):
            raise ValueError("all index keys must have a value.")
        for key, value in query.items():
            bkey = key.encode(self.key_encoding)
            bvalue = value.encode(self.value_encoding)
            eccodes.codes_index_select(self.codes_index, bkey, bvalue)
        while True:
            try:
                yield Message(codes_index=self.codes_index)
            except eccodes.EcCodesError:
                break


@attr.attrs()
class Stream(collections.Iterable):
    path = attr.attrib()
    mode = attr.attrib(default='r')

    def __iter__(self):
        # type: () -> T.Generator[Message, None, None]
        with open(self.path, self.mode) as file:
            while True:
                try:
                    yield Message(file)
                except (EOFError, eccodes.EcCodesError):
                    break

    def first(self):
        # type: () -> Message
        return next(iter(self))

    def index(self, keys):
        # type: (T.Iterable[str]) -> Index
        return Index(path=self.path, keys=keys)
