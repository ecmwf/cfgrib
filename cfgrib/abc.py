"""Abstract Base Classes for GRIB messsages and containers"""
import abc
import typing as T

MessageIdTypeVar = T.TypeVar("MessageIdTypeVar")
MessageTypeVar = T.TypeVar("MessageTypeVar", bound="Message")

Message = T.Mapping[str, T.Any]
MutableMessage = T.MutableMapping[str, T.Any]
Container = T.Mapping[MessageIdTypeVar, MessageTypeVar]


class Index(T.Mapping[str, T.List[T.Any]], T.Generic[MessageIdTypeVar, MessageTypeVar]):
    container: Container[MessageIdTypeVar, MessageTypeVar]
    index_keys: T.List[str]
    message_id_index: T.List[T.Tuple[T.Tuple[T.Any, ...], T.List[MessageIdTypeVar]]]
    filter_by_keys: T.Dict[str, T.Any] = {}

    @abc.abstractmethod
    def subindex(
        self, filter_by_keys: T.Mapping[str, T.Any] = {}, **query: T.Any
    ) -> "Index[MessageIdTypeVar, MessageTypeVar]":
        pass

    @abc.abstractmethod
    def getone(self, item: str) -> T.Any:
        pass

    @abc.abstractmethod
    def first(self) -> MessageTypeVar:
        pass
