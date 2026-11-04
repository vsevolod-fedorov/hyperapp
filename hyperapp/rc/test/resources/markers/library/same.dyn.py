from .code.base.mark import mark


@mark.test.function_marker
def fn():
    pass


assert fn.provider_path.project == 'library'
assert fn.provider_path.path == ('same',)
