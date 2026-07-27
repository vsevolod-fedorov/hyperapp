

def typed_dict_config_adapter(piece, spiece, fn, service_config_creg):
    assert 0, (piece, spiece, fn, service_config_creg)


def service_object_adapter(piece, spiece, fn):
    return fn()
