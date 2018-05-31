
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import typing as T  # noqa

import attr

from . import eccodes


@attr.attrs()
class GribMessage(collections.Mapping):
    codes_id = attr.attrib()
    key_encoding = attr.attrib(default='ascii')
    value_encoding = attr.attrib(default='ascii')

    def message_get(self, item, key_type=None, strict=True):
        # type: (bytes, int, bool) -> T.Any
        """Get value of a given key as its native or specified type."""
        ret = None
        size = eccodes.codes_get_size(self.codes_id, item)
        if size > 1:
            ret = eccodes.codes_get_array(self.codes_id, item, key_type=key_type)
        elif size == 1:
            ret = eccodes.codes_get(self.codes_id, item, key_type=key_type, strict=strict)
        return ret

    def message_iterkeys(self, namespace=None):
        # type: (bytes) -> T.Generator[bytes, None, None]
        iterator = eccodes.codes_keys_iterator_new(self.codes_id, namespace=namespace)
        while eccodes.codes_keys_iterator_next(iterator):
            yield eccodes.codes_keys_iterator_get_name(iterator)
        eccodes.codes_keys_iterator_delete(iterator)

    def __getitem__(self, item):
        # type: (str) -> T.Any
        key = item.encode(self.key_encoding)
        value = self.message_get(key)
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
