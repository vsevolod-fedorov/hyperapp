import logging

import pytest

from hyperapp.boot.htypes import tInt, tString, TRecord
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


def test_type_module_resolve_local(pyobj_creg, resources_dir, loader):
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


def test_type_module_resolve_imports(pyobj_creg, resources_dir, loader):
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


def test_type_module_resolve_nested_imports(pyobj_creg, resources_dir, loader):
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


def test_type_module_resolve_mixed_imports(pyobj_creg, resources_dir, loader):
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


def test_type_module_resolve_builtin_type(pyobj_creg, resources_dir, loader):
    dir = 'resolve_builtin_type'
    source_text = resources_dir.joinpath(dir, 'sample.types').read_text()
    resources, sources = loader({'a-project': dir})
    piece = resources['a-project', ('sample.t',), 'sample_record']
    t = pyobj_creg.animate(piece)
    assert isinstance(t, TRecord)
    assert t.fields['an_int'] is tInt
    assert t.fields['a_string'] is tString
    assert sources[piece] == ('a-project', ('sample.t',), TextSource(source_text))
