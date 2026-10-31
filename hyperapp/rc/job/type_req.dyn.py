from . import htypes


def import_to_type_req(path, prefix, import_path):
    return htypes.type_req.type_req(
        path=path.piece,
        prefix=prefix,
        import_as=import_path,
        )
