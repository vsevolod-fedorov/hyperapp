from .services import (
    pyobj_creg,
    web,
    )
from .code.mark import mark
from .code.context_code_registry import ContextCodeRegistry


class Selector:

    def __init__(self, model_t, open_action, pick_action):
        self.model_t = model_t
        self.open_action = open_action
        self.pick_action = pick_action


@mark.actor.cfg_value_creg
def resolve_selector_cfg_value(piece, key, system, service_name):
    system_fn_creg = system.resolve_service('system_fn_creg')
    return Selector(
        model_t=pyobj_creg.invite(piece.model_t),
        open_action=web.summon(piece.open_action),
        pick_action=web.summon(piece.pick_action),
        )


class SelectorRegistry:

    def __init__(self, config):
        self._config = config

    def __getitem__(self, value_t):
        return self._config[value_t]

    def by_model_t(self, model_t):
        for selector in self._config.values():
            if selector.model_t is model_t:
                return selector
        raise KeyError(model_t)


@mark.service
def selector_reg(config):
    return SelectorRegistry(config)


@mark.service
def selector_open_action_creg(config):
    return ContextCodeRegistry('selector_open_action_creg', config)


@mark.service
def selector_pick_action_creg(config):
    return ContextCodeRegistry('selector_pick_action_creg', config)
