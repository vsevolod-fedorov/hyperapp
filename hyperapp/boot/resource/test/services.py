from functools import partial

import pytest

from hyperapp.boot.htypes.builtins import make_builtin_name_to_type
from hyperapp.boot.htypes.meta_type import (
    make_meta_type_name_to_type,
    add_types_to_pyobj_creg_cache,
    register_builtin_mt,
    register_meta_types_actors,
    )
from hyperapp.boot.resource.resource_type import ResourceType
from hyperapp.boot.resource.resource_type_registry import make_type_to_resource_type
from hyperapp.boot.resource.pyobj_registry import register_resources_at_pyobj_creg
from hyperapp.boot.resource.builtin_service import make_builtin_name_to_service
# from hyperapp.boot.resource.legacy_type import load_legacy_type_resources
from hyperapp.boot.resource.resource_type_producer import resource_type_producer as resource_type_producer_fn
# from hyperapp.boot.resource.legacy_type import convert_builtin_types_to_dict
# from hyperapp.boot.project import BuiltinsProject, Project, load_texts
# from hyperapp.boot.test.hyper_types_namespace import HyperTypesNamespace
from hyperapp.boot.register_coders import register_coders


@pytest.fixture
def builtin_name_to_type():
    return {
        **make_builtin_name_to_type(),
        **make_meta_type_name_to_type(),
        }


@pytest.fixture
def builtin_name_to_service(pyobj_creg, mosaic, web):
    return make_builtin_name_to_service(pyobj_creg, mosaic, web)


@pytest.fixture
def init(pyobj_creg, mosaic, web, python_importer, builtin_name_to_type, builtin_name_to_service):
    pyobj_creg.init(mosaic, web)
    add_types_to_pyobj_creg_cache(pyobj_creg, builtin_name_to_type)
    register_builtin_mt(mosaic, pyobj_creg)
    register_meta_types_actors(pyobj_creg)
    register_resources_at_pyobj_creg(pyobj_creg, mosaic, web, python_importer, builtin_name_to_service)
    register_coders()


@pytest.fixture
def resource_type_factory(mosaic, web, pyobj_creg, init):
    return partial(ResourceType, mosaic, web, pyobj_creg)


@pytest.fixture
def type_to_resource_type():
    return make_type_to_resource_type()


@pytest.fixture
def resource_type_producer(resource_type_factory, type_to_resource_type):
    return partial(resource_type_producer_fn, resource_type_factory, type_to_resource_type)


# @pytest.fixture
# def resource_module_factory(mosaic, resource_type_producer, pyobj_creg):
#     return partial(ResourceModule, mosaic, resource_type_producer, pyobj_creg)


# @pytest.fixture
# def builtin_types_as_dict(pyobj_creg, builtin_types):
#     return partial(convert_builtin_types_to_dict, pyobj_creg, builtin_types)


# @pytest.fixture
# def builtin_services(mosaic, web):
#     return {
#         'mosaic': mosaic,
#         'web': web,
#         }


# @pytest.fixture
# def builtin_service_resource_loader(mosaic, builtin_services):
#     return partial(make_builtin_service_resource_module, mosaic, builtin_services.keys())


# @pytest.fixture
# def project(
#         type_module_loader, resource_module_factory, builtin_types_as_dict, builtin_service_resource_loader,
#         test_resources_dir):
#     builtin_type_modules = load_legacy_type_resources(builtin_types_as_dict())
#     builtins_project = BuiltinsProject(builtin_types_as_dict(), builtin_type_modules, builtin_service_resource_loader)
#     project = Project(
#         builtins_project, type_module_loader, resource_module_factory,
#         test_resources_dir, name='test-project')
#     path_to_text = load_texts(test_resources_dir)
#     project.load(path_to_text)
#     return project


# @pytest.fixture
# def resource_registry(project):
#     return project


# @pytest.fixture
# def htypes(pyobj_creg, project):
#     return HyperTypesNamespace(pyobj_creg, project.types)
