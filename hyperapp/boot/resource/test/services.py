from functools import partial

import pytest

from hyperapp.boot.htypes.builtins import make_builtin_name_to_type
from hyperapp.boot.htypes.meta_type import (
    make_meta_type_name_to_type,
    add_types_to_pyobj_creg_cache,
    register_builtin_mt,
    register_pyobj_creg_mt_actors,
    )
from hyperapp.boot.resource.resource_type import ResourceType
from hyperapp.boot.resource.resource_type_registry import make_type_to_resource_type
from hyperapp.boot.resource.pyobj_registry import register_pyobj_creg_actors
from hyperapp.boot.resource.builtin_service import make_builtin_name_to_service
from hyperapp.boot.resource.resource_type_producer import produce_resource_type
from hyperapp.boot.register_coders import register_coders


@pytest.fixture
def builtin_name_to_type():
    return {
        **make_builtin_name_to_type(),
        **make_meta_type_name_to_type(),
        }


@pytest.fixture
def builtin_name_to_service(reconstructors, pyobj_creg, mosaic, web, source_path):
    return make_builtin_name_to_service(reconstructors, pyobj_creg, mosaic, web, source_path)


@pytest.fixture
def init(pyobj_creg, mosaic, web, python_importer, source_path, builtin_name_to_type, builtin_name_to_service):
    pyobj_creg.init(mosaic, web)
    add_types_to_pyobj_creg_cache(pyobj_creg, builtin_name_to_type)
    register_builtin_mt(mosaic, pyobj_creg)
    register_pyobj_creg_mt_actors(pyobj_creg)
    register_pyobj_creg_actors(pyobj_creg, mosaic, web, python_importer, source_path, builtin_name_to_service)
    register_coders()


@pytest.fixture
def resource_type_factory(mosaic, web, pyobj_creg, init):
    return partial(ResourceType, mosaic, web, pyobj_creg)


@pytest.fixture
def type_to_resource_type():
    return make_type_to_resource_type()


@pytest.fixture
def resource_type_producer(resource_type_factory, type_to_resource_type):
    return partial(produce_resource_type, resource_type_factory, type_to_resource_type)
