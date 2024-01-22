import logging
from functools import partial

from hyperapp.common.htypes import bundle_t
from hyperapp.common.htypes.packet_coders import packet_coders

from .services import (
    bundler,
    mark,
    mosaic,
    unbundler,
    )

log = logging.getLogger(__name__)


DEFAULT_ENCODING = 'json'


class FileBundle:

    def __init__(self, path, encoding=DEFAULT_ENCODING):
        self.path = path
        self._encoding = encoding

    def save_ref(self, ref):
        bundle = bundler([ref]).bundle
        data = packet_coders.encode(self._encoding, bundle)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_bytes(data)
        log.info("Saved %s to %s (%d bytes)", ref, self.path, len(data))

    def load_ref(self):
        bundle = packet_coders.decode(self._encoding, self.path.read_bytes(), bundle_t)
        unbundler.register_bundle(bundle)
        ref_count = len(bundle.roots)
        if ref_count != 1:
            raise RuntimeError(f"Bundle {self.path} has {ref_count} refs, but expected only one")
        return bundle.roots[0]

    def save_piece(self, piece):
        log.info("Save %s to %s", piece, self.path)
        ref = mosaic.put(piece)
        self.save_ref(ref)

    def load_piece(self):
        ref = self.load_ref()
        return mosaic.resolve_ref(ref).value


@mark.service
def file_bundle():
    return FileBundle
