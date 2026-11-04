from .code.base.mark import mark


class Sample:
    @mark.test.wrapper
    @classmethod
    def method():
        pass
