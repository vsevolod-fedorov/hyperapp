from .code.base.mark import mark


@mark.test.constructor
def second():
    return 'ok'
