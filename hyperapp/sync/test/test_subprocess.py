import pytest

from hyperapp.common import cdr_coders  # self-registering


pytest_plugins = ['hyperapp.common.test.services']


@pytest.fixture
def type_module_list():
    return [
        ]


@pytest.fixture
def code_module_list():
    return [
        'common.visitor',
        'common.ref_collector',
        'common.unbundler',
        'common.remoting.identity',
        'sync.work_dir',
        'sync.async_stop',
        'sync.transport.transport',
        'sync.subprocess_connection',
        'sync.subprocess',
        ]


def test_subprocess(services):
    subprocess = services.subprocess(
        'subprocess',
        type_module_list=[
            ],
        code_module_list=[
            'common.visitor',
            'common.ref_collector',
            'common.remoting.identity',
            'common.unbundler',
            'sync.async_stop',
            'sync.transport.transport',
            'sync.subprocess_connection',
            'sync.subprocess_child',
            ],
        )
    with subprocess:
        pass


def test_import_failure(services):
    subprocess = services.subprocess(
        'subprocess',
        type_module_list=[
            ],
        code_module_list=[
            'common.visitor',
            'common.ref_collector',
            'sync.test.import_failure',
            ],
        )
    with pytest.raises(AssertionError) as excinfo:
        with subprocess:
            pass
    assert str(excinfo.value) == 'Test import failure'


def test_module_init_failure(services):
    subprocess = services.subprocess(
        'subprocess',
        type_module_list=[
            ],
        code_module_list=[
            'common.visitor',
            'common.ref_collector',
            'sync.test.module_init_failure',
            ],
        )
    with pytest.raises(AssertionError) as excinfo:
        with subprocess:
            pass
    assert str(excinfo.value) == 'Test module init failure'
