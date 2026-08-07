from collections import defaultdict, namedtuple
from datetime import datetime
import logging

from hyperapp.boot.htypes import ref_t, bundle_t
from hyperapp.boot.util import is_list_inst

from .services import (
    association_reg,
    mosaic,
    pyobj_creg,
    )

log = logging.getLogger(__name__)


ITERATION_LIMIT = 100000

_RefsAndBundle = namedtuple('_RefsAndBundle', 'ref_set bundle')


def _capsule_size(capsule):
    return len(capsule.encoded_object)  # TODO: Calculate full capsule size.


class _Batch:

    def __init__(self, visited):
        self.capsules = []
        self.visited = set(visited)

    def __iadd__(self, batch):
        self.capsules += batch.capsules
        self.visited |= batch.visited
        return self

    @property
    def size(self):
        return sum(
            _capsule_size(capsule)
            for capsule in self.capsules
            )


class Bundler:

    def __init__(self, assoc_pickers, pick_refs):
        self._assoc_pickers = assoc_pickers
        self._pick_refs = pick_refs
        self._missing_ref_count = 0
        self._seen_asss = set()
        self._processed_count = 0

    def run(self, target_ref, seen_refs, size_limit):
        log.debug("Making bundle from ref: %s", target_ref)
        batch = self._collect_batch(target_ref, seen_refs or set(), size_limit)
        if self._missing_ref_count:
            log.warning("Failed to resolve %d refs", self._missing_ref_count)
        bundle = bundle_t(
            root=target_ref,
            associations=tuple(self._seen_asss),
            capsule_list=tuple(batch.capsules),
            )
        return _RefsAndBundle(batch.visited, bundle)

    def _collect_batch(self, target_ref, visited, size_limit=None):
        batch = _Batch(visited)
        unvisited = [target_ref]
        while unvisited:
            if self._processed_count > ITERATION_LIMIT:
                raise RuntimeError(f"Bundler: Reached iteration limit {ITERATION_LIMIT}")
            ref = unvisited.pop(0)
            if ref.hash_algorithm == 'phony':
                continue
            if ref in batch.visited:
                continue
            try:
                rec = mosaic.resolve_ref(ref)
            except KeyError:
                log.warning("Failed to resolve ref %s", ref)
                self._missing_ref_count += 1
                continue
            type_batch = self._collect_batch(rec.type_ref, batch.visited)
            if size_limit:
                size = type_batch.size + _capsule_size(rec.capsule)
                if size > size_limit:
                    if not batch.capsules:
                        raise RuntimeError(f"Root capsule of size {size} did not fit in limit {size_limit}")
                    break
            batch += type_batch
            batch.capsules.append(rec.capsule)
            batch.visited.add(ref)
            unvisited += self._pick_refs(rec.value, rec.t)
            self._processed_count += 1
        return batch

    # def _collect_associations(self, ref, t, value):
    #     result = []
    #     t_res = pyobj_creg.actor_to_piece(t)
    #     for obj in [t_res, value]:
    #         for ass in association_reg.base_to_ass_list(obj):
    #             piece = ass.to_piece(mosaic)
    #             ass_ref = mosaic.put(piece)
    #             log.debug("Bundle association %s: %s (%s)", ass_ref, ass, piece)
    #             result.append(ass_ref)
    #     return result


def bundler(assoc_pickers, pick_refs, ref, seen_refs=None, size_limit=None):
    assert isinstance(ref, ref_t), repr(ref)
    return Bundler(assoc_pickers, pick_refs).run(ref, seen_refs, size_limit)
