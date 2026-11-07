from . import services
from .code.base.mark import mark


@mark.test.wrapper
def import_only():
    return services.mosaic is not None


@mark.test.wrapper
def value():
    return 42
