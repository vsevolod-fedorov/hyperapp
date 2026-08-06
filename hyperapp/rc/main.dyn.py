import logging

from .code.transport import LocalEndpoint

log = logging.getLogger(__name__)


def compile_resources():
    pass


def main(
        identity_creg,
        generate_rsa_identity,
        subprocess_workers_running,
        selectors,
        transport,
        message_creg,
        compile_resources,
        args,
        ):
    compile_resources()
    master_identity = generate_rsa_identity(fast=True)
    transport.add_endpoint(master_identity.peer, LocalEndpoint(message_creg, master_identity))
    log.info("master identity: %s", master_identity)
    with subprocess_workers_running(
            master_identity, 'sample', count=2, timeout_sec=5, start_timeout_sec=5) as workers:
        log.info("workers are running: %s", workers.peers)
        selectors.run(1)
    log.info("workers are finished")
