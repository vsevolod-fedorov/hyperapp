import logging

from . import htypes
from .code.selectors import StopSignal
from .code.subprocess.transport import IncomingConnection, SubprocessRoute

log = logging.getLogger(__name__)


def subprocess_worker_main(
        bundler, selectors, transport, peer_creg, generate_rsa_identity,
        connection, process_id, master_peer):
    log.info("Worker %d is starting", process_id)
    master = peer_creg.animate(master_peer)
    transport.add_internal_route(master, SubprocessRoute(bundler, 'master', connection))
    stop_signal = StopSignal()
    selectors.register(stop_signal)
    connection = IncomingConnection(
        selectors, transport, f"worker#{process_id}", connection, on_eof=stop_signal.fire)
    selectors.register(connection)
    identity = generate_rsa_identity(fast=True)
    message = htypes.subprocess.worker_started_report(
        process_id=process_id,
        )
    transport.send_message(master, identity, message)
    log.info("Worker %d is running", process_id)
    selectors.run()
    log.info("Worker %d is exiting", process_id)
