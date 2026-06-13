import logging

import pytest

from hyperapp.boot.htypes import (
    tInt,
    tString,
    tBool,
    tDateTime,
    TOptional,
    TRecord,
    TException,
    TList,
    ref_t,
    )
from hyperapp.boot.resource.source import ResourceModuleSource, TextSource

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    'hyperapp.boot.resource.test.services',
    'hyperapp.boot.resource.test.loader',
    ]


@pytest.fixture
def resources_dir(test_dir):
    return test_dir / 'resources' / 'type_module'


def test_type_module(pyobj_creg, resources_dir, loader):
    dir = 'module'
    source_text = resources_dir.joinpath(dir, 'sample.types').read_text()
    resources, sources = loader({'a-project': dir})
    piece = resources['a-project', ('sample.t',), 'sample_record']
    t = pyobj_creg.animate(piece)
    assert isinstance(t, TRecord)
    assert sources[piece] == ('a-project', ('sample.t',), TextSource(source_text))
    record = t()  # Should not fail on assertion.


def test_resolve_local(pyobj_creg, resources_dir, loader):
    dir = 'resolve_local'
    source_text = resources_dir.joinpath(dir, 'sample.types').read_text()
    resources, sources = loader({'a-project': dir})
    outer_mt = resources['a-project', ('sample.t',), 'outer_record']
    outer_t = pyobj_creg.animate(outer_mt)
    inner_t = outer_t.fields['inner']
    inner_mt = pyobj_creg.actor_to_piece(inner_t)
    assert isinstance(outer_t, TRecord)
    assert isinstance(inner_t, TRecord)
    assert sources[outer_mt] == ('a-project', ('sample.t',), TextSource(source_text))
    assert sources[inner_mt] == ('a-project', ('sample.t',), TextSource(source_text))


def test_resolve_imports(pyobj_creg, resources_dir, loader):
    dir = 'resolve_imports'
    source_1_text = resources_dir.joinpath(dir, 'sample_1.types').read_text()
    source_2_text = resources_dir.joinpath(dir, 'sample_2.types').read_text()
    source_3_text = resources_dir.joinpath(dir, 'sample_3.types').read_text()
    resources, sources = loader({'a-project': dir})
    outer_mt = resources['a-project', ('sample_3.t',), 'outer_record']
    outer_t = pyobj_creg.animate(outer_mt)
    middle_t = outer_t.fields['middle']
    middle_mt = pyobj_creg.actor_to_piece(middle_t)
    inner_t = middle_t.fields['inner']
    inner_mt = pyobj_creg.actor_to_piece(inner_t)
    assert isinstance(outer_t, TRecord)
    assert isinstance(middle_t, TRecord)
    assert isinstance(inner_t, TRecord)
    assert inner_mt == resources['a-project', ('sample_1.t',), 'inner_record']
    assert sources[inner_mt] == ('a-project', ('sample_1.t',), TextSource(source_1_text))
    assert sources[middle_mt] == ('a-project', ('sample_2.t',), TextSource(source_2_text))
    assert sources[outer_mt] == ('a-project', ('sample_3.t',), TextSource(source_3_text))


def test_resolve_nested_imports(pyobj_creg, resources_dir, loader):
    dir = 'resolve_nested_imports'
    source_1_text = resources_dir.joinpath(dir, 'sub_2/sample_1.types').read_text()
    source_2_text = resources_dir.joinpath(dir, 'sub_1/sample_2.types').read_text()
    source_3_text = resources_dir.joinpath(dir, 'sub_1/sub_1_1/sample_3.types').read_text()
    resources, sources = loader({'a-project': dir})
    outer_mt = resources['a-project', ('sub_1', 'sub_1_1', 'sample_3.t'), 'outer_record']
    outer_t = pyobj_creg.animate(outer_mt)
    middle_t = outer_t.fields['middle']
    middle_mt = pyobj_creg.actor_to_piece(middle_t)
    inner_t = middle_t.fields['inner']
    inner_mt = pyobj_creg.actor_to_piece(inner_t)
    assert isinstance(outer_t, TRecord)
    assert isinstance(middle_t, TRecord)
    assert isinstance(inner_t, TRecord)
    assert inner_mt == resources['a-project', ('sub_2', 'sample_1.t'), 'inner_record']
    assert sources[inner_mt] == ('a-project', ('sub_2', 'sample_1.t'), TextSource(source_1_text))
    assert sources[middle_mt] == ('a-project', ('sub_1', 'sample_2.t'), TextSource(source_2_text))
    assert sources[outer_mt] == ('a-project', ('sub_1', 'sub_1_1', 'sample_3.t'), TextSource(source_3_text))


