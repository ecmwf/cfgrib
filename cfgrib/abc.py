"""Abstract Base Classes for GRIB messsages and containers"""

import typing as T

import attr
import numpy as np

ItemTypeVar = T.TypeVar("ItemTypeVar")
MessageTypeVar = T.TypeVar("MessageTypeVar")


class Message(T.Mapping[str, T.Any]):
    pass


class MutableMessage(T.MutableMapping[str, T.Any]):
    pass


class Container(T.Mapping[ItemTypeVar, MessageTypeVar]):
    pass


@attr.attrs(auto_attribs=True)
class Index(T.Mapping[str, ItemTypeVar]):
    container: Container[ItemTypeVar, Message]
    index_keys: T.List[str]
    index_data: T.List[T.Tuple[T.Tuple[T.Any, ...], T.List[ItemTypeVar]]]

    @classmethod
    def from_container(cls, container, index_keys):
        # type: (Container[ItemTypeVar, Message], T.Iterable[str]) -> Index[ItemTypeVar]
        index_data: T.Dict[T.Tuple[T.Any, ...], ItemTypeVar] = {}
        index_keys = list(index_keys)
        count_offsets = {}  # type: T.Dict[int, int]
        header_values_cache = {}  # type: T.Dict[T.Tuple[T.Any, type], T.Any]
        for message_uid, message in container.items():
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
            index_data_key = tuple(header_values)
            if index_data_key in index_data:
                print(f"multiple messages with identical values for {index_keys}")
            index_data.setdefault(index_data_key, []).append(message_uid)
            # index_data[index_data_key] = [message_uid]
        self = cls(container=container, index_keys=index_keys, index_data=list(index_data.items()))
        return self

    def __iter__(self) -> T.Iterator[str]:
        return iter(self.index_keys)

    def __len__(self) -> int:
        return len(self.index_keys)

    @property
    def header_values(self) -> T.Dict[str, T.List[T.Any]]:
        if not hasattr(self, "_header_values"):
            all_header_values = {}  # type: T.Dict[str, T.Dict[T.Any, None]]
            for header_values, _ in self.index_data:
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
        for header_values, offsets_values in self.index_data:
            for idx, val in raw_query:
                if header_values[idx] != val:
                    break
            else:
                offsets.append((header_values, offsets_values))
        index = type(self)(
            container=self.container,
            index_keys=self.index_keys,
            index_data=offsets,
            filter_by_keys=query,
        )
        return index

    def first(self) -> Message:
        return self.container[self.index_data[0][1][0]]
