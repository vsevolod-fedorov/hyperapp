from functools import partial


def typed_dict_config_adapter(piece, spiece, fn, service_config_creg):
    rec = service_config_creg.animate(spiece)
    return partial(fn, rec.config)


def service_object_adapter(piece, spiece, fn):
    return fn()
