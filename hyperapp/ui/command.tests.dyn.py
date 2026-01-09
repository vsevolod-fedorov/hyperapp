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
def _sample_command(piece):
    assert isinstance(piece, htypes.command_tests.sample_command)
    return 'sample-command-result'


@mark.fixture
def sample_command():
    return htypes.command_tests.sample_command()


@mark.fixture
def navigator():
    return AsyncMock()


@mark.fixture
def ctx(navigator):
    return Context(
        navigator=Mock(view=navigator),
        )


async def test_runner_run_model_command(command_runner, sample_command, navigator, ctx):
    result = await command_runner.run_model_command(ctx.push(), sample_command)
    assert result == 'sample-command-result'


async def test_runner_run_command(command_runner, sample_command, navigator, ctx):
    await command_runner.run_command(ctx.push(), sample_command)
    navigator.open.assert_called_once()
    assert navigator.open.call_args.args[1] == 'sample-command-result'


async def test_command_factory(command_factory, sample_command, navigator, ctx):
    command = command_factory(
        key=htypes.command.model_command_key(
            model_t=pyobj_creg.actor_to_ref(htypes.command_tests.sample_model),
            name='sample_command',
            ),
        name='sample_command',
        command=sample_command,
        ctx=ctx.push(),
        )
    await command.run()
    navigator.open.assert_called_once()
    assert navigator.open.call_args.args[1] == 'sample-command-result'
