"""Abstract Base Classes for GRIB messsages and containers"""

import typing as T

import attr
import numpy as np

ItemTypeVar = T.TypeVar("ItemTypeVar")
MessageTypeVar = T.TypeVar("MessageTypeVar", bound="Message")
IndexTypeVar = T.TypeVar("IndexTypeVar", bound="Index")  # type: ignore

Message = T.Mapping[str, T.Any]
MutableMessage = T.MutableMapping[str, T.Any]
Container = T.Mapping[ItemTypeVar, MessageTypeVar]


class Index(T.Mapping[str, T.List[T.Any]], T.Generic[ItemTypeVar, MessageTypeVar]):
    pass
