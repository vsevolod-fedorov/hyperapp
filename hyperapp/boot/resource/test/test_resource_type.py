import logging
from pathlib import Path
from unittest.mock import Mock

import pytest

from hyperapp.boot.htypes import tInt, tString, TOptional, TList, TRecord
from hyperapp.boot.htypes.meta_type import builtin_mt, optional_mt, list_mt, field_mt, record_mt
from hyperapp.boot.htypes.partial import partial_param_t, partial_t

log = logging.getLogger(__name__)


pytest_plugins = [
    'hyperapp.boot.test.services',
    'hyperapp.boot.resource.test.services',
    ]

TEST_RESOURCES_DIR = Path(__file__).parent / 'test_resources'


@pytest.fixture
def test_resources_dir():
    return TEST_RESOURCES_DIR


def mock_ctx(names):
    def resolve_to_ref(name):
        return names[name]

    return Mock(resolve_to_ref=resolve_to_ref)


def test_definition_type_partial(resource_type_producer):
    resource_t = partial_t
    resource_type = resource_type_producer(resource_t)
    log.info("definition_t: %r", resource_type.definition_t)
    assert resource_type.definition_t == TRecord('builtin', 'partial_def', {
        'function': tString,
        'params': TList(TRecord('builtin', 'partial_param_def', {
            'name': tString,
            'value': tString,
            })),
        })


@pytest.fixture
def a_record_t(pyobj_creg, mosaic):
    ref_mt = builtin_mt('ref')
    ref_opt_mt = optional_mt(mosaic.put(ref_mt))
    base_record_mt = record_mt('a_module', 'base_record', base=None, fields=(
        field_mt('a_ref_opt', mosaic.put(ref_opt_mt)),
        ))
    ref_list_mt = list_mt(mosaic.put(ref_mt))
    a_record_mt = record_mt('a_module', 'a_record', base=mosaic.put(base_record_mt), fields=(
        field_mt('a_ref_list', mosaic.put(ref_list_mt)),
        ))
    return  pyobj_creg.animate(a_record_mt)


def test_definition_type_based(resource_type_factory, a_record_t):
    resource_type = resource_type_factory(a_record_t)
    log.info("definition_t: %r", resource_type.definition_t)
    expected_base_t = TRecord('a_module', 'base_record_def', {
        'a_ref_opt': TOptional(tString),
        })
    assert resource_type.definition_t == TRecord('a_module', 'a_record_def', {
        'a_ref_opt': TOptional(tString),
        'a_ref_list': TList(tString),
        }, base=expected_base_t)


def test_mapper(resource_type_factory):
    resource_t = partial_t
    resource_type = resource_type_factory(resource_t)
    log.info("mapper: %r", resource_type._mapper)


def test_from_dict_partial(resource_type_producer):
    resource_t = partial_t
    resource_type = resource_type_producer(resource_t)
    log.info("definition_t: %r", resource_type.definition_t)
    definition_dict = {
        'function': 'some_function',
        'params': {
            'param_1': 'value_1',
            'param_2': 'value_2',
            },
        }
    definition = resource_type.from_dict(definition_dict)
    log.info("definition: %r", definition)
    param_t = resource_type.definition_t.fields['params'].element_t
    assert definition == resource_type.definition_t(
        function='some_function',
        params=(
            param_t('param_1', 'value_1'),
            param_t('param_2', 'value_2'),
            ),
        )


def test_from_dict_based(resource_type_factory, a_record_t):
    resource_type = resource_type_factory(a_record_t)
    log.info("definition_t: %r", resource_type.definition_t)
    definition_dict = {
        'a_ref_opt': 'some-int',
        'a_ref_list': ['string-1', 'string-2'],
        }
    definition = resource_type.from_dict(definition_dict)
    log.info("definition: %r", definition)
    assert definition == resource_type.definition_t(
        a_ref_opt='some-int',
        a_ref_list=('string-1', 'string-2'),
        )


def test_to_dict_partial(resource_type_producer):
    resource_t = partial_t
    resource_type = resource_type_producer(resource_t)
    param_t = resource_type.definition_t.fields['params'].element_t
    definition = resource_type.definition_t(
        function='some_function',
        params=(
            param_t('param_1', 'value_1'),
            param_t('param_2', 'value_2'),
            ),
        )
    definition_dict = resource_type.to_dict(definition)
    log.info("definition dict: %r", definition_dict)
    assert definition_dict == {
        'function': 'some_function',
        'params': {
            'param_1': 'value_1',
            'param_2': 'value_2',
            },
        }


def test_to_dict_based(resource_type_factory, a_record_t):
    resource_type = resource_type_factory(a_record_t)
    definition = resource_type.definition_t(
        a_ref_opt='some-int',
        a_ref_list=('string-1', 'string-2'),
        )
    definition_dict = resource_type.to_dict(definition)
    log.info("definition dict: %r", definition_dict)
    assert definition_dict == {
        'a_ref_opt': 'some-int',
        'a_ref_list': ['string-1', 'string-2'],
        }


