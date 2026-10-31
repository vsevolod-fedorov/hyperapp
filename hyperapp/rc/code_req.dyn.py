from dataclasses import dataclass

from .code.import_dep import ImportDep, UnresolvedImportError
from .code.path import Path


@dataclass(frozen=True)
class CodeReq:
    path: Path
    prefix: tuple[str]
    import_as: tuple[str]

    # Code modules are compiled by jobs, not preloaded.
    is_preloaded = False

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
            return ImportDep(self.import_as[:prefix_len + idx], self._module_target(module))
        raise UnresolvedImportError(f"{self.path}: Module not found for import: {'.'.join(self.import_as)}")

    # Complete module, having all its imports resolved.
    def _module_target(self, module):
        if module.module_tgt is None:
            # Only manual modules having a module resource get a target.
            raise UnresolvedImportError(
                f"{self.path}: Manual module has no {module.path.path[-1]}.module resource"
                f" for import: {'.'.join(self.import_as)}")
        return module.module_tgt


# Test module import of a module it tests. Found the same way as code import.
@dataclass(frozen=True)
class TestedCodeReq(CodeReq):

    # Module as recorded by its import, so tests record what the tested module uses.
    # Manual module is not compiled, so there is nothing to record its uses for: it is tested as it is.
    def _module_target(self, module):
        if module.import_alias_tgt is None:
            return super()._module_target(module)
        return module.import_alias_tgt
