from .services import (
    code_registry_ctr,
    )


def identity_creg(config):
    return code_registry_ctr('identity_creg', config)


def peer_registry(config):
    return code_registry_ctr('peer_registry', config)


def signature_registry(config):
    return code_registry_ctr('signature_registry', config)


def parcel_registry(config):
    return code_registry_ctr('parcel_registry', config)
