import datetime

from .htypes import tString, tBinary, tInt, tBool, tDateTime, TList
from .record import TRecord
from .hierarchy import TClass


class DeduceTypeError(RuntimeError):
    pass


_primitive_types = {
    str: tString,
    bytes: tBinary,
    int: tInt,
    bool: tBool,
    datetime.datetime: tDateTime,
    }


def deduce_value_type(value):
    t = _primitive_types.get(type(value))
    if t:
        return t
    t = getattr(value, '_t', None)
    if isinstance(t, TRecord):
        if isinstance(t, TClass):
            return t.hierarchy
        return t
    if isinstance(value, list):
        return TList(deduce_value_type(value[0]))
    raise DeduceTypeError(f"Unable to deduce type for {value!r} (t: {t!r}). Use explicit type parameter.")
