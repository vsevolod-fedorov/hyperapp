from . import htypes
from .services import (
    web,
    )
from .code.resolving_code_registry import (
    ResolvingCodeRegistry,
    CachedResolvingCodeRegistry,
    AdapterCodeRegistry,
    ServiceCodeRegistry,
    )
from .code.config import TypedDictConfig, DataDictConfig
from . import data


def setup_system(config_piece_list):
    service_to_config_pieces = {}
    for config in config_piece_list:
        for rec in config.services:
            service = web.summon(rec.service)
            service_config = web.summon(rec.config)
            service_to_config_pieces.setdefault(service, []).append(service_config)
    print("service_to_config_pieces:", service_to_config_pieces)

    config_creg = ResolvingCodeRegistry('config_creg')
    adapter_creg_config = TypedDictConfig().piece_list_to_config(
        service_to_config_pieces[htypes.adapter_creg()])
    adapter_creg = AdapterCodeRegistry('adapter_creg', adapter_creg_config)
    service_creg_config = DataDictConfig().piece_list_to_config(
        service_to_config_pieces[htypes.service_creg()])
    print("service_creg_config:", service_creg_config)
    service_creg = ServiceCodeRegistry(adapter_creg, service_creg_config)
    adapter_creg.set_service_creg(service_creg)
    service_config_creg_config = TypedDictConfig().piece_list_to_config(
        service_to_config_pieces[data.system.service.service_config_creg])
    service_config_creg = service_creg.animate(data.system.service.service_config_creg)
    service_config_creg.update_config(service_config_creg_config)
    return service_creg


def service_config_creg():
    return CachedResolvingCodeRegistry('service_config_creg')
