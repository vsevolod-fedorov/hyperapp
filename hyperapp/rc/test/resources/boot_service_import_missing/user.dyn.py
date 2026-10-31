# No boot service is named so.
from .services import missing


def fn():
    return missing.value
