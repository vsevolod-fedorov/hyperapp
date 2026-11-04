from pathlib import Path
from types import SimpleNamespace

import pytest

from hyperapp.boot.boot import boot_services, load_projects_resources, parse_path


TEST_DIR = Path(__file__).parent.resolve()


@pytest.fixture
def resources():
    svc = boot_services()
    loaded = load_projects_resources(
        svc.pyobj_creg, svc.mosaic, svc.source_path, svc.builtin_name_to_type,
        svc.builtin_name_to_service, svc.resource_type_producer, TEST_DIR / 'projects.yaml')

    def piece(path):
        return loaded[parse_path(path)]

    module = svc.pyobj_creg.animate(piece('base:system/system:system.module'))
    return SimpleNamespace(
        svc=svc, piece=piece, setup=module.setup_system,
        config=piece('base:config:config'),
        factory=piece('base:system/system:subsystem_factory.service'),
        pickers=piece('base:assoc_pickers:assoc_pickers.service'),
        bundler=piece('base:bundler:bundler.service'),
        )


# Use the real bundler to observe its injected picker list, rather than inspecting adapter partials.
def _record_picker_calls(calls):
    def picker(value):
        calls.append(value)
        return []
    return picker


def test_subsystems_isolate_mutable_services_and_transitive_dependencies(resources):
    configs = [resources.config]
    parent = resources.setup(configs)
    factory = parent.animate(resources.factory)
    configs.clear()  # The factory must retain the declarations independently of this input list.
    parent_calls = []
    parent_pickers = parent.animate(resources.pickers)
    parent_pickers.append(_record_picker_calls(parent_calls))
    parent_bundler = parent.animate(resources.bundler)

    first = factory()
    first_pickers = first.animate(resources.pickers)
    assert first_pickers == []
    first_calls = []
    first_pickers.append(_record_picker_calls(first_calls))
    first_bundler = first.animate(resources.bundler)
    second = factory()
    second_pickers = second.animate(resources.pickers)
    assert second_pickers == []
    assert second_pickers is not first_pickers
    assert first_pickers is not parent_pickers
    assert first.animate(resources.pickers) is first_pickers

    ref = resources.svc.mosaic.put(resources.pickers)
    first_bundler(ref)
    assert first_calls
    assert parent_calls == []
    first_calls.clear()
    parent_bundler(ref)
    assert parent_calls
    assert first_calls == []
    parent_calls.clear()
    second.animate(resources.bundler)(ref)
    assert first_calls == parent_calls == []


def test_scoped_instances_reach_dependencies_but_are_not_inherited(resources):
    calls = []
    scoped_pickers = [_record_picker_calls(calls)]
    parent = resources.setup([resources.config], {resources.pickers: scoped_pickers})
    factory = parent.animate(resources.factory)
    child_pickers = []
    child = factory({resources.pickers: child_pickers})
    assert parent.animate(resources.pickers) is scoped_pickers
    assert child.animate(resources.pickers) is child_pickers
    child_calls = []
    child_pickers.append(_record_picker_calls(child_calls))

    ref = resources.svc.mosaic.put(resources.pickers)
    child.animate(resources.bundler)(ref)
    assert child_calls
    assert calls == []
    child_calls.clear()
    parent.animate(resources.bundler)(ref)
    assert calls
    assert child_calls == []
    calls.clear()

    sibling = factory()
    grandchild = child.animate(resources.factory)()
    for subsystem in (sibling, grandchild):
        assert subsystem.animate(resources.pickers) == []
        subsystem.animate(resources.bundler)(ref)
    assert calls == child_calls == []


def test_subsystems_rebuild_config_and_registry_actors(resources):
    parent = resources.setup([resources.config])
    factory = parent.animate(resources.factory)
    config_service = resources.piece('base:system/system:service_config_creg.service')
    registry_service = resources.piece('base:resource/name:resource_name_creg.service')
    module_piece = resources.piece('base:assoc_pickers:assoc_pickers.module')
    module_type = resources.svc.builtin_name_to_type['python_module']
    parent_config = parent.animate(config_service).animate(registry_service)
    parent_registry = parent.animate(registry_service)
    assert parent_registry.animate(module_piece, None) == 'assoc_pickers.module'
    parent_config.config.clear()
    parent_registry.update_resolved_config({module_type: lambda piece, name_of: 'parent mutation'})
    assert parent_registry.animate(module_piece, None) == 'parent mutation'

    first = factory()
    first_config = first.animate(config_service).animate(registry_service)
    first_registry = first.animate(registry_service)
    assert first_config.config
    assert first_config is not parent_config
    assert first_registry.animate(module_piece, None) == 'assoc_pickers.module'
    first_config.config.clear()
    first_registry.update_resolved_config({module_type: lambda piece, name_of: 'child mutation'})

    second = factory()
    second_config = second.animate(config_service).animate(registry_service)
    second_registry = second.animate(registry_service)
    assert second_config.config
    assert second_config is not first_config
    assert second_registry.animate(module_piece, None) == 'assoc_pickers.module'
    assert first_registry.animate(module_piece, None) == 'child mutation'
    assert parent_registry.animate(module_piece, None) == 'parent mutation'
