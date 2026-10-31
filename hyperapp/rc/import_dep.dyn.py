from dataclasses import dataclass

from . import htypes
from .services import (
    mosaic,
    )


# Import can not be resolved to a target. Fails the target having the import.
class UnresolvedImportError(Exception):
    pass


# Requirement resolved to a target, like a module one. Reqs importing the same thing give equal deps.
@dataclass(frozen=True)
class ImportDep:
    import_path: tuple[str]  # import_as prefix naming the module.
    target: object

    def make_cfg_item(self):
        return htypes.import_recorder.import_cfg_item(
            import_path=self.import_path,
            resource=mosaic.put(self.target.result),
            )

    def make_import(self):
        rec = htypes.builtin.import_rec(
            full_name='.'.join(self.import_path),
            resource=mosaic.put(self.target.result),
            )
        return htypes.builtin.imports(
            pyobj=(rec,),
            raw=(),
            )
