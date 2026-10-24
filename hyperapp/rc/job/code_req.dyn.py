from . import htypes


def import_to_code_req(path, prefix, import_path):
    return htypes.code_req.code_req(
        path=path.piece,
        prefix=prefix,
        import_as=import_path,
        )


def import_to_tested_code_req(path, prefix, import_path):
    return htypes.code_req.tested_code_req(
        path=path.piece,
        prefix=prefix,
        import_as=import_path,
        )
