from dataclasses import dataclass

from . import htypes
from .services import (
    mosaic,
    )
from .code.import_dep import ImportDep, UnresolvedImportError
from .code.path import Path
from .code.target.boot_service import BootServiceTarget

# The one job/boot_service_req is registered for, in worker_config.resources.yaml.
BOOT_SERVICE_IMPORT_PREFIX = ('services',)


# Import of a boot service, as services.<service name>, usually by from .services import (...).
@dataclass(frozen=True)
class BootServiceReq:
    path: Path
    prefix: tuple[str]
    import_as: tuple[str]

    # Preloaded: resolved to a loaded resource and given to recorders up front,
    # so test runs take it like a type, see TestModuleTarget.add_tested_loaded_reqs.
    is_preloaded = True

    @classmethod
    def from_piece(cls, piece):
        return cls(
            path=Path.from_piece(piece.path),
            prefix=piece.prefix,
            import_as=piece.import_as,
            )

    def resolve(self, targets):
        prefix_len = len(self.prefix)
        # Lone prefix gives no requirement, so the service name is always here.
        # Longer import path is an attribute of the service: it is recorded when the service is not resolved yet.
        name = self.import_as[prefix_len]
        try:
            piece = targets.find_boot_service(name)
        except KeyError:
            raise UnresolvedImportError(
                f"{self.path}: Boot service not found for import: {'.'.join(self.import_as)}")
        return ImportDep(self.import_as[:prefix_len + 1], BootServiceTarget.ensure(targets, name, piece))


# Boot services are loaded resources, like types, so all are given to import recorders up front.
# Services used are still recorded, giving requirements, so module resources get just these.
def boot_service_cfg_items(targets):
    return [
        htypes.import_recorder.import_cfg_item(
            import_path=(*BOOT_SERVICE_IMPORT_PREFIX, name),
            resource=mosaic.put(piece),
            )
        for name, piece in targets.boot_services.items()
        ]
