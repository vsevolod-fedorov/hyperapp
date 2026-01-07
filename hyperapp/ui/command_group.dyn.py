from .services import (
    deduce_t,
    )
from .code.mark import mark
from .code.config_key_ctl import TypeKeyCtl
from .code.config_value_ctl import DataValueCtl
from .code.config_ctl import DictConfigCtl, data_service_config_ctl


@mark.service(ctl=data_service_config_ctl())
def command_group_reg(config):
    return config


@mark.service(ctl=DictConfigCtl(key_ctl=TypeKeyCtl(), value_ctl=DataValueCtl()))
def command_group_type_reg(config):
    return config


@mark.service
def get_command_group(command_group_reg, command_group_type_reg, command_key):
    try:
        return command_group_reg[command_key]
    except KeyError:
        pass
    command_key_t = deduce_t(command_key)
    try:
        return command_group_type_reg[command_key_t]
    except KeyError:
        pass
    return None
