from .services import (
    pyobj_creg,
    )


def import_to_req(config, path, import_path):
    for key, actor in config.items():
        if import_path[:len(key)] == key:
            if len(import_path) == len(key):
                return None  # Lone prefix, like 'code'.
            req_ctr = pyobj_creg.invite(actor.fn)
            # Prefix is passed, so requirements do not repeat what they are registered with.
            return req_ctr(path, key, import_path)
    raise RuntimeError(f"Unknown import prefix: {'.'.join(import_path)}")
