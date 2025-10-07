from .services import (
    deduce_t,
    web,
    )
from .code.mark import mark
from .code.config_ctl import DictConfigCtl
from .code.config_value_ctl import DataValueCtl
from .code.config_struct_ctl import ListStructCtl


def _properties_match(factory_prop_list, wanted_props):
    factory_props = {
        prop.name: prop.value
        for prop in factory_prop_list
        }
    for name, wanted_value in wanted_props.items():
        value = factory_props.get(name)
        if value is None:
            # Factory property is missing or it's value is None (match everything) -> accept.
            continue
        if value != wanted_value:
            return False
    return True


@mark.service(ctl=DictConfigCtl(value_ctl=DataValueCtl(), struct_ctl=ListStructCtl()))
def default_model_factory(config, view_factory_reg, model_t, properties):
    for factory in config[model_t]:
        if _properties_match(factory.properties, properties):
            layout_k = web.summon(factory.layout_k)
            break
    else:
        raise KeyError(model_t)
    return view_factory_reg[layout_k]


@mark.service(ctl=DictConfigCtl(value_ctl=DataValueCtl()))
def default_ui_factory(config, view_factory_reg, ui_t):
    ui_t_t = deduce_t(ui_t)
    k = config[ui_t_t]
    return view_factory_reg[k]
