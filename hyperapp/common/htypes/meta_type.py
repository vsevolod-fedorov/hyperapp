# meta type is type for storing types themselves as data

from .htypes import (
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
from .hyper_ref import ref_t
from .interface import Request, Notification, Interface


builtin_mt = TRecord('builtin_mt', {
    'name': tString,
    })


# Produced by type module parsed, removed by loader.
name_mt = TRecord('name_mt', {
    'name': tString,
    })


name_wrapped_mt = TRecord('name_wrapped_mt', {
    'name': tString,
    'type': ref_t,
    })


def name_wrapped_from_piece(rec, type_code_registry, name):
    return type_code_registry.invite(rec.type, type_code_registry, rec.name)


optional_mt = TRecord('optional_mt', {
    'base': ref_t,
    })


def optional_from_piece(rec, type_code_registry, name):
    base_t = type_code_registry.invite(rec.base, type_code_registry, None)
    return TOptional(base_t)


list_mt = TRecord('list_mt', {
    'element': ref_t,
    })


def list_from_piece(rec, type_code_registry, name):
    element_t = type_code_registry.invite(rec.element, type_code_registry, None)
    return TList(element_t)


field_mt = TRecord('field_mt', {
    'name': tString,
    'type': ref_t,
    })

record_mt = TRecord('record_mt', {
    'base': TOptional(ref_t),
    'fields': TList(field_mt),
    })


def _field_from_piece(rec, type_code_registry):
    t = type_code_registry.invite(rec.type, type_code_registry, None)
    return (rec.name, t)


def _field_dict_from_piece_list(field_list, type_code_registry):
    return dict(_field_from_piece(field, type_code_registry) for field in field_list)


def record_from_piece(rec, type_code_registry, name):
    if rec.base is not None:
        base_t = type_code_registry.invite(rec.base, type_code_registry, None)
        assert isinstance(base_t, TRecord), f"Record base is not a record: {base_t}"
    else:
        base_t = None
    field_dict = _field_dict_from_piece_list(rec.fields, type_code_registry)
    return TRecord(name, field_dict, base=base_t)


request_mt = TRecord('request_mt', {
    'method_name': tString,
    'param_fields': TList(field_mt),
    'response_fields': TList(field_mt),
    })

notification_mt = TRecord('notification_mt', {
    'method_name': tString,
    'param_fields': TList(field_mt),
    })

interface_mt = TRecord('interface_mt', {
    'base': TOptional(ref_t),
    'method_list': TList(ref_t),
    })


def request_from_piece(piece, type_code_registry, name, mosaic, types):
    # name here is interface name.
    params_ref = mosaic.put(record_mt(None, piece.param_fields))
    named_params_ref = mosaic.put(name_wrapped_mt(f'{name}_{piece.method_name}_params', params_ref))
    params_record_t = types.resolve(named_params_ref)

    response_ref = mosaic.put(record_mt(None, piece.response_fields))
    named_response_ref = mosaic.put(name_wrapped_mt(f'{name}_{piece.method_name}_response', response_ref))
    response_record_t = types.resolve(named_response_ref)

    return Request(piece.method_name, params_record_t, response_record_t)


def notification_from_piece(piece, type_code_registry, name, mosaic, types):
    params_ref = mosaic.put(record_mt(None, piece.param_fields))
    named_params_ref = mosaic.put(name_wrapped_mt(f'{name}_{piece.method_name}_params', params_ref))
    params_record_t = types.resolve(named_params_ref)

    return Notification(piece.method_name, params_record_t)


def _method_iter_from_field_list(method_ref_list, type_code_registry, name):
    for method_ref in method_ref_list:
        yield type_code_registry.invite(method_ref, type_code_registry, name)


def interface_from_piece(piece, type_code_registry, name):
    if piece.base is not None:
        base_t = type_code_registry.invite(piece.base, type_code_registry, None)
        assert isinstance(base_t, Interface), f"Interface base is not a Interface: {base_t}"
    else:
        base_t = None
    method_list = list(_method_iter_from_field_list(piece.method_list, type_code_registry, name))
    return Interface(name, base_t, method_list)


def register_builtin_meta_types(types):
    types.register_builtin_type(name_mt)
    types.register_builtin_type(name_wrapped_mt)
    types.register_builtin_type(optional_mt)
    types.register_builtin_type(list_mt)
    types.register_builtin_type(field_mt)
    types.register_builtin_type(record_mt)
    types.register_builtin_type(request_mt)
    types.register_builtin_type(notification_mt)
    types.register_builtin_type(interface_mt)


def register_meta_types(mosaic, types, type_code_registry):
    # name_mt does not produce a type, it is removed by type module loader.
    type_code_registry.register_actor(name_wrapped_mt, name_wrapped_from_piece)
    type_code_registry.register_actor(optional_mt, optional_from_piece)
    type_code_registry.register_actor(list_mt, list_from_piece)
    type_code_registry.register_actor(record_mt, record_from_piece)
    type_code_registry.register_actor(request_mt, request_from_piece, mosaic, types)
    type_code_registry.register_actor(notification_mt, notification_from_piece, mosaic, types)
    type_code_registry.register_actor(interface_mt, interface_from_piece)
