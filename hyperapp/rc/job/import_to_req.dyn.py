from .services import (
    pyobj_creg,
    )


def import_to_req(config, path, import_path):
    for prefix, actor in config.items():
        if import_path[:len(prefix)] == prefix:
            if len(import_path) == len(prefix):
                return None  # Lone prefix, like 'code'.
            req_ctr = pyobj_creg.invite(actor.fn)
            # Prefix is passed, so requirements do not repeat what they are registered with.
            return req_ctr(path, prefix, import_path)
    raise RuntimeError(f"Unknown import prefix: {'.'.join(import_path)}")
