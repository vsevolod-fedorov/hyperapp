from .code import dependency
from .code.base.mark import mark


@mark.test.function_marker
def fn():
    pass


assert fn.test_marker == 'function'
assert str(fn.provider_path) == 'sample:a_incomplete'
assert dependency.get_value() == 42
