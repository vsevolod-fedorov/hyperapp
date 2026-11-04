from .code.base.mark import mark


@mark.test.class_marker
def fn():
    pass


assert fn.test_marker == 'class'
assert str(fn.provider_path) == 'sample:z_valid'
