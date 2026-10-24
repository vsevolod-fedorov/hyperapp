from .code.target.import_target import ProjectImportsTarget


class ProjectTarget:

    @classmethod
    def ensure(cls, targets, project_name):
        name = f'project/{project_name}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, project_name)
        targets[name] = tgt
        return tgt

    def __init__(self, targets, name, project_name):
        self._targets = targets
        self._name = name
        self._project_name = project_name
        # Resource targets are added by first imports of their modules.
        self._project_imports_tgt = ProjectImportsTarget.ensure(targets, project_name)
        self._path_to_resource_tgt = {}

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._targets.deps_state(self.deps)

    @property
    def deps(self):
        return {self._project_imports_tgt, *self._path_to_resource_tgt.values()}

    def add_resource_tgt(self, path, tgt):
        self._path_to_resource_tgt[path] = tgt

    @property
    def error(self):
        return None

    @property
    def result(self):
        return None

    @property
    def resources(self):
        return {
            path: tgt.result
            for path, tgt
            in self._path_to_resource_tgt.items()
            }
