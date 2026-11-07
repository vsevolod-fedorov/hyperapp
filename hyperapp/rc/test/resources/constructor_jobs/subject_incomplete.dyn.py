from .code.base.mark import mark


@mark.test.constructor
def value(value='ok'):
    return value


value()
from .code import missing
missing.fn()
