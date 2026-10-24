from .tested.code import module_a
from .tested.code import module_b


# Tested module_a imports tested module_b through untested module_c. Being complete, module_c needs
# complete module_b, which waits for its tests: a dependency cycle.
def test_fn():
    assert module_a.fn_a() == module_b.fn_b()
