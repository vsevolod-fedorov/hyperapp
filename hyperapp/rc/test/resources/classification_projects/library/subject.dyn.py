from . import services


def value():
    assert services.mosaic is not None
    return 42


def has_web():
    return getattr(services, 'web', None) is not None
