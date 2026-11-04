from functools import partial

from .services import (
    pyobj_creg,
    )


class MarkerRegistry:

    def __init__(self, service_creg, config):
        self._service_creg = service_creg
        self._config = config  # Marker name tuple -> system actor.

    def make_marker(self, marker_path, provider_path):
        try:
            actor = self._config[marker_path]
        except KeyError:
            raise RuntimeError(
                f"Unknown marker {'.'.join(marker_path)!r} for module {provider_path}") from None
        service_params = {
            rec.name: self._service_creg.invite(rec.service)
            for rec in actor.service_params
            }
        template = pyobj_creg.invite(actor.fn)
        if type(template) is type:
            # Class-backed marker: provider Path is the first constructor argument.
            return template(provider_path, **service_params)
        # Function-backed marker: provider Path is a keyword, leaving decorator arguments positional.
        return partial(template, **{**service_params, 'path': provider_path})


def marker_registry(service_creg, config):
    return MarkerRegistry(service_creg, config)
