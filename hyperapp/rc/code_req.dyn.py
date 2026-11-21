from dataclasses import dataclass

from .code.import_dep import ModuleImportDep, UnresolvedImportError
from .code.path import Path


@dataclass(frozen=True)
class CodeReq:
    path: Path
    prefix: tuple[str]
    import_as: tuple[str]

    # Code modules are compiled by jobs, not preloaded.
    is_preloaded = False
    _testing_project = None

    @classmethod
    def from_piece(cls, piece):
        return cls(
            path=Path.from_piece(piece.path),
            prefix=piece.prefix,
            import_as=piece.import_as,
            )

    def resolve(self, targets):
        # import_as is (*prefix, *module_path, *attr_path); Try longest module path first.
        prefix_len = len(self.prefix)
        sub_path = self.import_as[prefix_len:]
        for idx in range(len(sub_path), 0, -1):
            try:
                module = targets.find_nearest_module(self.path, sub_path[:idx])
            except KeyError:
                continue
            break
        else:
            raise UnresolvedImportError(f"{self.path}: Module not found for import: {'.'.join(self.import_as)}")
        if module.import_tgt is None and module.module_tgt is None:
            # Only manual modules having a module resource get a target.
            raise UnresolvedImportError(
                f"{self.path}: Manual module has no {module.path.path[-1]}.module resource"
                f" for import: {'.'.join(self.import_as)}")
        return ModuleImportDep(self.import_as[:prefix_len + idx], module, testing_project=self._testing_project)


# Test module import of a module it tests. Found the same way as code import.
@dataclass(frozen=True)
class TestedCodeReq(CodeReq):

    @property
    def _testing_project(self):
        return self.path.project
