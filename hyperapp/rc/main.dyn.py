from .code.transport import LocalEndpoint


def compile_resources():
    print("rc compile resources")


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
    print("rc main service:", args)
    print("identity_creg:", identity_creg)
    print("transport:", transport)
    compile_resources()
    master_identity = generate_rsa_identity(fast=True)
    transport.add_endpoint(master_identity.peer, LocalEndpoint(message_creg, master_identity))
    print("master identity:", master_identity)
    with subprocess_workers_running(master_identity, 'sample', count=2, timeout_sec=5, start_timeout_sec=5):
        print("subprocess is running")
        selectors.run(1)
    print("subprocess is finished")
