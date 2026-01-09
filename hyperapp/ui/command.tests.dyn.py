from unittest.mock import AsyncMock, Mock

from . import htypes
from .services import (
    pyobj_creg,
    )
from .code.mark import mark
from .code.context import Context
from .fixtures import visualizer_fixtures
from .tested.code import command as command_module


@mark.ctx_actor.command_creg(htypes.command_tests.sample_command)
def sample_command(piece):
    assert isinstance(piece, htypes.command_tests.sample_command)
    return 'sample-command-result'


async def test_command_runner(command_runner):
    navigator_view = AsyncMock()
    ctx = Context(
        navigator=Mock(view=navigator_view),
        ).push()
    command = htypes.command_tests.sample_command()
    await command_runner.run_command(ctx, command)
    navigator_view.open.assert_called_once()
    assert navigator_view.open.call_args.args[1] == 'sample-command-result'


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
