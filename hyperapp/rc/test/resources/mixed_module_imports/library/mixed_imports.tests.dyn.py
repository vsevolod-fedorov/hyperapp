from . import code
from .code import manual
from .tested import code as subjects
from .tested.code import module_1


def test_code_alias_of_tested_module():
    assert code.module_1.fn_1() == 111


def test_unforced_code_alias():
    assert code.module_1 is not None


def test_tested_alias_of_plain_module():
    assert subjects.manual.value() == 42


def test_mixed_import_in_subject():
    assert module_1.lazy_import() is not None
