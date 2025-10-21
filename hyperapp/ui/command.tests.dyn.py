from . import htypes
from .tested.code import command as command_module


def test_prepare_result():
    command = command_module.Command(
        t=None,
        name=None,
        command=None,
        ctx=None,
        )
    result = command._prepare_result(result="Sample text")
    assert isinstance(result, htypes.command.command_result)
