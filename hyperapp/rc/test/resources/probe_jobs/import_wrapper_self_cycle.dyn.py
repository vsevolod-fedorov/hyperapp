from .code.base.mark import mark


@mark.test.wrapper
def value():
    return 42


assert value() == 42


def test_cycle():
    pass


test_cycle.__wrapped__ = test_cycle
