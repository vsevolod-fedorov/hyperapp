from .code import other
from .code.base.mark import mark


@mark.test.constructor
def value():
    return other.second()
