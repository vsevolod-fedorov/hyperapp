import itertools
from contextlib import ExitStack, contextmanager


from .code.make_partial import make_partial
from .code.futures import get_process_future
from .data.server_boot import boot as server_boot


_process_id_counter = itertools.count()


def subprocess_server_running(
        transport,
        subprocess_running,
        ):

    @contextmanager
    def _subprocess_server_running(master_identity, name, count, timeout_sec, start_timeout_sec):
        with ExitStack() as stack:
            for idx in range(count):
                process_id = next(_process_id_counter)
                future = get_process_future(process_id)
                main = make_partial(server_boot, process_id=process_id)
                rec = stack.enter_context(subprocess_running(f'{name}-{idx:02d}', main))
                print(rec.connection)
            yield

    return _subprocess_server_running
