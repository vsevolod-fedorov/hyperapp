import itertools
from contextlib import ExitStack, contextmanager


from .code.make_partial import make_partial
from .code.futures import get_process_future
from .data.worker_boot import boot as worker_boot


_process_id_counter = itertools.count()


def subprocess_workers_running(
        transport,
        subprocess_running,
        ):

    @contextmanager
    def _subprocess_workers_running(master_identity, name, count, timeout_sec, start_timeout_sec):
        with ExitStack() as stack:
            for idx in range(count):
                process_id = next(_process_id_counter)
                future = get_process_future(process_id)
                main = make_partial(
                    worker_boot, process_id=process_id, master_peer=master_identity.peer.piece)
                rec = stack.enter_context(subprocess_running(f'{name}-{idx:02d}', main))
                print(rec.connection)
            yield

    return _subprocess_workers_running
