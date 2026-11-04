from contextlib import contextmanager
from functools import partial

from .services import (
    pyobj_creg,
    )


class MarkerRegistry:

    def __init__(self, config, resolve_service=None):
        self._config = config  # Marker name tuple -> system actor.
        self._resolve_service = resolve_service

    # Lookup is worker-scoped; dependency resolution belongs entirely to the running job, including
    # dependencies of injected services. There is no fallback to worker-owned service instances.
    @contextmanager
    def bound(self, resolve_service):
        registry = MarkerRegistry(self._config, resolve_service)
        try:
            yield registry
        finally:
            registry._resolve_service = None

    def make_marker(self, marker_path, provider_path):
        if self._resolve_service is None:
            raise RuntimeError("Marker registry has no active job binding")
        try:
            actor = self._config[marker_path]
        except KeyError:
            raise RuntimeError(
                f"Unknown marker {'.'.join(marker_path)!r} for module {provider_path}") from None
        service_params = {
            rec.name: self._resolve_service(rec.service)
            for rec in actor.service_params
            }
        template = pyobj_creg.invite(actor.fn)
        if type(template) is type:
            # Class-backed marker: provider Path is the first constructor argument.
            return template(provider_path, **service_params)
        # Function-backed marker: provider Path is a keyword, leaving decorator arguments positional.
        return partial(template, **{**service_params, 'path': provider_path})


def marker_registry(config):
    return MarkerRegistry(config)
