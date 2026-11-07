from .code.base.mark import mark


@mark.test.constructor
def value(result):
    return result


value('one')
value('contradiction')
