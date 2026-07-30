import inspect
from functools import partial


def typed_dict_config_adapter(piece, spiece, fn, service_config_creg):
    rec = service_config_creg.animate(spiece)
    return partial(fn, rec.config)


def _make_partial(fn, params):
    fn_params = list(inspect.signature(fn).parameters)
    for fname, name in zip(fn_params, params):
        if fname != name:
            raise RuntimeError(
                f"Wrong service parameter order for {fn}: {list(params)} vs actual {fn_params}")
    return partial(fn, *params.values())


def service_args_adapter(piece, spiece, fn, service_creg):
    args = {
        rec.name: service_creg.invite(rec.service)
        for rec in piece.args
        }
    if not args:
        return fn
    return _make_partial(fn, args)


def service_object_adapter(piece, spiece, fn):
    return fn()
