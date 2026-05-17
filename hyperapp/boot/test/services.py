import logging

import pytest

from hyperapp.boot.htypes.builtins import make_builtin_name_to_type
from hyperapp.boot.mosaic import Mosaic
from hyperapp.boot.web import Web
from hyperapp.boot.pyobj_registry import PyObjRegistry
from hyperapp.boot.association_registry import AssociationRegistry
from hyperapp.boot.python_importer import PythonImporter
# from hyperapp.boot.htypes import BuiltinTypeRegistry, register_builtin_types
# from hyperapp.boot.htypes.python_module import python_module_t
# from hyperapp.boot.htypes.attribute import attribute_t
# from hyperapp.boot.htypes.partial import partial_t
# from hyperapp.boot.services import pyobj_config
# from hyperapp.boot.type_module_loader import TypeModuleLoader
# from hyperapp.boot.resource.attribute import attribute_pyobj
# from hyperapp.boot.resource.call import call_pyobj
# from hyperapp.boot.resource.partial import partial_pyobj
# from hyperapp.boot.resource.python_module import python_module_pyobj

log = logging.getLogger(__name__)


@pytest.fixture
def association_reg():
    return AssociationRegistry()


@pytest.fixture
def pyobj_creg():
    return PyObjRegistry(config={}, reconstructors=[])


@pytest.fixture
def mosaic(pyobj_creg):
    return Mosaic(pyobj_creg)


@pytest.fixture
def web(pyobj_creg, mosaic):
    return Web(mosaic, pyobj_creg)
    # pyobj_creg.init(builtin_types, mosaic, web)
    # register_builtin_types(builtin_types, pyobj_creg)
    # pyobj_creg.register_actor(
    #     python_module_t, python_module_pyobj,
    #     mosaic=mosaic,
    #     python_importer=python_importer,
    #     pyobj_creg=pyobj_creg,
    #     )
    # # pyobj_creg.register_actor(builtin_service_t, builtin_service_pyobj, self)
    # pyobj_creg.register_actor(attribute_t, attribute_pyobj, pyobj_creg=pyobj_creg)
    # pyobj_creg.register_actor(partial_t, partial_pyobj, pyobj_creg=pyobj_creg)
    # return (mosaic, web)


@pytest.fixture
def builtin_name_to_type():
    return make_builtin_name_to_type()


@pytest.fixture
def python_importer():
    importer = PythonImporter()
    importer.register_meta_hook()
    yield importer
    importer.remove_modules()
    importer.unregister_meta_hook()
