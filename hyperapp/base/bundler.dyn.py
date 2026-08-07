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
    return len(capsule.encoded_object)  # TODO: Calculate full capsule size; Add association sizes.


class _Batch:

    def __init__(self, visited):
        self.capsules = []
        self.visited = set(visited)  # ref set
        self.assocs = []  # ref list

    def __iadd__(self, batch):
        self.capsules += batch.capsules
        self.visited |= batch.visited
        self.assocs += batch.assocs
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
        self._processed_count = 0

    def run(self, target_ref, seen_refs, size_limit):
        log.debug("Making bundle from ref: %s", target_ref)
        batch = self._collect_batch(target_ref, seen_refs or set(), size_limit)
        if self._missing_ref_count:
            log.warning("Failed to resolve %d refs", self._missing_ref_count)
        bundle = bundle_t(
            root=target_ref,
            associations=tuple(batch.assocs),
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
            assoc_batch, assoc_unvisited = self._pick_associations(
                rec.value, batch.visited | type_batch.visited)
            if size_limit:
                size = type_batch.size + assoc_batch.size + _capsule_size(rec.capsule)
                if size > size_limit:
                    if not batch.capsules:
                        raise RuntimeError(f"Root capsule of size {size} did not fit in limit {size_limit}")
                    break
            batch += type_batch
            batch += assoc_batch
            batch.capsules.append(rec.capsule)
            batch.visited.add(ref)
            unvisited += assoc_unvisited
            unvisited += self._pick_refs(rec.value, rec.t)
            self._processed_count += 1
        return batch

    def _pick_associations(self, value, visited):
        unvisited = []
        assoc_list = []
        for picker in self._assoc_pickers:
            new_list = picker(value)
            if new_list:
                log.debug("Bundle associations from %s: %s", picker, new_list)
                assoc_list += new_list
        batch = _Batch(visited)
        for assoc in assoc_list:
            rec = mosaic.put_for_rec(assoc)
            if rec.ref in visited:
                continue
            type_batch = self._collect_batch(rec.type_ref, batch.visited)
            batch += type_batch
            batch.assocs.append(rec.ref)
            batch.capsules.append(rec.capsule)
            batch.visited.add(rec.ref)
            unvisited += self._pick_refs(assoc, rec.t)
        return (batch, unvisited)


def bundler(assoc_pickers, pick_refs, ref, seen_refs=None, size_limit=None):
    assert isinstance(ref, ref_t), repr(ref)
    return Bundler(assoc_pickers, pick_refs).run(ref, seen_refs, size_limit)
