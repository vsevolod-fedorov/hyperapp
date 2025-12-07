from . import htypes
from .code.mark import mark
from .code.config_ctl import data_service_config_ctl


@mark.service(ctl=data_service_config_ctl())
def command_group_reg(config):
    return config


@mark.service
def get_command_group(command_group_reg, command_key):
    try:
        return command_group_reg[command_key]
    except KeyError:
        pass
    if isinstance(command_key, htypes.command.model_command_key):
        return 'context'
    if isinstance(command_key, htypes.command.global_model_command_key):
        return 'global'
    if isinstance(command_key, htypes.command.ui_command_key):
        return 'view'
    return None
