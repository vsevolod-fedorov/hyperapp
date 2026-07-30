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

    def _resolve_actor(self, piece, actor):
        return pyobj_creg.invite(actor.fn)

    def _resolve(self, t, piece):
        try:
            return super()._resolve(t, piece)
        except KeyError:
            pass
        actor = self._unresolved_config[t]
        return self._resolve_actor(piece, actor)


class CachedResolvingCodeRegistry(CachedCodeRegistry):

    def __init__(self, service_name, config=None):
        super().__init__(mosaic, pyobj_creg, web, service_name, {})
        self._unresolved_config = config or {}

    def update_config(self, config):
        self._unresolved_config.update(config)

    def _resolve_actor(self, piece, actor):
        return pyobj_creg.invite(actor.fn)

    def _resolve(self, t, piece):
        try:
            return super()._resolve(t, piece)
        except KeyError:
            pass
        actor = self._unresolved_config[t]
        return self._resolve_actor(piece, actor)


class AdapterCodeRegistry(ResolvingCodeRegistry):

    def __init__(self, service_name, config):
        super().__init__(service_name, config)
        self._service_creg = None

    def set_service_creg(self, service_creg):
        self._service_creg = service_creg

    def _resolve(self, t, piece):
        try:
            return CodeRegistry._resolve(self, t, piece)
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


class ServiceCodeRegistry(CachedResolvingCodeRegistry):

    def __init__(self, adapter_creg, config):
        super().__init__('service_creg', config)
        self._adapter_creg = adapter_creg

    def _resolve_actor(self, piece, actor):
        fn = super()._resolve_actor(piece, actor)
        for adapter_ref in actor.adapters:
            fn = self._adapter_creg.invite(adapter_ref, piece, fn)
        return fn  # After adapter calls it may be object.

    def _post_process(self, fn, piece, args, kw):
        assert not args and not kw
        return fn
