from .services import (
    pyobj_creg,
    )


def import_to_req(config, path, import_path):
    for key, actor in config.items():
        if import_path[:len(key)] == key:
            req_ctr = pyobj_creg.invite(actor.fn)
            return req_ctr(path, import_path)
    raise RuntimeError(f"Unknown import prefix: {'.'.join(import_path)}")
