from . import htypes
from .services import (
    pyobj_creg,
    )
from .tested.code import command as command_module


def test_command_factory_and_prepare_result(command_factory):
    command = command_factory(
        key=htypes.command.model_command_key(
            model_t=pyobj_creg.actor_to_ref(htypes.command_tests.sample_model),
            name='sample_command',
            ),
        name='sample_command',
        command=None,
        ctx=None,
        )
    result = command._prepare_result(result="Sample text")
    assert isinstance(result, htypes.command.command_result)
