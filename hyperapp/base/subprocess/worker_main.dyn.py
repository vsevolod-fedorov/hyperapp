from . import htypes
from .code.subprocess.transport import SubprocessRoute


def subprocess_worker_main(
        bundler, transport, peer_creg, generate_rsa_identity,
        connection, process_id, master_peer):
    print("worker main:", process_id)
    master = peer_creg.animate(master_peer)
    transport.add_internal_route(master, SubprocessRoute(bundler, 'master', connection))
    identity = generate_rsa_identity(fast=True)
    message = htypes.subprocess.worker_started_report(
        process_id=process_id,
        )
    transport.send_message(master, identity, message)
