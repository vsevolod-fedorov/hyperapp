from .code.base.mark import mark


@mark.test.constructor
def value(value='ok'):
    return value


value('failed observation')
raise RuntimeError('failed import')
