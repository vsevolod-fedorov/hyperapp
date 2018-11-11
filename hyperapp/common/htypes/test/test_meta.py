# test types serialization

import logging
import pytest
import unittest

from hyperapp.common.htypes import (
    TPrimitive,
    tNone,
    tString,
    tBinary,
    tInt,
    tBool,
    tDateTime,
    TOptional,
    Field,
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
    make_root_type_namespace,
    TypeNamespace,
    t_ref,
    builtin_ref_t,
    meta_ref_t,
    )
from hyperapp.common import cdr_coders  # register codec
from hyperapp.common.builtin_types_registry import make_builtin_types_registry
from hyperapp.common.ref_registry import RefRegistry
from hyperapp.common.ref_resolver import RefResolver
from hyperapp.common.type_resolver import TypeResolver

log = logging.getLogger(__name__)


@pytest.fixture
def types():
    return make_root_type_namespace()


@pytest.fixture
def ref_registry(types):
    return RefRegistry(types)


@pytest.fixture
def type_resolver(types, ref_registry):
    builtin_types_registry = make_builtin_types_registry()
    ref_resolver = RefResolver(types)
    ref_resolver.add_source(ref_registry)
    return TypeResolver(types, builtin_types_registry, ref_resolver)


@pytest.fixture
def builtin_ref(ref_registry):

    def make(name):
        ref = ref_registry.register_object(builtin_ref_t(['basic', name]))
        return t_ref(ref)

    return make


@pytest.fixture
def type_ref(ref_registry):

    def make(name, meta_type):
        rec = meta_ref_t(
            name=name,
            random_salt=name.encode() + b'-salt',
            type=meta_type,
            )
        return ref_registry.register_object(rec)

    return make


@pytest.fixture
def resolve(type_resolver, type_ref):

    def act(name, meta_data):
        ref = type_ref(name, meta_data)
        return type_resolver.resolve(ref)

    return act


def test_optional(builtin_ref, resolve):
    data = t_optional_meta(builtin_ref('string'))
    t = resolve('some_optional', data)
    assert t == TOptional(tString)
    assert t.base_t is tString


def test_list(builtin_ref, resolve):
    data = t_list_meta(t_optional_meta(builtin_ref('datetime')))
    t = resolve('some_list', data)
    assert t == TList(TOptional(tDateTime))


def test_record(builtin_ref, resolve):
    data = t_record_meta([
        t_field_meta('int_field', builtin_ref('int')),
        t_field_meta('string_list_field', t_list_meta(builtin_ref('string'))),
        t_field_meta('bool_optional_field', t_optional_meta(builtin_ref('bool'))),
        ])
    t = resolve('some_record', data)
    assert t == TRecord([
        Field('int_field', tInt),
        Field('string_list_field', TList(tString)),
        Field('bool_optional_field', TOptional(tBool)),
        ])


def test_based_record(builtin_ref, type_ref, resolve):
    base_record_data = t_record_meta([
        t_field_meta('int_field', builtin_ref('int')),
        ])
    base_record_ref = t_ref(type_ref('some_base_record', base_record_data))

    record_data = t_record_meta([
        t_field_meta('string_field', builtin_ref('string')),
        ], base=base_record_ref)
    t = resolve('some_record', record_data)
    assert t == TRecord([
        Field('int_field', tInt),
        Field('string_field', tString),
        ])


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
    assert THierarchy('test_hierarchy').matches(hierarchy)
    class_a = resolve('some_class_a', class_a_data)
    class_b = resolve('some_class_b', class_b_data)
    assert class_a == TClass(hierarchy, 'class_a', TRecord([Field('field_a_1', tString)]))
    assert class_b == TClass(hierarchy, 'class_b', TRecord([Field('field_a_1', tString),
                                                            Field('field_b_1', TList(tInt))]))


class MetaTypeTest(unittest.TestCase):

    __test__ = False

    def test_interface(self):
        data = t_interface_meta(None, [
            t_command_meta('request', 'request_one',
                           [t_field_meta('req_param1', builtin_ref('string'))],
                           [t_field_meta('req_result1', t_list_meta(builtin_ref('int')))]),
            t_command_meta('notification', 'notification_one',
                           [t_field_meta('noti_param1', t_optional_meta(builtin_ref('bool'))),
                            t_field_meta('noti_param2', builtin_ref('datetime'))]),
            t_command_meta('request', 'request_open', [],
                           [t_field_meta('result', t_optional_meta(builtin_ref('int')))]),
            ])
        t = self.resolve(data, full_name=['test_meta', 'test_iface'])
        self.assertEqual(Interface(['test_meta', 'test_iface'],
            commands=[
                RequestCmd(['test_meta', 'test_iface', 'request_one'], 'request_one',
                           [Field('req_param1', tString)],
                           [Field('req_result1', TList(tInt))]),
                NotificationCmd(['test_meta', 'test_iface', 'notification_one'], 'notification_one',
                                [Field('noti_param1', TOptional(tBool)),
                                 Field('noti_param2', tDateTime)]),
                RequestCmd(['test_meta', 'test_iface', 'request_open'], 'request_open', [],
                           [Field('result', TOptional(tInt))]),
            ]), t)
