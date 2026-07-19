from hyperapp.boot.config_key_error import ConfigKeyError
from hyperapp.boot.cached_code_registry import CachedCodeRegistry

from .services import (
  mosaic,
  pyobj_creg,
  web,
  )


class ResolvingCodeRegistry(CachedCodeRegistry):

    def __init__(self, service_name, config):
        super().__init__(mosaic, pyobj_creg, web, service_name, config)


class AdapterCodeRegistry(ResolvingCodeRegistry):

    def __init__(self, service_name, config):
        super().__init__(service_name, config)
        self._service_creg = None

    def set_service_creg(self, service_creg):
        self._service_creg = service_creg


class ServiceCodeRegistry:

    def __init__(self, adapter_creg, config):
        self._config = config
        self._adapter_creg = adapter_creg

    def animate(self, piece):
        try:
            actor = self._config[piece]
        except KeyError:
            raise ConfigKeyError('service_creg', piece)
        fn = pyobj_creg.invite(actor.fn)
        return fn
