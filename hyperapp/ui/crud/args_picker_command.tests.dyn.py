import weakref
from unittest.mock import AsyncMock, Mock

from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    )
from .code.mark import mark
from .code.context import Context
from .fixtures import feed_fixtures
from .fixtures import visualizer_fixtures
from .tested.code import args_picker_command


def _editor_default():
    return 123


@mark.ctx_actor.command_creg(htypes.args_picker_command_tests.sample_command)
def sample_command(arg):
    return f'sample-command:{arg}'


def test_sample_command():
    ctx = Context(
        arg='sample-value',
        )
    result = sample_command(ctx)
    assert result == 'sample-command:sample-value', repr(result)


@mark.ctx_actor.crud_init_action_creg(htypes.args_picker_command_tests.sample_init_action)
def sample_picker():
    return htypes.args_picker_command_tests.sample_value(id=0)


def test_sample_picker():
    ctx = Context(
        piece=htypes.args_picker_command_tests.sample_init_action(),
        )
    result = sample_picker(ctx)
    assert result == htypes.args_picker_command_tests.sample_value(id=0)


@mark.config_fixture('editor_default_reg')
def editor_default_reg_config():
    return {
        htypes.args_picker_command_tests.sample_value: htypes.args_picker_command_tests.sample_init_action(),
        }


@mark.fixture
def navigator_widget():
    return Mock()


@mark.fixture
def navigator_rec(navigator_widget):
    return Mock(view=AsyncMock(), widget_wr=weakref.ref(navigator_widget))


async def test_args_picker_command(navigator_rec):
    commit_command = htypes.args_picker_command_tests.sample_command()
    piece = htypes.command.args_picker_command(
        name='sample-command',
        args=(),
        required_args=(
            htypes.command.arg_t(
                name='sample_value',
                t=pyobj_creg.actor_to_ref(htypes.args_picker_command_tests.sample_value),
                ),
            ),
        commit_command=mosaic.put(commit_command),
        )
    canned_item_piece = htypes.ui.canned_ctl_item(
        item_id=12345,
        path=(11, 22, 33),
        )
    ctx = Context(
        controller=Mock(),
        navigator=navigator_rec,
        hook=Mock(canned_item_piece=canned_item_piece),
        piece=piece,
        )
    await args_picker_command.args_picker_command(ctx)
    navigator_rec.view.open.assert_awaited_once()
