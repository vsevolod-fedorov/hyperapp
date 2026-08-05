from .code.resolving_code_registry import ResolvingCodeRegistry


def identity_creg(config):
    return ResolvingCodeRegistry('identity_creg', config)


def peer_creg(config):
    return ResolvingCodeRegistry('peer_creg', config)


def signature_creg(config):
    return ResolvingCodeRegistry('signature_creg', config)


def parcel_creg(config):
    return ResolvingCodeRegistry('parcel_creg', config)


def route_creg(config):
    return ResolvingCodeRegistry('route_creg', config)


def message_creg(config):
    return ResolvingCodeRegistry('message_creg', config)