def test_resolve_mixed_imports(pyobj_creg, resources_dir, loader):
    dir = 'resolve_mixed_imports'
    source_1_text = resources_dir.joinpath(dir, 'sample_1.types').read_text()
    source_2_text = resources_dir.joinpath(dir, 'sample_2.types').read_text()
    source_3_text = resources_dir.joinpath(dir, 'sample_3.types').read_text()
    resources, sources = loader({'a-project': dir})
    outer_mt = resources['a-project', ('sample_3.t',), 'outer_record']
    outer_t = pyobj_creg.animate(outer_mt)
    middle_1_t = outer_t.fields['middle_1']
    middle_1_mt = pyobj_creg.actor_to_piece(middle_1_t)
    middle_2_t = outer_t.fields['middle_2']
    middle_2_mt = pyobj_creg.actor_to_piece(middle_2_t)
    inner_t = middle_1_t.fields['inner']
    assert inner_t is middle_2_t.fields['inner']
    inner_mt = pyobj_creg.actor_to_piece(inner_t)
    assert isinstance(outer_t, TRecord)
    assert isinstance(middle_1_t, TRecord)
    assert isinstance(middle_2_t, TRecord)
    assert isinstance(inner_t, TRecord)
    assert inner_mt == resources['a-project', ('sample_1.t',), 'inner_record']
    assert middle_1_mt == resources['a-project', ('sample_2.t',), 'middle_1_record']
    assert middle_2_mt == resources['a-project', ('sample_2',), 'middle_2_record']
    assert sources[inner_mt] == ('a-project', ('sample_1.t',), TextSource(source_1_text))
    assert sources[middle_1_mt] == ('a-project', ('sample_2.t',), TextSource(source_2_text))
    assert sources[middle_2_mt] == ('a-project', ('sample_2',), ResourceModuleSource('middle_2_record'))
    assert sources[outer_mt] == ('a-project', ('sample_3.t',), TextSource(source_3_text))


def test_resolve_builtin_type(pyobj_creg, resources_dir, loader):
    dir = 'resolve_builtin_type'
    source_text = resources_dir.joinpath(dir, 'sample.types').read_text()
    resources, sources = loader({'a-project': dir})
    piece = resources['a-project', ('sample.t',), 'sample_record']
    t = pyobj_creg.animate(piece)
    assert isinstance(t, TRecord)
    assert t.fields['an_int'] is tInt
    assert t.fields['a_string'] is tString
    assert sources[piece] == ('a-project', ('sample.t',), TextSource(source_text))


def test_types(pyobj_creg, loader):
    dir = 'types'
    resources, sources = loader({'a-project': dir})

    assert (pyobj_creg.animate(resources['a-project', ('module_1.t',), 'record_1'])
            == TRecord('module_1', 'record_1', {'int_field': tInt}))
    assert (pyobj_creg.animate(resources['a-project', ('module_1.t',), 'record_2'])
            == TRecord('module_1', 'record_2', {'int_field': tInt, 'string_field': tString}))

    assert (pyobj_creg.animate(resources['a-project', ('module_2.t',), 'record_3'])
            == TRecord('module_2', 'record_3', {'int_field': tInt, 'string_field': tString, 'datetime_field': tDateTime}))
    assert (pyobj_creg.animate(resources['a-project', ('module_2.t',), 'record_with_ref'])
            == TRecord('module_2', 'record_with_ref', {'ref_field': ref_t}))
    assert (pyobj_creg.animate(resources['a-project', ('module_2.t',), 'record_with_opt_ref'])
            == TRecord('module_2', 'record_with_opt_ref', {'opt_ref_field': TOptional(ref_t)}))

    assert (pyobj_creg.animate(resources['a-project', ('module_1.t',), 'empty_record_1'])
            == TRecord('module_1', 'empty_record_1'))
    assert (pyobj_creg.animate(resources['a-project', ('module_2.t',), 'empty_record_2'])
            == TRecord('module_2', 'empty_record_2'))
    assert (pyobj_creg.animate(resources['a-project', ('module_1.t',), 'empty_record_1'])
            != pyobj_creg.animate(resources['a-project', ('module_2.t',), 'empty_record_2']))


def test_same_instance(pyobj_creg, loader):
    dir = 'same_instance'
    resources, sources = loader({'a-project': dir})

    element_t = pyobj_creg.animate(resources['a-project', ('same_instance.t',), 'element'])
    container_t = pyobj_creg.animate(resources['a-project', ('same_instance.t',), 'container'])
    list_container_t = pyobj_creg.animate(resources['a-project', ('same_instance.t',), 'list_container'])
    opt_container_t = pyobj_creg.animate(resources['a-project', ('same_instance.t',), 'opt_container'])
    based_container_t = pyobj_creg.animate(resources['a-project', ('same_instance.t',), 'based_container'])

    element = element_t(key='arbitrary key')

    # Same types should resolve to same instances.
    assert container_t.fields['element_field'] == element_t
    assert container_t.fields['element_field'] is element_t
    # To be able to pass isinstance check on instantiation.
    value = container_t(element_field=element)
    assert isinstance(value, container_t)

    assert list_container_t.fields['element_field'].element_t is element_t
    _ = list_container_t(element_field=[element])

    assert opt_container_t.fields['element_field'].base_t is element_t
    _ = opt_container_t(element_field=element)

    assert based_container_t.base is container_t
    value = based_container_t(element_field=element)
    assert isinstance(value, container_t)


def test_exception(pyobj_creg, loader):
    dir = 'exceptions'
    resources, sources = loader({'a-project': dir})

    assert (pyobj_creg.animate(resources['a-project', ('exceptions.t',), 'exception_1'])
            == TException('exceptions', 'exception_1', {'int_field': tInt}))
    assert (pyobj_creg.animate(resources['a-project', ('exceptions.t',), 'exception_2'])
            == TException('exceptions', 'exception_2', {'int_field': tInt, 'string_field': tString}))
    assert (pyobj_creg.animate(resources['a-project', ('exceptions.t',), 'empty_exception'])
            == TException('exceptions', 'empty_exception', {}))
