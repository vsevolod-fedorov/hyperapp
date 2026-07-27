

def typed_dict_config_adapter(piece, spiece, fn, service_config_creg):
    config = service_config_creg.animate(spiece)
    assert 0, (config, piece, spiece, fn)


def service_object_adapter(piece, spiece, fn):
    return fn()
