from .code.base.mark import mark


@mark.test.wrapper
def next_value():
    return 42


assert next_value() == 42
