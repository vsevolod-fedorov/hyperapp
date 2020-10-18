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
    TClass,
    THierarchy,
    RequestCmd,
    NotificationCmd,
    Interface,
    tMetaType,
    t_named,
    t_optional_meta,
    t_list_meta,
    t_field_meta,
    t_record_meta,
    t_hierarchy_meta,
    t_hierarchy_class_meta,
    t_command_meta,
    t_interface_meta,
    make_meta_type_registry,
    t_ref,
    builtin_ref_t,
    meta_ref_t,
    register_builtin_types,
    )
from hyperapp.common import cdr_coders  # register codec
from hyperapp.common.ref_registry import RefRegistry
from hyperapp.common.ref_resolver import RefResolver
from hyperapp.common.type_system import TypeSystem

log = logging.getLogger(__name__)


@pytest.fixture
def ref_resolver():
    return RefResolver()


@pytest.fixture
def types(ref_resolver):
    return TypeSystem(ref_resolver)


@pytest.fixture
def ref_registry(ref_resolver, types):
    registry = RefRegistry(types)
    ref_resolver.add_source(registry)
    register_builtin_types(registry, types)
    return registry


@pytest.fixture
def builtin_ref(ref_registry):

    def make(name):
        ref = ref_registry.register_object(builtin_ref_t(name))
        return t_ref(ref)

    return make


@pytest.fixture
def type_ref(ref_registry):

    def make(name, meta_type):
        rec = meta_ref_t(
            name=name,
            type=meta_type,
            )
        return ref_registry.register_object(rec)

    return make


@pytest.fixture
def resolve(types, type_ref):

    def resolve(name, meta_data):
        ref = type_ref(name, meta_data)
        return types.resolve(ref)

    return resolve


def test_optional(builtin_ref, resolve):
    data = t_optional_meta(builtin_ref('string'))
    t = resolve('some_optional', data)
    assert t.match(TOptional(tString))
    assert t.base_t is tString


def test_list(builtin_ref, resolve):
    data = t_list_meta(t_optional_meta(builtin_ref('datetime')))
    t = resolve('some_list', data)
    assert t.match(TList(TOptional(tDateTime)))


def test_record(builtin_ref, resolve):
    data = t_record_meta([
        t_field_meta('int_field', builtin_ref('int')),
        t_field_meta('string_list_field', t_list_meta(builtin_ref('string'))),
        t_field_meta('bool_optional_field', t_optional_meta(builtin_ref('bool'))),
        ])
    t = resolve('some_record', data)
    assert t.match(TRecord('some_record', OrderedDict([
        ('int_field', tInt),
        ('string_list_field', TList(tString)),
        ('bool_optional_field', TOptional(tBool)),
        ])))


def test_based_record(builtin_ref, type_ref, resolve):
    base_record_data = t_record_meta([
        t_field_meta('int_field', builtin_ref('int')),
        ])
    base_record_ref = t_ref(type_ref('some_base_record', base_record_data))

    record_data = t_record_meta([
        t_field_meta('string_field', builtin_ref('string')),
        ], base=base_record_ref)
    t = resolve('some_record', record_data)
    assert t.match(TRecord('some_record', OrderedDict([
        ('int_field', tInt),
        ('string_field', tString),
        ])))


def test_hierarchy(builtin_ref, type_ref, resolve):
    hierarchy_data = t_hierarchy_meta('test_hierarchy')
    hierarchy_ref = t_ref(type_ref('some_hierarchy', hierarchy_data))

    class_a_data = t_hierarchy_class_meta(hierarchy_ref, 'class_a', fields=[
        t_field_meta('field_a_1', builtin_ref('string')),
        ])
    class_a_ref = t_ref(type_ref('some_class_a', class_a_data))
    class_b_data = t_hierarchy_class_meta(hierarchy_ref, 'class_b', base=class_a_ref, fields=[
        t_field_meta('field_b_1', t_list_meta(builtin_ref('int'))),
        ])
    hierarchy = resolve('some_hierarchy', hierarchy_data)
    assert THierarchy('test_hierarchy').match(hierarchy)
    class_a = resolve('some_class_a', class_a_data)
    class_b = resolve('some_class_b', class_b_data)
    assert class_a.match(TClass(hierarchy, 'class_a', OrderedDict([('field_a_1', tString)])))
    assert class_b.match(TClass(hierarchy, 'class_b', OrderedDict([
        ('field_a_1', tString),
        ('field_b_1', TList(tInt)),
        ])))

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
