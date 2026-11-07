from .code.base.mark import mark


@mark.test.constructor
def value():
    return 'ok'
