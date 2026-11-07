from dataclasses import dataclass

from . import htypes
from .services import (
    mosaic,
    web,
    )
from .code.path import Path


class Constructor:

    def __init__(self, path, key):
        _validate_identity(path, key)
        self.path = path
        self.key = key

    @property
    def piece(self):
        raise NotImplementedError(self)


def _validate_identity(path, key):
    if not isinstance(path, Path) or not path.project or not path.path or not all(path.path):
        raise ValueError(f"Invalid constructor provider: {path!r}")
    if not isinstance(key, str) or not key:
        raise ValueError(f"Invalid constructor key: {key!r}")


def constructor_ref(ctr):
    if not isinstance(ctr, Constructor):
        raise TypeError(f"Not a constructor: {ctr!r}")
    _validate_identity(ctr.path, ctr.key)
    return mosaic.put(htypes.constructor.constructor(
        path=ctr.path.piece,
        key=ctr.key,
        payload=mosaic.put(ctr.piece),
        ))


@dataclass(frozen=True)
class ConstructorEntry:
    ref: object
    payload: object
    constructor: Constructor
    source_target: str


# The decoder registry is a service; accepted constructors belong to a single compilation.
# Preparing a whole batch before updating this mapping prevents a bad later entry from
# leaving earlier entries attached. No concrete constructor hook mutates the graph here.
class ConstructorRegistry:

    def __init__(self):
        self._by_path = {}  # Path -> key -> ConstructorEntry.

    def prepare(self, rc_constructor_creg, refs, allowed_paths, source_target):
        pending = {}
        for ref in refs:
            piece = web.summon(ref)
            if not isinstance(piece, htypes.constructor.constructor):
                raise TypeError(f"Invalid constructor envelope: {piece!r}")
            path = Path.from_piece(piece.path)
            _validate_identity(path, piece.key)
            if path not in allowed_paths:
                raise ValueError(f"Constructor {piece.key!r} has unexpected provider {path}")
            try:
                ctr = rc_constructor_creg.invite(piece.payload)
                if not isinstance(ctr, Constructor) or ctr.path != path or ctr.key != piece.key:
                    raise ValueError(f"Constructor ownership/key mismatch for {path}: {piece.key!r}")
                if constructor_ref(ctr) != ref:
                    raise ValueError(f"Constructor round trip mismatch for {path}: {piece.key!r}")
                payload = web.summon(piece.payload)
            except Exception as x:
                x.add_note(f"While decoding constructor {path}: {piece.key!r} from {source_target}")
                raise
            entries = pending.setdefault(path, {})
            previous = entries.get(piece.key, self._by_path.get(path, {}).get(piece.key))
            if previous is not None and previous.ref != ref:
                raise ValueError(
                    f"Conflicting constructor {path}: {piece.key!r} from {source_target};"
                    f" previous discovery from {previous.source_target}")
            entries[piece.key] = previous or ConstructorEntry(ref, payload, ctr, source_target)
        return pending

    def apply(self, pending):
        for path, entries in pending.items():
            self._by_path.setdefault(path, {}).update(entries)

    def for_path(self, path):
        return tuple(entry.constructor for key, entry in sorted(self._by_path.get(path, {}).items()))

    @property
    def pieces(self):
        # Inspection reports the validated wire snapshot, even if a consumer changes a constructor.
        return {
            path: tuple(entry.payload for key, entry in sorted(self._by_path[path].items()))
            for path in sorted(self._by_path, key=str)
            }
