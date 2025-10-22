from . import htypes
from .tested.code import command as command_module


def test_command_factory_and_prepare_result(command_factory):
    command = command_factory(
        t=None,
        name='sample_command',
        command=None,
        ctx=None,
        )
    result = command._prepare_result(result="Sample text")
    assert isinstance(result, htypes.command.command_result)
