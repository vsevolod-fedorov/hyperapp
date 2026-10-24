from .code import helper

# Imported function is called at import time, so the first import attempt is incomplete,
# not getting to the tested import below: module is decided to be a compiled one.
VALUE = helper.value()

from .tested.code import module_1
