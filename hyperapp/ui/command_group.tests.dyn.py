from . import htypes
from .services import (
    pyobj_creg,
    )
from .code.mark import mark
from .tested.code import command_group


@mark.config_fixture('command_group_type_reg')
def command_group_type_reg_config():
    return {
        htypes.command.model_command_key: 'test_group',
        }


def test_get_command_group(get_command_group):
    context_group = get_command_group(
        htypes.command.model_command_key(
            model_t=pyobj_creg.actor_to_ref(htypes.command_group_tests.sample_model),
            name='sample_context_command',
            ),
        )
    assert context_group == 'test_group'
