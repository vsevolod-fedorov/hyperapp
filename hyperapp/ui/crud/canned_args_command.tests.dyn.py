from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.context import Context
from .tested.code import canned_args_command


@mark.ctx_actor.command_creg(htypes.canned_args_command_tests.sample_command)
def sample_command(arg):
    return f'sample-command:{arg}'


def test_sample_command():
    ctx = Context(
        arg='sample-value',
        )
    result = sample_command(ctx)
    assert result == 'sample-command:sample-value', repr(result)


async def test_canned_command():
    commit_command = htypes.canned_args_command_tests.sample_command()
    piece = htypes.command.canned_args_command(
        args=(
            htypes.command.arg('arg', mosaic.put('sample-value')),
            ),
        commit_command=mosaic.put(commit_command),
        )
    ctx = Context(
        piece=piece,
        )
    result = await canned_args_command.canned_args_command(ctx)
    assert result == 'sample-command:sample-value'


def _test_format_d():
    commit_command_d = htypes.canned_args_command_tests.sample_command_d()
    d = htypes.command.canned_arg_command_d(
        commit_command_d=mosaic.put(commit_command_d),
        args=(
            htypes.command.arg(
                name='arg_name',
                value=mosaic.put("Sample arg value"),
                ),
            ),
        )
    title = canned_args_command.format_canned_arg_command_d(d)
    assert type(title) is str
