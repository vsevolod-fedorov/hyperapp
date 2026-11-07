from .code.base.mark import mark
from .code import missing


@mark.test.constructor
def value():
    return 'ok'
