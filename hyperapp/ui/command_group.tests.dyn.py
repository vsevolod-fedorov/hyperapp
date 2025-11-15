from . import htypes
from .services import (
    pyobj_creg,
    )
from .tested.code import command_group


def test_get_command_group(get_command_group):
    context_group = get_command_group(
        htypes.command.model_command_key(
            model_t=pyobj_creg.actor_to_ref(htypes.command_group_tests.sample_model),
            name='sample_context_command',
            ),
        )
    assert context_group == 'context'
    global_group = get_command_group(
        htypes.command.global_model_command_key(
            name='sample_global_command',
            ),
        )
    assert global_group == 'global'
    view_group = get_command_group(
        htypes.command.ui_command_key(
            view_t=pyobj_creg.actor_to_ref(htypes.command_group_tests.sample_view),
            name='sample_view_command',
            ),
        )
    assert view_group == 'view'
