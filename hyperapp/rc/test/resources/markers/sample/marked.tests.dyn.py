from .code.base.mark import mark
from .tested.code import marked


@mark.test.function_marker
def local_helper():
    return 'local'


def test_tested_module_markers():
    assert marked.bare_class.test_marker == 'class'
    assert marked.bare_class.provider_path.project == 'sample'
    assert marked.bare_class.provider_path.path == ('marked',)
    assert marked.bare_class.marker_args == ()
    assert marked.bare_class.marker_kw == {}
    assert marked.bare_class() == 'bare class'

    assert marked.configured_class.test_marker == 'class'
    assert marked.configured_class.marker_args == ('configured',)
    assert marked.configured_class.marker_kw == {'option': 2}
    assert marked.configured_class.injected_service is marked.bare_class.injected_service

    assert marked.bare_function.test_marker == 'function'
    assert marked.bare_function.marker_args == ()
    assert marked.bare_function.marker_kw == {}
    assert marked.bare_function() == 'bare function'

    assert marked.configured_function.test_marker == 'function'
    assert marked.configured_function.provider_path.path == ('marked',)
    assert marked.configured_function.marker_args == ('configured',)
    assert marked.configured_function.marker_kw == {'option': 4}
    assert marked.configured_function.injected_service is marked.bare_class.injected_service

    if hasattr(local_helper, 'test_marker'):
        # A shared worker may reuse the module imported by its own import job. Its discoveries
        # must not be repeated by this test job; a fresh worker simply has no marker attributes.
        local_calls = [
            call for call in local_helper.injected_service.calls
            if call[2] == 'local_helper'
            ]
        assert local_calls == [('function', 'sample:marked.tests', 'local_helper')]
    assert local_helper() == 'local'
