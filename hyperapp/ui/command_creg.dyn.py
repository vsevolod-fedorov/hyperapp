from .code.mark import mark
from .code.context_code_registry import ContextCodeRegistry


@mark.service
def command_creg(config):
    return ContextCodeRegistry('command_creg', config)


@mark.service
def command_enum_creg(config):
    return ContextCodeRegistry('command_enum_creg', config)
