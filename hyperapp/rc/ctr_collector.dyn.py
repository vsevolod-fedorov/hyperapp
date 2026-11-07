import sys
from dataclasses import dataclass, replace

from .services import (
    mosaic,
    )
from .code.probe import real_fn
from .code.constructor import constructor_ref
from .data import ctr_collector_service


COLLECTOR_REF = mosaic.put(ctr_collector_service)
_DECLARATIONS = '_rc_constructor_declarations'


class ConstructorCollectionError(Exception):
    pass


@dataclass(frozen=True)
class ConstructorDiscovery:
    module_name: str
    constructor: object


@dataclass(frozen=True)
class ConstructorDeclaration:
    module_name: str
    ref: object


@dataclass(frozen=True)
class ModuleDeclarations:
    module_ref: object
    path_piece: object
    refs: tuple = ()


def _module_declarations(module, active):
    declarations = vars(module).get(_DECLARATIONS)
    if declarations is None:
        return ModuleDeclarations(active.ref, active.path.piece)
    if declarations.module_ref != active.ref or declarations.path_piece != active.path.piece:
        raise ConstructorCollectionError(f"Constructor declaration identity mismatch: {active.path}")
    return declarations


# A facade over the existing job sink, not a second collection scope. Only serialized
# declarations survive, on the exact cached module that executed their decorators.
class CtrCollector:

    def __init__(self, context, modules):
        self._context = context
        self._modules = context.state_for(self)
        self._modules.update(modules)

    def _provider(self, ctr, fn):
        self._context.state_for(self)  # Reject a retained collector after job cleanup.
        module_name = real_fn(fn).__module__
        module = self._modules.get(module_name)
        if module is None:
            return None  # Includes cached probe-wrapped functions of the test module itself.
        if ctr.path != module.path:
            raise ConstructorCollectionError(f"Constructor provider {ctr.path} does not match {module.path}")
        return module_name

    def add_constructor(self, ctr, fn):
        try:
            if (name := self._provider(ctr, fn)) is not None:
                self._context.discoveries.add(ConstructorDiscovery(name, ctr))
        except Exception as x:
            raise ConstructorCollectionError(f"Error collecting constructor: {x}") from x

    def declare(self, ctr, fn):
        try:
            name = self._provider(ctr, fn)
            if name is None:
                return
            module = sys.modules[name]
            if not module.__spec__._initializing:
                raise ValueError("Constructor declarations must be made during module import")
            declarations = _module_declarations(module, self._modules[name])
            ref = constructor_ref(ctr)
            # Metadata contains pieces/refs only, never a probe, constructor, job service or callback.
            setattr(module, _DECLARATIONS, replace(declarations, refs=(*declarations.refs, ref)))
            self._context.discoveries.add(ConstructorDeclaration(name, ref))
        except Exception as x:
            raise ConstructorCollectionError(f"Error declaring constructor: {x}") from x

    def snapshot(self):
        self._context.state_for(self)
        refs = set()
        for name, active in self._modules.items():
            module = sys.modules.get(name)
            if module is None:
                continue
            refs.update(_module_declarations(module, active).refs)
        for entry in self._context.discoveries.entries:
            # Other discovery protocols stay opaque, even if they happen to expose a 'piece'.
            if isinstance(entry, ConstructorDeclaration):
                refs.add(entry.ref)
            elif isinstance(entry, ConstructorDiscovery):
                active = self._modules.get(entry.module_name)
                if active is None or active.path != entry.constructor.path:
                    raise ConstructorCollectionError("Constructor discovery has an inactive provider")
                refs.add(constructor_ref(entry.constructor))
        return tuple(sorted(refs, key=lambda ref: (ref.hash_algorithm, ref.hash)))


def constructor_snapshot(context):
    return context.invite(COLLECTOR_REF).snapshot()


# Decorator errors pass through the Python importer's exception wrappers.
def find_collection_error(error):
    while error is not None:
        if isinstance(error, ConstructorCollectionError):
            return error
        error = error.__cause__ or error.__context__
    return None
