from .code.base.mark import mark


@mark.test.constructor
def changed():
    return 'ok'
