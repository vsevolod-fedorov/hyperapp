import datetime

from .htypes import (
    tNone,
    tString,
    tBinary,
    tInt,
    tBool,
    tDateTime,
    TList,
    )
from .record import TRecord
from .exception import TException
from .meta_type import list_mt
from .builtins import primitive_list_types


class DeduceTypeError(RuntimeError):
    pass


_primitive_types = {
    type(None): tNone,
    str: tString,
    bytes: tBinary,
    int: tInt,
    bool: tBool,
    datetime.datetime: tDateTime,
    }



def safe_repr(obj):
    try:
        return repr(obj)
    except Exception as x:
        return f"__repr__ failed: {x}"


def _is_named_tuple(value):
    return all(hasattr(value, field) for field in ['_fields', '_field_defaults', '_replace', '_make'])


def deduce_value_type(value):
    t = _primitive_types.get(type(value))
    if t:
        return t
    t = getattr(value, '_t', None)
    if isinstance(t, (TRecord, TException)):
        return t
    if isinstance(value, (list, tuple)) and not _is_named_tuple(value):
        if value:
            element_t = deduce_value_type(value[0])
        else:
            element_t = tNone
        return primitive_list_types[element_t]  # Use deduce_complex_value_type for non-primitive-element lists.
    raise DeduceTypeError(f"Unable to deduce type for {safe_repr(value)} (t: {t!r}). Use explicit type parameter.")


def _deduce_list_type(mosaic, types, value):
    if value:
        element_t = deduce_complex_value_type(mosaic, types, value[0])
    else:
        element_t = tNone  # Does not matter for an empty list.
    t = TList(element_t)
    try:
        _ = types.reverse_resolve(t)
        return t
    except:
        element_t_ref = types.reverse_resolve(element_t)
        piece = list_mt(element_t_ref)
        type_ref = mosaic.put(piece)
        return types.resolve(type_ref)


def deduce_complex_value_type(mosaic, types, value):
    if (isinstance(value, (list, tuple))
        and not _is_named_tuple(value)
        and not hasattr(value, '_t')):
        return _deduce_list_type(mosaic, types, value)
    return deduce_value_type(value)
