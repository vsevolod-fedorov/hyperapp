# test types serialization

from collections import OrderedDict
import logging
import pytest

from hyperapp.common.htypes import (
    TPrimitive,
    tNone,
    tString,
    tBinary,
    tInt,
    tBool,
    tDateTime,
    TOptional,
    TRecord,
    TList,
    RequestCmd,
    NotificationCmd,
    Interface,
    builtin_mt,
    name_wrapped_mt,
    optional_mt,
    list_mt,
    field_mt,
    record_mt,
    register_builtin_types,
    )
from hyperapp.common import cdr_coders  # register codec
from hyperapp.common.mosaic import Mosaic
from hyperapp.common.web import Web
from hyperapp.common.type_system import TypeSystem

log = logging.getLogger(__name__)


@pytest.fixture
def web():
    return Web()


@pytest.fixture
def types():
    return TypeSystem()


@pytest.fixture
def mosaic(web, types):
    mosaic = Mosaic(types)
    types.init_mosaic(mosaic)
    web.add_source(mosaic)
    register_builtin_types(types)
    return mosaic


def test_optional(types, mosaic):
    base_ref = mosaic.put(builtin_mt('string'))
    piece = optional_mt(base_ref)
    t = types.resolve(mosaic.put(piece))
    assert t.match(TOptional(tString))
    assert t.base_t is tString


def test_list(types, mosaic):
    element_ref = mosaic.put(builtin_mt('int'))
    piece = list_mt(element_ref)
    t = types.resolve(mosaic.put(piece))
    assert t.match(TList(tInt))


def test_list_opt(types, mosaic):
    base_ref = mosaic.put(builtin_mt('datetime'))
    element_ref = mosaic.put(optional_mt(base_ref))
    piece = list_mt(element_ref)
    t = types.resolve(mosaic.put(piece))
    assert t.match(TList(TOptional(tDateTime)))


def test_record(types, mosaic):
    string_list_mt = list_mt(mosaic.put(builtin_mt('string')))
    bool_opt_t = optional_mt(mosaic.put(builtin_mt('bool')))
    piece = record_mt(None, [
        field_mt('int_field', mosaic.put(builtin_mt('int'))),
        field_mt('string_list_field', mosaic.put(string_list_mt)),
        field_mt('bool_optional_field', mosaic.put(bool_opt_t)),
        ])
    name = 'some_test_record'
    named_piece = name_wrapped_mt(name, mosaic.put(piece))
    t = types.resolve(mosaic.put(named_piece))
    assert t.match(TRecord(name, {
        'int_field': tInt,
        'string_list_field': TList(tString),
        'bool_optional_field': TOptional(tBool),
        }))


def test_based_record(types, mosaic):
    base_piece = record_mt(None, [
        field_mt('int_field', mosaic.put(builtin_mt('int'))),
        ])
    named_base_piece = name_wrapped_mt('some_base_record', mosaic.put(base_piece))
    named_base_ref = mosaic.put(named_base_piece)
    piece = record_mt(named_base_ref, [
        field_mt('string_field', mosaic.put(builtin_mt('string'))),
        ])
    name = 'some_test_record'
    named_piece = name_wrapped_mt(name, mosaic.put(piece))
    t = types.resolve(mosaic.put(named_piece))
    assert t.match(TRecord(name, {
        'int_field': tInt,
        'string_field': tString,
        }))


def test_interface(builtin_ref, resolve):
    iface_data = t_interface_meta([
        t_command_meta('request', 'request_one',
                       [t_field_meta('req_param1', builtin_ref('string'))],
                       [t_field_meta('req_result1', t_list_meta(builtin_ref('int')))]),
        t_command_meta('notification', 'notification_one',
                       [t_field_meta('noti_param1', t_optional_meta(builtin_ref('bool'))),
                        t_field_meta('noti_param2', builtin_ref('datetime'))]),
        t_command_meta('request', 'request_open', [],
                       [t_field_meta('result', t_optional_meta(builtin_ref('int')))]),
        ])
    t = resolve('test_iface', iface_data)
    assert t.match(Interface(['test_iface'],
        commands=[
            RequestCmd(['test_iface', 'request_one'], 'request_one',
                       OrderedDict([('req_param1', tString)]),
                       OrderedDict([('req_result1', TList(tInt))])),
            NotificationCmd(['test_iface', 'notification_one'], 'notification_one',
                            OrderedDict([('noti_param1', TOptional(tBool)),
                                         ('noti_param2', tDateTime)])),
            RequestCmd(['test_iface', 'request_open'], 'request_open',
                       OrderedDict(),
                       OrderedDict([('result', TOptional(tInt))])),
        ]))


def test_based_interface(builtin_ref, type_ref, resolve):
    iface_a_data = t_interface_meta([
        t_command_meta('request', 'request_one',
                       [t_field_meta('req_param1', builtin_ref('string'))],
                       [t_field_meta('req_result1', t_list_meta(builtin_ref('int')))]),
        ])
    iface_a_ref = t_ref(type_ref('iface_a', iface_a_data))

    iface_b_data = t_interface_meta(base=iface_a_ref, commands=[
        t_command_meta('notification', 'notification_one',
                       [t_field_meta('noti_param1', t_optional_meta(builtin_ref('bool'))),
                        t_field_meta('noti_param2', builtin_ref('datetime'))]),
        ])

    iface_a = resolve('iface_a', iface_a_data)
    iface_b = resolve('iface_b', iface_b_data)
    assert iface_b.match(Interface(['iface_b'], base=iface_a, commands=[
        NotificationCmd(['iface_b', 'notification_one'], 'notification_one',
                        OrderedDict([('noti_param1', TOptional(tBool)),
                                     ('noti_param2', tDateTime)])),
        ]))
