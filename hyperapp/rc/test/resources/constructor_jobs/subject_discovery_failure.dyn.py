from .code.base.mark import mark


@mark.test.constructor
def value():
    return 'ok'


def test_cycle():
    pass


test_cycle.__wrapped__ = test_cycle
