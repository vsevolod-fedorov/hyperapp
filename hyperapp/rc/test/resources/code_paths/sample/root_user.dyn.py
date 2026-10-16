# Module import from the same directory.
from .code import module_1
# Attribute import from the same directory; sub/common is not visible from here.
from .code.common import common_value
# Attribute import from a subdirectory module.
from .code.sub.nested import nested_value
# Module import from a subdirectory.
from .code.sub import nested_2
# Imports from other project, by its local name.
from .code.lib.util import util_value
from .code.lib.sub.deep import deep_value


def values():
    return (
        module_1.module_1_value,
        common_value,
        nested_value,
        nested_2.nested_2_value,
        util_value,
        deep_value,
        )
