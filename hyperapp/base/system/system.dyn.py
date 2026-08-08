from .services import (
    web,
    )
from .code.code_registry import (
    ResolvingCodeRegistry,
    CachedResolvingCodeRegistry,
    AdapterCodeRegistry,
    ServiceCodeRegistry,
    )
from .code.config import TypedDictConfigCtl, DataDictConfigCtl
from . import data


def setup_system(config_piece_list):
    service_to_config_pieces = {}
    for config in config_piece_list:
        for rec in config.services:
            service = web.summon(rec.service)
            service_config = web.summon(rec.config)
            service_to_config_pieces.setdefault(service, []).append(service_config)

    config_creg = ResolvingCodeRegistry('config_creg')
    adapter_creg_config = TypedDictConfigCtl().piece_list_to_config(
        service_to_config_pieces[data.system.service.adapter_creg])
    adapter_creg = AdapterCodeRegistry('adapter_creg', adapter_creg_config)
    service_creg_config = TypedDictConfigCtl().piece_list_to_config(
        service_to_config_pieces[data.system.service.service_creg])
    service_creg = ServiceCodeRegistry(adapter_creg, service_creg_config)
    service_creg.add_to_cache(data.system.service.service_creg, service_creg)
    adapter_creg.set_service_creg(service_creg)
    service_config_creg_config = TypedDictConfigCtl().piece_list_to_config(
        service_to_config_pieces[data.system.service.service_config_creg])
    service_config_creg = service_creg.animate(data.system.service.service_config_creg)
    service_config_creg.update_config(service_config_creg_config)

    for service, config_pieces in service_to_config_pieces.items():
        if service in {data.system.service.adapter_creg,
                       data.system.service.service_creg,
                       data.system.service.service_config_creg}:
            continue
        rec = service_config_creg.animate(service)
        rec.config = rec.ctl.piece_list_to_config(config_pieces)

    return service_creg


def service_config_creg():
    return CachedResolvingCodeRegistry('service_config_creg')
