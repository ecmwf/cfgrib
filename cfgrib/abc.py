"""Abstract Base Classes for GRIB messsages and containers"""

import typing as T

import attr

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
    index_data: T.Mapping[T.Tuple[T.Any], ItemTypeVar]
