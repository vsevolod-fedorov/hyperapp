from .code import module_1

# Uses imported value at import time, not just its attribute, so import is incomplete.
module_2_value = module_1.module_1_value * 2


def module_2_fn(value):
    return value + module_2_value
