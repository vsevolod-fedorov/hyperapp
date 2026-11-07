from dataclasses import dataclass

from . import htypes
from .services import (
    mosaic,
    )
from .code.module import ModuleType


# Import can not be resolved to a target. Fails the target having the import.
class UnresolvedImportError(Exception):
    pass


class _ImportDep:

    error = None

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


# Reqs importing the same thing give equal deps.
@dataclass(frozen=True)
class ImportDep(_ImportDep):
    import_path: tuple[str]  # import_as prefix naming the module, or the type.
    target: object


# Keep the module identity in hashed dependency sets while its target is still undecided.
# Ordinary imports wait for collective classification before following the completed module target.
@dataclass(frozen=True)
class ModuleImportDep(_ImportDep):
    import_path: tuple[str]
    module: object
    tested: bool = False

    @property
    def target(self):
        if self.tested:
            return self.module.import_alias_tgt
        return self.module.module_tgt or self.module.project_imports_tgt

    @property
    def error(self):
        if self.module.type == ModuleType.TEST:
            kind = 'tested code' if self.tested else 'code'
            return f"Test module {self.module.path} cannot be imported as {kind}"
        return None


# Classification may finish after the importing job, so owners check errors when deriving their state.
def import_deps_error(deps):
    errors = {dep.error for dep in deps} - {None}
    return min(errors) if errors else None
