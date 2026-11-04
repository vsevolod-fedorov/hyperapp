from contextlib import contextmanager

from .code.mark import markers_activated
from .code.probe import ProbeContext
from .data.probe import probe_context_service


@contextmanager
def job_active(subsystem_factory, marker_registry, module_to_path):
    with ProbeContext() as context:
        service_creg = subsystem_factory(service_instances={probe_context_service: context})
        context.bind_services(service_creg.invite)
        with (
                marker_registry.bound(context.invite) as bound,
                markers_activated(bound, module_to_path),
                ):
            yield context
