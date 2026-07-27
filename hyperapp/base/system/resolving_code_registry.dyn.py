from functools import partial

from hyperapp.boot.config_key_error import ConfigKeyError
from hyperapp.boot.code_registry import CodeRegistry
from hyperapp.boot.cached_code_registry import CachedCodeRegistry

from . import htypes
from .services import (
  mosaic,
  pyobj_creg,
  web,
  )


class ResolvingCodeRegistry(CodeRegistry):

    def __init__(self, service_name, config=None):
        super().__init__(pyobj_creg, web, service_name, {})
        self._unresolved_config = config or {}

    def update_config(self, config):
        self._unresolved_config.update(config)

    def _resolve(self, t):
        try:
            return super()._resolve(t)
        except KeyError:
            pass
        actor = self._unresolved_config[t]
        return pyobj_creg.invite(actor.fn)


class CachedResolvingCodeRegistry(CachedCodeRegistry):

    def __init__(self, service_name, config=None):
        super().__init__(mosaic, pyobj_creg, web, service_name, {})
        self._unresolved_config = config or {}

    def update_config(self, config):
        self._unresolved_config.update(config)

    def _resolve(self, t):
        try:
            return super()._resolve(t)
        except KeyError:
            pass
        actor = self._unresolved_config[t]
        return pyobj_creg.invite(actor.fn)


class AdapterCodeRegistry(ResolvingCodeRegistry):

    def __init__(self, service_name, config):
        super().__init__(service_name, config)
        self._service_creg = None

    def set_service_creg(self, service_creg):
        self._service_creg = service_creg

    def _resolve(self, t):
        try:
            return CodeRegistry._resolve(self, t)
        except KeyError:
            pass
        actor = self._unresolved_config[t]
        service_params = {
            rec.name: self._service_creg.invite(rec.service)
            for rec in actor.service_params
            }
        fn = pyobj_creg.invite(actor.fn)
        if service_params:
            fn = partial(fn, **service_params)
        return fn


class ServiceCodeRegistry:

    def __init__(self, adapter_creg, config):
        self._config = config
        self._adapter_creg = adapter_creg
        self._cache = {}  # piece -> actor

    def invite(self, ref):
        assert isinstance(ref, htypes.builtin.ref), repr(ref)
        value = web.summon(ref)
        return self.animate(value)

    def animate(self, piece):
        try:
            return self._cache[piece]
        except KeyError:
            pass
        try:
            actor = self._config[piece]
        except KeyError:
            raise ConfigKeyError('service_creg', piece)
        service_params = {
            rec.name: self.invite(rec.service)
            for rec in actor.service_params
            }
        fn = pyobj_creg.invite(actor.fn)
        if service_params:
            fn = partial(fn, **service_params)
        for adapter_ref in actor.adapters:
            fn = self._adapter_creg.invite(adapter_ref, piece, fn)
        self._cache[piece] = fn
        return fn
