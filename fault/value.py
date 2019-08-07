from enum import Enum


class Value(Enum):
    Any = 0
    Unknown = 1  # X
    HiZ = 2  # Z


AnyValue = Value.Any
UnknownValue = Value.Unknown
HiZ = Value.HiZ
