from .code.make_partial import make_partial
from .data.subprocess_main import subprocess_main


def compile_resources():
    print("rc compile resources")


def main(identity_creg, generate_rsa_identity, subprocess_server_running, transport, compile_resources, args):
    print("rc main service:", args)
    print("identity_creg:", identity_creg)
    print("transport:", transport)
    compile_resources()
    master_identity = generate_rsa_identity(fast=True)
    print("master identity:", master_identity)
    with subprocess_server_running(master_identity, 'sample', count=2, timeout_sec=5, start_timeout_sec=5):
        print("subprocess is running")
    print("subprocess is finished")
