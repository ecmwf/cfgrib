
from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import attr

from . import eccodes


@attr.attrs()
class GribMessage(collections.Mapping):
    codes_id = attr.attrib()
    encoding = attr.attrib(default='ascii')

    def message_get(self, item, key_type=None, strict=True):
        """Get value of a given key as its native or specified type."""
        if eccodes.codes_get_size(self.codes_id, item) > 1:
            ret = eccodes.codes_get_array(self.codes_id, item, key_type=key_type)
        else:
            ret = eccodes.codes_get(self.codes_id, item, key_type=key_type, strict=strict)
        return ret

    def message_iterkeys(self, namespace=None):
        iterator = eccodes.codes_keys_iterator_new(self.codes_id, namespace=namespace)
        while eccodes.codes_keys_iterator_next(iterator):
            yield eccodes.codes_keys_iterator_get_name(iterator)
        eccodes.codes_keys_iterator_delete(iterator)

    def __getitem__(self, item):
        value = self.message_get(item.encode(self.encoding))
        if isinstance(value, bytes):
            return value.decode(self.encoding)
        elif isinstance(value, list) and value and isinstance(value[0], bytes):
            return [v.decode(self.encoding) for v in value]
        else:
            return value

    def __iter__(self):
        for key in self.message_iterkeys():
            yield key.decode(self.encoding)

    def __len__(self):
        return sum(1 for _ in self)
