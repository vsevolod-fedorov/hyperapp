from .code.base.mark import mark


@mark.test.class_marker
def bare_class():
    return 'bare class'


@mark.test.class_marker('configured', option=2)
def configured_class():
    return 'configured class'


@mark.test.function_marker
def bare_function():
    return 'bare function'


@mark.test.function_marker('configured', option=4)
def configured_function():
    return 'configured function'
