# meta type is type for storing types themselves as data

from .htypes import (
    BUILTIN_MODULE_NAME,
    Type,
    tNone,
    tString,
    tBinary,
    tInt,
    tBool,
    tDateTime,
    TOptional,
    TList,
    )
from .record import TRecord
from .exception import TException
from .hyper_ref import ref_t
from .phony_ref import phony_ref


builtin_mt = TRecord(BUILTIN_MODULE_NAME, 'builtin_mt', {
    'name': tString,
    })


# Produced by type module parsed, removed by loader.
name_mt = TRecord(BUILTIN_MODULE_NAME, 'name_mt', {
    'name': tString,
    })


optional_mt = TRecord(BUILTIN_MODULE_NAME, 'optional_mt', {
    'base': ref_t,
    })


def optional_from_piece(piece, pyobj_creg):
    base_t = pyobj_creg.invite(piece.base)
    return TOptional(base_t)


list_mt = TRecord(BUILTIN_MODULE_NAME, 'list_mt', {
    'element': ref_t,
    })


def list_from_piece(piece, pyobj_creg):
    element_t = pyobj_creg.invite(piece.element)
    return TList(element_t)


field_mt = TRecord(BUILTIN_MODULE_NAME, 'field_mt', {
    'name': tString,
    'type': ref_t,
    })

record_mt = TRecord(BUILTIN_MODULE_NAME, 'record_mt', {
    'module_name': tString,
    'name': tString,
    'base': TOptional(ref_t),
    'fields': TList(field_mt),
    })

exception_mt = TRecord(BUILTIN_MODULE_NAME, 'exception_mt', {
    'module_name': tString,
    'name': tString,
    'base': TOptional(ref_t),
    'fields': TList(field_mt),
    })


def _field_from_piece(piece, pyobj_creg):
    t = pyobj_creg.invite(piece.type)
    return (piece.name, t)


def _field_dict_from_piece_list(field_list, pyobj_creg):
    return dict(_field_from_piece(field, pyobj_creg) for field in field_list)


def record_from_piece(piece, pyobj_creg):
    if piece.base is not None:
        base_t = pyobj_creg.invite(piece.base)
        assert isinstance(base_t, TRecord), f"Record base is not a record: {base_t}"
    else:
        base_t = None
    field_dict = _field_dict_from_piece_list(piece.fields, pyobj_creg)
    return TRecord(piece.module_name, piece.name, field_dict, base=base_t)


def exception_from_piece(piece, pyobj_creg):
    if piece.base is not None:
        base_t = pyobj_creg.invite(piece.base)
        assert isinstance(base_t, TException), f"Exception base is not an exception: {base_t}"
    else:
        base_t = None
    field_dict = _field_dict_from_piece_list(piece.fields, pyobj_creg)
    return TException(piece.module_name, piece.name, field_dict, base=base_t)


_meta_type_list = [
    name_mt,
    optional_mt,
    list_mt,
    field_mt,
    record_mt,
    exception_mt,
    ]


def make_meta_type_name_to_type():
    return {
        t.name: t
        for t in _meta_type_list
        }


def add_types_to_pyobj_creg_cache(pyobj_creg, name_to_type):
    for name, t in name_to_type.items():
        piece = builtin_mt(name)
        pyobj_creg.add_to_cache(piece, t)


# piece: builtin_mt
def resolve_builtin_mt(name_to_type, piece):
    return name_to_type[piece.name]


# Register builtin_mt with phony piece - can not be registered as usual because of dependency loop.
def register_builtin_mt(mosaic, pyobj_creg):
    builtin_ref = phony_ref(builtin_mt.name)
    builtin_mt_piece = builtin_mt(builtin_mt.name)
    mosaic.add_to_cache(builtin_mt_piece, builtin_mt, builtin_ref)
    pyobj_creg.add_to_cache(builtin_mt_piece, builtin_mt)
    pyobj_creg.register_actor(builtin_mt, resolve_builtin_mt)


def register_pyobj_creg_mt_actors(pyobj_creg):
    # name_mt does not produce a type, it is removed by type module loader.
    pyobj_creg.register_actor(optional_mt, optional_from_piece, pyobj_creg=pyobj_creg)
    pyobj_creg.register_actor(list_mt, list_from_piece, pyobj_creg=pyobj_creg)
    pyobj_creg.register_actor(record_mt, record_from_piece, pyobj_creg=pyobj_creg)
    pyobj_creg.register_actor(exception_mt, exception_from_piece, pyobj_creg=pyobj_creg)
