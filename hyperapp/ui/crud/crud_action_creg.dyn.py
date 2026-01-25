from .code.mark import mark
from .code.context_code_registry import ContextCodeRegistry


@mark.service
def crud_init_action_creg(config):
    return ContextCodeRegistry('crud_init_action_creg', config)


@mark.service
def crud_commit_action_creg(config):
    return ContextCodeRegistry('crud_commit_action_creg', config)
