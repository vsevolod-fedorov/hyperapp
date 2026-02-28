from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.context import Context
from .code.arg_mark import value_mark_name
from .tested.code import args_picker_command_enum


@mark.fixture.obj
def piece():
    command = htypes.args_picker_command_enum_tests.sample_command()
    return htypes.command.args_picker_command_enum(
        name='sample_command',
        required_args=(
            htypes.command.arg_t(
                name='arg_name',
                t=pyobj_creg.actor_to_ref(htypes.builtin.string),
                ),
            ),
        commit_command=mosaic.put(command),
        )


@mark.fixture
def ctx(piece):
    return Context(
        piece=piece,
        )


@mark.fixture.obj
def canned_ctx(ctx):
    return ctx.clone_with({value_mark_name(htypes.builtin.string): "Sample value"})


def _test_model_args_picker(ctx, piece):
    piece = args_picker_enum(htypes.command.model_args_picker_command_enumerator)
    enum = args_picker_command_enum.UnboundArgsPickerModelCommandEnumerator.from_piece(piece)
    assert isinstance(enum, args_picker_command_enum.UnboundArgsPickerModelCommandEnumerator)
    command_list = enum.enum_commands(ctx)
    assert type(command_list) is list
    [command] = command_list
    assert isinstance(command, UnboundModelCommand)
    assert isinstance(web.summon(command.piece.system_fn), htypes.command.args_picker_command_fn)


def _test_ui_args_picker(ctx, piece):
    piece = args_picker_enum(htypes.command.ui_args_picker_command_enumerator)
    enum = args_picker_command_enum.UnboundArgsPickerUiCommandEnumerator.from_piece(piece)
    assert isinstance(enum, args_picker_command_enum.UnboundArgsPickerUiCommandEnumerator)
    command_list = enum.enum_commands(ctx)
    assert type(command_list) is list
    [command] = command_list
    assert isinstance(command, UnboundUiCommand)
    assert isinstance(web.summon(command.piece.system_fn), htypes.command.args_picker_command_fn)


def test_canned(canned_ctx):
    command_list = args_picker_command_enum.args_picker_command_enum(canned_ctx)
    assert type(command_list) is list
    [command] = command_list
    assert isinstance(command.command, htypes.command.canned_args_command)


def _test_format_open_args_picker_command_d():
    commit_command_d = htypes.args_picker_command_enum_tests.sample_command_d()
    d = htypes.command.open_args_picker_command_d(
        commit_command_d=mosaic.put(commit_command_d),
        )
    title = args_picker_command_enum.format_open_args_picker_command_d(d)
    assert type(title) is str
