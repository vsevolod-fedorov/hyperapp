from .tested.code import code_import


def test_import():
    assert code_import.checks is not None
