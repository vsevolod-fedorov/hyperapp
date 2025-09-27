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


BUNDLED_REFS_LIMIT = 100000

_RefsAndBundle = namedtuple('_RefsAndBundle', 'ref_set bundle')


class Bundler:

    def __init__(self, pick_refs):
        self._pick_refs = pick_refs

    def bundle(self, ref_list, seen_refs=None, size_limit=None):
        assert is_list_inst(ref_list, ref_t), repr(ref_list)
        log.debug("Making bundle from refs: %s", [str(ref) for ref in ref_list])
        refs, asss, capsule_list = self._collect_capsule_list(ref_list, seen_refs or [], size_limit)
        bundle = bundle_t(
            roots=tuple(ref_list),
            associations=tuple(asss),
            capsule_list=tuple(capsule_list),
            )
        return _RefsAndBundle(refs, bundle)

    def _collect_capsule_list(self, ref_list, seen_refs, size_limit):
        result_capsule_list = []  # Capsules within size limit
        result_size = 0
        current_capsule_list = []  # Current ref capsule and it's type dependencies.
        current_size = 0
        missing_ref_count = 0
        seen_asss = set()
        visited_refs = set(seen_refs)
        unvisited_refs = [*ref_list]
        current_refs = []
        type_idx = {}  # ref -> index of type in current capsule list.
        current_types = set()  # Type refs in current block.

        i = 0
        while unvisited_refs or current_refs:
            if i > BUNDLED_REFS_LIMIT:
                raise RuntimeError(f"Bundler: Reached refs limit {BUNDLED_REFS_LIMIT}")
            if current_refs:
                # Types and their deps should come first, or unbundler won't be able to decode capsules.
                ref = current_refs.pop(0)
                target_refs = current_refs
            else:
                ref = unvisited_refs.pop(0)
                target_refs = unvisited_refs
            if ref.hash_algorithm == 'phony':
                continue
            if ref in visited_refs:
                continue
            rec = mosaic.resolve_ref(ref)
            if rec is None:
                log.warning("Failed to resolve ref %s", ref)
                missing_ref_count += 1
                continue
            if rec.type_ref in type_idx:
                target_idx = type_idx[rec.type_ref]
            else:
                target_idx = len(current_capsule_list)
            current_capsule_list.insert(target_idx, rec.capsule)
            if ref in current_types:
                type_idx[ref] = target_idx
            current_size += len(rec.capsule.encoded_object)
            if size_limit and result_size + current_size > size_limit:
                break
            if rec.type_ref.hash_algorithm != 'phony' and rec.type_ref not in visited_refs:
                current_refs.append(rec.type_ref)
                current_types.add(rec.type_ref)
            visited_refs.add(ref)
            associations = self._collect_associations(ref, rec.t, rec.value)
            current_refs += [ass for ass in associations if ass not in visited_refs]
            seen_asss |= set(associations)
            dep_refs = self._pick_refs(rec.value, rec.t)
            target_refs += [d for d in dep_refs if d not in visited_refs]
            if not current_refs:
                result_capsule_list += reversed(current_capsule_list)
                current_capsule_list = []
                result_size += current_size
                current_size = 0
                current_types = set()
            i += 1

        if not size_limit or result_size + current_size <= size_limit:
            result_capsule_list += reversed(current_capsule_list)
        if missing_ref_count:
            log.warning("Failed to resolve %d refs", missing_ref_count)
        return (visited_refs, seen_asss & visited_refs, result_capsule_list)

    def _collect_associations(self, ref, t, value):
        result = []
        t_res = pyobj_creg.actor_to_piece(t)
        for obj in [t_res, value]:
            for ass in association_reg.base_to_ass_list(obj):
                piece = ass.to_piece(mosaic)
                ass_ref = mosaic.put(piece)
                log.debug("Bundle association %s: %s (%s)", ass_ref, ass, piece)
                result.append(ass_ref)
        return result


def bundler(pick_refs, ref_list, seen_refs=None, size_limit=None):
    return Bundler(pick_refs).bundle(ref_list, seen_refs, size_limit)
