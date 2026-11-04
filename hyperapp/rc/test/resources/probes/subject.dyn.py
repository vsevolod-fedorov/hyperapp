from .code.base.mark import mark


@mark.test.wrapper
@mark.test.wrapper
def value():
    return 42


class Sample:

    @mark.test.wrapper
    @mark.test.wrapper
    def instance(self):
        return self

    @classmethod
    @mark.test.wrapper
    @mark.test.wrapper
    def cls(cls):
        return cls

    @staticmethod
    @mark.test.wrapper
    @mark.test.wrapper
    def static(value):
        return value


# Resolve at import too: cached probes must lose this state before any test job runs.
assert value() == 42
