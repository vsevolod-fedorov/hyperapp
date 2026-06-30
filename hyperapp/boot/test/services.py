import logging

import pytest

from hyperapp.boot.htypes.builtins import make_builtin_name_to_type
from hyperapp.boot.mosaic import Mosaic
from hyperapp.boot.web import Web
from hyperapp.boot.pyobj_registry import PyObjRegistry
# from hyperapp.boot.association_registry import AssociationRegistry
from hyperapp.boot.python_importer import PythonImporter

log = logging.getLogger(__name__)


# @pytest.fixture
# def association_reg():
#     return AssociationRegistry()


@pytest.fixture
def pyobj_creg():
    return PyObjRegistry(config={}, reconstructors=[])


@pytest.fixture
def mosaic(pyobj_creg):
    return Mosaic(pyobj_creg)


@pytest.fixture
def web(pyobj_creg, mosaic):
    return Web(mosaic, pyobj_creg)


@pytest.fixture
def builtin_name_to_type():
    return make_builtin_name_to_type()


@pytest.fixture
def source_path():
    return {}


@pytest.fixture
def python_importer():
    return PythonImporter()
