from contextlib import contextmanager
from dataclasses import dataclass

from . import htypes
from .services import (
    pyobj_creg,
    web,
    )
from .code.import_recorder import module_recorder_piece, recorded_python_module_name
from .code.mark import markers_activated
from .code.path import Path
from .code.probe import ProbeContext
from .code.ctr_collector import CtrCollector
from .data import ctr_collector_service
from .data.probe import probe_context_service


@dataclass(frozen=True)
class ActiveModule:
    path: Path
    ref: object


# Only the test's local providers get recorders, including during test-module import retries.
# Foreign subjects and other complete dependencies keep their ordinary, inactive marker behavior.
# Returns (dynamic module name -> ActiveModule, (provider Path, recorder) list).
def tested_modules(cfg_items):
    active_modules = {}
    tested_recorders = []
    for item in cfg_items:
        if not isinstance(item, htypes.import_recorder.import_cfg_item):
            continue
        module_piece = web.summon(item.resource)
        recorder_piece = module_recorder_piece(module_piece)
        if recorder_piece is None:
            continue
        path = Path.from_piece(recorder_piece.module_path)
        name = recorded_python_module_name(module_piece)
        active_modules[name] = ActiveModule(path, item.resource)
        tested_recorders.append((path, pyobj_creg.animate(recorder_piece)))
    return active_modules, tested_recorders


@contextmanager
def job_active(subsystem_factory, marker_registry, active_modules):
    with ProbeContext() as context:
        collector = CtrCollector(context, active_modules)
        service_creg = subsystem_factory(service_instances={
            probe_context_service: context,
            ctr_collector_service: collector,
            })
        context.bind_services(service_creg.invite)
        with (
                marker_registry.bound(context.invite) as bound,
                markers_activated(bound, {name: module.path for name, module in active_modules.items()}),
                ):
            yield context
