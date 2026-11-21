from .code import dependency
from .code.base.mark import mark


@mark.test.wrapper
def import_only():
    return dependency.import_only()


def value():
    return dependency.value()
