from .code.base.mark import mark


@mark.test.function_marker
def fn():
    return 'subject'
