import codecs
import logging
import multiprocessing
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from hyperapp.boot.ref import hash_sha512
from hyperapp.boot.htypes.packet_coders import packet_coders

from .services import (
    mosaic,
    )
from .data.subprocess import mp_main

log = logging.getLogger(__name__)


_mp_context = multiprocessing.get_context('spawn')


class _Subprocess:

    def __init__(self, process, connection, sent_refs):
        self.process = process
        self.connection = connection
        self.sent_refs = sent_refs


def _cache_dir():
    runtime_dir = (
        os.environ.get('XDG_RUNTIME_DIR')
        or tempfile.gettempdir()
        )
    dir = Path(runtime_dir) / 'hyperapp/subprocess/source'
    dir.mkdir(parents=True, exist_ok=True)
    return dir


def _prepare_mp_main(dir):
    data = mp_main.data
    hash = hash_sha512(data)
    suffix = codecs.encode(hash[:4], 'hex').decode()
    path = dir / f'subprocess_mp_main_{suffix}.py'
    if not path.exists():
        path.write_bytes(data)
    return path


def subprocess_running(bundler):

    @contextmanager
    def _subprocess_running(name, main_fn_piece):
        dir = _cache_dir()
        mp_main_path = _prepare_mp_main(dir)
        sys.path.append(str(dir))
        module = __import__(mp_main_path.stem, level=0)
        subprocess_main = module.subprocess_main

        refs_and_bundle = bundler(mosaic.put(main_fn_piece))
        bundle_cdr = packet_coders.encode('cdr', refs_and_bundle.bundle)
        log.debug("Subprocess %s: Packed main function. Bundle size: %.2f KB", name, len(bundle_cdr)/1024)

        parent_connection, child_connection = _mp_context.Pipe()
        subprocess_args = [name, child_connection, bundle_cdr]
        process = _mp_context.Process(target=subprocess_main, args=subprocess_args)
        process.start()

        try:
            yield _Subprocess(process, parent_connection, refs_and_bundle.ref_set)
        finally:
            parent_connection.close()  # Signal child to stop.
            log.debug("Joining process %s...", name)
            process.join()
            log.debug("Joining process %s: done", name)

    return _subprocess_running
