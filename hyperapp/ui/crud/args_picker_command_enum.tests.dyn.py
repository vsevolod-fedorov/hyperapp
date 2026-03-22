from . import htypes
from .services import (
    mosaic,
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.context import Context
from .code.arg_mark import model_mark_name, value_mark_name
from .tested.code import args_picker_command_enum


@mark.fixture
def make_enum(t):
    command = htypes.args_picker_command_enum_tests.sample_command()
    return htypes.command.args_picker_command_enum(
        name='sample_command',
        required_args=(
            htypes.command.arg_t(
                name='arg_name',
                t=pyobj_creg.actor_to_ref(t),
                ),
            ),
        commit_command=mosaic.put(command),
        )

@mark.fixture.obj
def enum_piece(make_enum):
    return make_enum(htypes.builtin.string)


def key_factory(name):
    return htypes.command.model_command_key(
        model_t=pyobj_creg.actor_to_ref(htypes.args_picker_command_enum_tests.sample_model),
        name=name,
        )


@mark.fixture.obj
def enum_ctx(enum_piece):
    return Context(
        piece=enum_piece,
        key_factory=key_factory,
        )


def test_arg_picker_command(enum_ctx):
    command_list = args_picker_command_enum.args_picker_command_enum(enum_ctx)
    assert type(command_list) is list
    [command] = command_list
    assert isinstance(command.command, htypes.command.args_picker_command)


def test_value_from_context(enum_ctx):
    ctx = enum_ctx.clone_with(
        **{value_mark_name(htypes.builtin.string): "Sample value"},
        )
    command_list = args_picker_command_enum.args_picker_command_enum(ctx)
    assert type(command_list) is list
    [command] = command_list
    assert isinstance(command.command, htypes.command.canned_args_command)


def test_ref_from_context(make_enum):
    enum_piece = make_enum(htypes.builtin.ref)
    ctx = Context(
        piece=enum_piece,
        key_factory=key_factory,
        **{model_mark_name(htypes.builtin.string): "Sample value"},
        )
    command_list = args_picker_command_enum.args_picker_command_enum(ctx)
    assert type(command_list) is list
    [command] = command_list
    assert isinstance(command.command, htypes.command.canned_args_command)


@mark.config_fixture('command_group_type_reg')
def command_group_type_reg_config():
    return {
        htypes.command.model_command_key: 'test_group',
        }


def test_args_picker_command_group():
    commit_command_key = key_factory('sample_command')
    piece = htypes.command.args_picker_command_key(
        name='sample_command',
        commit_command_key=mosaic.put(commit_command_key),
        )
    group = args_picker_command_enum.args_picker_command_group(piece)
    assert group == 'test_group'