def test_resolve_definition_partial(mosaic, resource_type_producer):
    resource_t = partial_t
    resource_type = resource_type_producer(resource_t)
    param_t = resource_type.definition_t.fields['params'].element_t
    definition = resource_type.definition_t(
        function='some_function',
        params=(
            param_t('param_1', 'value_1'),
            param_t('param_2', 'value_2'),
            ),
        )
    names = {
        'some_function': mosaic.put('some_function'),
        'value_1': mosaic.put(111),
        'value_2': mosaic.put(222),
        }
    ctx = mock_ctx(names)
    resource, sources = resource_type.resolve(definition, ctx)
    log.info('Resolved resource: %r', resource)
    assert resource == resource_t(
        function=names['some_function'],
        params=(
            partial_param_t('param_1', names['value_1']),
            partial_param_t('param_2', names['value_2']),
        ),
    )


def test_resolve_definition_based(mosaic, resource_type_factory, a_record_t):
    resource_type = resource_type_factory(a_record_t)
    definition = resource_type.definition_t(
        a_ref_opt='some-int',
        a_ref_list=('string-1', 'string-2'),
        )
    names = {
        'some-int': mosaic.put(123),
        'string-1': mosaic.put('some string 1'),
        'string-2': mosaic.put('some string 2'),
        }
    ctx = mock_ctx(names)
    resource, sources = resource_type.resolve(definition, ctx)
    log.info('Resolved resource: %r', resource)
    assert resource == a_record_t(
        a_ref_opt=names['some-int'],
        a_ref_list=(names['string-1'], names['string-2']),
    )


def test_reverse_resolve_definition_partial(mosaic, resource_type_producer):
    resource_t = partial_t
    resource_type = resource_type_producer(resource_t)
    names = {
        'some_function': mosaic.put('some_function'),
        'value_1': mosaic.put(111),
        'value_2': mosaic.put(222),
        }
    reverse_names = {
        value: key for key, value in names.items()
        }
    resource = resource_t(
        function=names['some_function'],
        params=(
            partial_param_t('param_1', names['value_1']),
            partial_param_t('param_2', names['value_2']),
            ),
        )

    def reverse_resolve_name(name):
        return reverse_names[name]

    definition = resource_type.reverse_resolve(resource, reverse_resolve_name, TEST_RESOURCES_DIR)
    log.info('Resolved definition: %r', definition)
    param_t = resource_type.definition_t.fields['params'].element_t
    assert definition == resource_type.definition_t(
        function='some_function',
        params=(
            param_t('param_1', 'value_1'),
            param_t('param_2', 'value_2'),
        ),
    )


def _test_reverse_resolve_definition_based(mosaic, resource_type_factory, a_record_t):
    resource_type = resource_type_factory(a_record_t)
    names = {
        'some-value': mosaic.put('some value'),
        'other-1': mosaic.put(111),
        'other-2': mosaic.put(222),
        }
    reverse_names = {
        value: key for key, value in names.items()
        }
    resource = resource_t(
        a_ref_opt=names['some-value'],
        a_ref_list=(names['other-1'], names['other-2']),
        )

    def reverse_resolve_name(name):
        return reverse_names[name]

    definition = resource_type.reverse_resolve(resource, reverse_resolve_name, TEST_RESOURCES_DIR)
    log.info('Resolved definition: %r', definition)
    assert definition == resource_type.definition_t(
        a_ref_opt='some-value',
        a_ref_list=('other-1', 'other-2'),
        )


def test_resolve_definition_empty_inherited_record(pyobj_creg, mosaic, resource_type_factory):
    string_mt = builtin_mt('string')
    ref_mt = builtin_mt('ref')
    ref_list_mt = list_mt(mosaic.put(ref_mt))
    base_record_mt = record_mt('a_module', 'base_record', base=None, fields=(
        field_mt('a_string', mosaic.put(string_mt)),
        field_mt('a_ref', mosaic.put(ref_mt)),
        field_mt('a_ref_list', mosaic.put(ref_list_mt)),
        ))
    a_record_mt = record_mt('a_module', 'a_record', base=mosaic.put(base_record_mt), fields=())
    a_record_t = pyobj_creg.animate(a_record_mt)
    resource_type = resource_type_factory(a_record_t)
    definition = resource_type.definition_t(
        a_string='some string',
        a_ref='some-value',
        a_ref_list=('some-item',),
        )
    names = {
        'some-value': mosaic.put('some value'),
        'some-item': mosaic.put('some item'),
        }
    ctx = mock_ctx(names)
    resource, sources = resource_type.resolve(definition, ctx)
    log.info('Resolved resource: %r', resource)
    assert resource == a_record_t(
        a_string='some string',
        a_ref=names['some-value'],
        a_ref_list=(names['some-item'],),
        )
