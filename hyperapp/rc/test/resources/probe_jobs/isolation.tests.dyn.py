from .code.base.mark import mark


@mark.test.wrapper
def test_succeeded():
    pass


@mark.test.wrapper
def test_failed():
    raise RuntimeError('expected failure')


@mark.test.wrapper
def test_incomplete():
    from .code import missing
    missing.fn()


@mark.test.wrapper
def test_next():
    pass
