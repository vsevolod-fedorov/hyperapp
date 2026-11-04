from .code.base.mark import mark


class Sample:
    @mark.test.wrapper
    @staticmethod
    def method():
        pass
