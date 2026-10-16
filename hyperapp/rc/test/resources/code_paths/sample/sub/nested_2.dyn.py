# Sibling in the same subdirectory.
from .code.nested import nested_value
# Not found in this directory, found in a parent one.
from .code.module_1 import module_1_value
# Nearest one wins: sub/common shadows root common.
from .code.common import common_value

nested_2_value = 444


def values():
    return (nested_value, module_1_value, common_value)
