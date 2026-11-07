from contextlib import contextmanager

from . import htypes
from .services import (
    pyobj_creg,
    web,
    )
from .code.import_recorder import module_recorder_piece, recorded_python_module_name
from .code.mark import markers_activated
from .code.path import Path
from .code.probe import ProbeContext
from .data.probe import probe_context_service


# Recorded dependencies are tested providers, including during test-module import retries.
# Complete dependencies have no recorder and keep their ordinary, inactive marker behavior.
def tested_modules(cfg_items):
    modules = {}
    recorders = []
    for item in cfg_items:
        if not isinstance(item, htypes.import_recorder.import_cfg_item):
            continue
        module_piece = web.summon(item.resource)
        recorder_piece = module_recorder_piece(module_piece)
        if recorder_piece is None:
            continue
        path = Path.from_piece(recorder_piece.module_path)
        name = recorded_python_module_name(module_piece)
        modules[name] = path
        recorders.append((path, pyobj_creg.animate(recorder_piece)))
    return modules, recorders


@contextmanager
def job_active(subsystem_factory, marker_registry, modules):
    with ProbeContext() as context:
        service_creg = subsystem_factory(service_instances={probe_context_service: context})
        context.bind_services(service_creg.invite)
        with (
                marker_registry.bound(context.invite) as bound,
                markers_activated(bound, modules),
                ):
            yield context
