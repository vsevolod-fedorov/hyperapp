from . import htypes
from .code.mark import mark


@mark.service
def get_command_group(command_key):
    if isinstance(command_key, htypes.command.model_command_key):
        return 'context'
    if isinstance(command_key, htypes.command.global_model_command_key):
        return 'global'
    if isinstance(command_key, htypes.command.ui_command_key):
        return 'view'
    return None
