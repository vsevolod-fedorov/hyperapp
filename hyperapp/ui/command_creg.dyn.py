from .services import (
    code_registry_ctr,
    )
from .code.mark import mark
from .code.context_code_registry import ContextCodeRegistry


@mark.service
def ui_command_creg(config):
    return ContextCodeRegistry('ui_command_creg', config)


@mark.service
def command_creg(config):
    return code_registry_ctr('command_creg', config)
