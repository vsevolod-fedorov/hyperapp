from . import htypes


def import_to_code_req(path, import_path):
    return htypes.code_req.code_req(
        path=path.piece,
        import_as=import_path,
        )
