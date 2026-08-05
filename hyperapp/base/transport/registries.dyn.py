
def identity_creg(config, system_code_registry_factory):
    return system_code_registry_factory('identity_creg', config)


def peer_creg(config, system_code_registry_factory):
    return system_code_registry_factory('peer_creg', config)


def signature_creg(config, system_code_registry_factory):
    return system_code_registry_factory('signature_creg', config)


def parcel_creg(config, system_code_registry_factory):
    return system_code_registry_factory('parcel_creg', config)


def route_creg(config, system_code_registry_factory):
    return system_code_registry_factory('route_creg', config)


def message_creg(config, system_code_registry_factory):
    return system_code_registry_factory('message_creg', config)
