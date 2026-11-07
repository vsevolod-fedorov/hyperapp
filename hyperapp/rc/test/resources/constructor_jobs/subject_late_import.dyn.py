from . import code
from .code.base.mark import mark


@mark.test.constructor
def value():
    return code.other.value()
