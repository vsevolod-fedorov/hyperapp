from unittest.mock import MagicMock, Mock

from . import htypes
from .services import (
    mosaic,
    )
from .code.mark import mark
from .code.context import Context
from .code.system_fn import ContextFn
# from .code.model_command import UnboundModelCommand
# from .code.ui_model_command import UnboundUiModelCommand, CommandItem
from .fixtures import feed_fixtures
from .tested.code import command_list_model, model_commands, global_commands


def _sample_fn(model, state):
    return f'sample-fn: {state}'


@mark.fixture.obj
def shortcut_reg():
    reg = MagicMock()
    reg.get.return_value = None
    return reg


@mark.fixture
def lcs():
    lcs = Mock()
    lcs.get.return_value = None
    return lcs


def _test_command_item_to_item(rpc_system_call_factory, format, diff_creg, feed_factory, error_view, view_reg, visualizer, shortcut_reg, lcs):
    system_fn = ContextFn(
        rpc_system_call_factory=rpc_system_call_factory,
        ctx_params=('view', 'state'),
        service_params=(),
        raw_fn=_sample_fn,
        )
    model_command = UnboundModelCommand(
        d=htypes.command_list_model_tests.sample_model_command_d(),
        ctx_fn=system_fn,
        properties=htypes.command.properties(False, False, False),
        )
    command = UnboundUiModelCommand(
        diff_creg=diff_creg,
        feed_factory=feed_factory,
        error_view=error_view,
        view_reg=view_reg,
        visualizer=visualizer,
        d=htypes.command_list_model_tests.sample_model_command_d(),
        model_command=model_command,
        )
    command_item = CommandItem(
        format=format,
        d=htypes.command_list_model_tests.sample_command_d(),
        model_command_d=htypes.command_list_model_tests.sample_model_command_d(),
        command=command,
        )
    view_item = command_list_model.command_item_to_model_item(shortcut_reg, lcs, command_item)
    assert view_item


def mock_run_input_key_dialog():
    return 'Space'


@mark.fixture
def model_piece():
    model = htypes.command_list_model_tests.sample_model()
    model_state = htypes.command_list_model_tests.sample_model_state()
    return htypes.model_commands.model(
        model=mosaic.put(model),
        model_state=mosaic.put(model_state)
        )


@mark.fixture
def global_piece():
    return htypes.global_commands.model()


@mark.fixture
def command_d():
    return mosaic.put(htypes.command_list_model_tests.sample_command_d())


def _test_model_command_get(lcs, model_piece, command_d):
    form = command_list_model.command_get(model_piece, command_d, lcs)


def _test_global_command_get(lcs, global_piece, command_d):
    form = command_list_model.command_get(global_piece, command_d, lcs)


def _test_model_command_update(lcs, model_piece, command_d):
    value = htypes.command_list_model.form("new text", "new tooltip")
    command_list_model.command_update(model_piece, command_d, value, lcs)


def _test_global_command_update(lcs, global_piece, command_d):
    value = htypes.command_list_model.form("new text", "new tooltip")
    command_list_model.command_update(global_piece, command_d, value, lcs)


@mark.fixture.obj
def command():
    return htypes.command_list_model.command(
        name='sample_command',
        key=mosaic.put(htypes.command.global_model_command_key(name='sample_command')),
        model=None,
        model_state=None,
    )


@mark.fixture.obj
def model(command):
    return htypes.command_list_model.model(
        commands=(command,),
        )


def test_commands_model(model):
    item_list = command_list_model.commands_model(model)
    assert item_list
    assert isinstance(item_list[0], htypes.command_list_model.item)


@mark.fixture
def ctx(command_factory):
    return Context()


def test_open_model(command_factory, ctx):
    commands= [
        command_factory(
            key=htypes.command.global_model_command_key(name='sample_command'),
            name='sample_command',
            command=None,  # Unused
            ctx=ctx,
        ),
    ]
    model = command_list_model.open_commands(commands)
    assert isinstance(model, htypes.command_list_model.model)


@mark.fixture
def current_item(command):
    return htypes.command_list_model.item(
        name='sample_command',
        groups="",
        shortcut="",
        text="",
        tooltip="",
        command=mosaic.put(command),
    )


async def test_set_shortcut(feed_factory, shortcut_reg, model, current_item):
    feed = feed_factory(model)
    command_list_model.run_key_input_dialog = mock_run_input_key_dialog
    current_idx = 0
    command_list_model.set_shortcut(model, current_idx, current_item)
    shortcut_reg.__setitem__.assert_called_once()
    await feed.wait_for_diffs(count=1)
