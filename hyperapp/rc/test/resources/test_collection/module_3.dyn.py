from .code import module_1
from .code import module_4


# Tested by the same test module as module_1, so gets recorded module_1, as tests do;
# module_4 is not tested by it, so it gets complete module_4, compiled before tests.
def fn_3():
    return module_1.fn_1() + module_4.fn_4()
