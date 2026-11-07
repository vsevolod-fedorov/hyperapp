from .code.base.mark import mark


@mark.test.constructor
def value(value='ok'):
    return value


assert value() == 'ok'
