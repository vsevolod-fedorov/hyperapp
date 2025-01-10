import logging
import pytest

from hyperapp.boot.init_logging import setup_filter

log = logging.getLogger(__name__)


class AsyncExceptionHandler(object):

    def __init__(self):
        self.had_exceptions = False

    def __call__(self, loop, context):
        self.had_exceptions = True
        loop.default_exception_handler(context)


def _log_separator(section_name):
    log.info('{:-<9} {:-<150}'.format('', section_name + ' '))


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    setup_filter()
    _log_separator('setup')
    yield

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    setup_filter()
    _log_separator('test')
    yield

@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item):
    setup_filter()
    _log_separator('teardown')
    yield

@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
    _log_separator('%s setup' % fixturedef.argname)
    yield

def pytest_fixture_post_finalizer(fixturedef):
    _log_separator('%s teardown' % fixturedef.argname)


@pytest.hookimpl(hookwrapper=True)
def pytest_pyfunc_call(pyfuncitem):
    event_loop = None
    for name in pyfuncitem._request.fixturenames:
        if name == 'event_loop':
            event_loop = pyfuncitem._request.getfixturevalue(name)
            break
    if event_loop:
        handler = AsyncExceptionHandler()
        event_loop.set_exception_handler(handler)
    outcome = yield
    passed = outcome.excinfo is None
    if passed and event_loop:
        assert not handler.had_exceptions, 'Event loop had unhandled exceptions'
