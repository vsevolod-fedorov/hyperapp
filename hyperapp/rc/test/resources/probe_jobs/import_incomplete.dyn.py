from .code.base.mark import mark


@mark.test.wrapper
def value():
    return 42


assert value() == 42
from .code import missing
missing.fn()
