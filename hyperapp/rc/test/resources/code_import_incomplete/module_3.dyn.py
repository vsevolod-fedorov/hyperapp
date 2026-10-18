from .code.module_1 import module_1_value
from .code import module_2

# Calls imported function at import time, so import is incomplete.
module_3_value = module_2.module_2_fn(module_1_value)
