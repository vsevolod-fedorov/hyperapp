import logging
from types import SimpleNamespace

import pytest

from hyperapp.common.services import Services
from hyperapp.common.test.hyper_types_namespace import HyperTypesNamespace

log = logging.getLogger(__name__)


@pytest.fixture
def type_module_list():
    return []


@pytest.fixture
def code_module_list():
    return []


@pytest.fixture
def services(type_module_list, code_module_list):
    services = Services()
    services.init_services()
    services.init_modules(type_module_list, code_module_list)
    services.start()
    yield services
    services.stop()
    for reason in services.get_failure_reason_list():
        log.error("Services failure reason: %s", reason)
    services.check_failures()


@pytest.fixture
def htypes(services):
    return HyperTypesNamespace(services.types, services.local_type_module_registry)


@pytest.fixture
def code(services):
    return SimpleNamespace(**{
        name.split('.')[-1]: module  # sync.rpc.rpc_endpoint -> rpc_endpoint
        for name, module in services.name2module.items()
        })
