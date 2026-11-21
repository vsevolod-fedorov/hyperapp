from .tested.code import module_1
from .code import manual


assert manual.value() == 42
from .code.module_1 import fn_1
