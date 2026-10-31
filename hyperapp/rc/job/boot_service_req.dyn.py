from . import htypes


def import_to_boot_service_req(path, prefix, import_path):
    return htypes.boot_service_req.boot_service_req(
        path=path.piece,
        prefix=prefix,
        import_as=import_path,
        )
