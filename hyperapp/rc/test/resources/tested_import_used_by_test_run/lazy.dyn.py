from . import code


# Gets module_1 by attribute only when called, so its import does not use it.
def fn():
    return code.module_1.fn_1()
