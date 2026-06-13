# test types serialization

import logging
import pytest

from hyperapp.boot.htypes import (
    TPrimitive,
    tNone,
    tString,
    tBinary,
    tInt,
    tBool,
    tDateTime,
    TOptional,
    TRecord,
    TException,
    TList,
    builtin_mt,
    optional_mt,
    list_mt,
    field_mt,
    record_mt,
    exception_mt,
    )
from hyperapp.boot.htypes.builtins import make_builtin_name_to_type
from hyperapp.boot.htypes.meta_type import (
    make_meta_type_name_to_type,
    add_types_to_pyobj_creg_cache,
    register_builtin_mt,
    register_pyobj_creg_mt_actors,
    )
from hyperapp.boot.register_coders import register_coders

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    ]


@pytest.fixture
def builtin_name_to_type():
    return {
        **make_builtin_name_to_type(),
        **make_meta_type_name_to_type(),
        }


@pytest.fixture
def init(mosaic, web, pyobj_creg, builtin_name_to_type):
    pyobj_creg.init(mosaic, web)
    add_types_to_pyobj_creg_cache(pyobj_creg, builtin_name_to_type)
    register_builtin_mt(mosaic, pyobj_creg)
    register_pyobj_creg_mt_actors(pyobj_creg)
    register_coders()


def test_optional(mosaic, pyobj_creg, init):
    base_ref = mosaic.put(builtin_mt('string'))
    piece = optional_mt(base_ref)
    t = pyobj_creg.animate(piece)
    assert t == TOptional(tString)
    assert t.base_t is tString


def test_list(mosaic, pyobj_creg, init):
    element_ref = mosaic.put(builtin_mt('int'))
    piece = list_mt(element_ref)
    t = pyobj_creg.animate(piece)
    assert t == TList(tInt)


def test_list_opt(mosaic, pyobj_creg, init):
    base_ref = mosaic.put(builtin_mt('datetime'))
    element_ref = mosaic.put(optional_mt(base_ref))
    piece = list_mt(element_ref)
    t = pyobj_creg.animate(piece)
    assert t == TList(TOptional(tDateTime))


def test_record(mosaic, pyobj_creg, init):
    module_name = 'test_record'
    name = 'some_test_record'
    string_list_mt = list_mt(mosaic.put(builtin_mt('string')))
    bool_opt_mt = optional_mt(mosaic.put(builtin_mt('bool')))
    piece = record_mt(module_name, name, None, (
        field_mt('int_field', mosaic.put(builtin_mt('int'))),
        field_mt('string_list_field', mosaic.put(string_list_mt)),
        field_mt('bool_optional_field', mosaic.put(bool_opt_mt)),
        ))
    t = pyobj_creg.animate(piece)
    assert t == TRecord(module_name, name, {
        'int_field': tInt,
        'string_list_field': TList(tString),
        'bool_optional_field': TOptional(tBool),
        })


def test_based_record(mosaic, pyobj_creg, init):
    module_name = 'test_based_record'
    base_piece = record_mt(module_name, 'some_base_record', None, (
        field_mt('int_field', mosaic.put(builtin_mt('int'))),
        ))
    base_ref = mosaic.put(base_piece)
    name = 'some_test_record'
    piece = record_mt(module_name, name, base_ref, (
        field_mt('string_field', mosaic.put(builtin_mt('string'))),
        ))
    t = pyobj_creg.animate(piece)
    assert t == TRecord(module_name, name, {
        'int_field': tInt,
        'string_field': tString,
        })


def test_empty_record(mosaic, pyobj_creg, init):
    module_name = 'test_empty_record'
    name_1 = 'record_1'
    piece_1 = record_mt(module_name, name_1, None, ())
    t_1 = pyobj_creg.animate(piece_1)
    assert t_1 == TRecord(module_name, name_1, {})

    name_2 = 'record_2'
    piece_2 = record_mt(module_name, name_2, None, ())
    t_2 = pyobj_creg.animate(piece_2)
    assert t_2 == TRecord(module_name, name_2, {})

    assert t_1 != t_2


def test_exception(mosaic, pyobj_creg, init):
    module_name = 'test_exception'
    string_list_mt = list_mt(mosaic.put(builtin_mt('string')))
    bool_opt_mt = optional_mt(mosaic.put(builtin_mt('bool')))
    module_name = 'test'
    name = 'some_test_exception'
    piece = exception_mt(module_name, name, None, (
        field_mt('int_field', mosaic.put(builtin_mt('int'))),
        field_mt('string_list_field', mosaic.put(string_list_mt)),
        field_mt('bool_optional_field', mosaic.put(bool_opt_mt)),
        ))
    t = pyobj_creg.animate(piece)
    assert t == TException(module_name, name, {
        'int_field': tInt,
        'string_list_field': TList(tString),
        'bool_optional_field': TOptional(tBool),
        })


def test_based_exception(mosaic, pyobj_creg, init):
    module_name = 'test_based_exception'
    base_piece = exception_mt(module_name, 'some_base_exception', None, (
        field_mt('int_field', mosaic.put(builtin_mt('int'))),
        ))
    base_ref = mosaic.put(base_piece)
    name = 'some_test_exception'
    piece = exception_mt(module_name, name, base_ref, (
        field_mt('string_field', mosaic.put(builtin_mt('string'))),
        ))
    t = pyobj_creg.animate(piece)
    assert t == TException(module_name, name, {
        'int_field': tInt,
        'string_field': tString,
        })


def test_empty_exception(mosaic, pyobj_creg, init):
    module_name = 'test_empty_exception'

    name_1 = 'exception_1'
    piece_1 = exception_mt(module_name, name_1, None, ())
    t_1 = pyobj_creg.animate(piece_1)
    assert t_1 == TException(module_name, name_1, {})

    name_2 = 'exception_2'
    piece_2 = exception_mt(module_name, name_2, None, ())
    t_2 = pyobj_creg.animate(piece_2)
    assert t_2 == TException('test', name_2, {})

    assert t_1 != t_2
