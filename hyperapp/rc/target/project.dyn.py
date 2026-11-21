class _AggregateTarget:

    error = None
    result = None

    def __init__(self, targets):
        self._targets = targets

    def __repr__(self):
        return f"<Target:{self.name}>"

    @property
    def state(self):
        return self._targets.deps_state(self.deps)


class AllTarget(_AggregateTarget):

    name = 'all'

    @property
    def deps(self):
        return self._targets.project_tgts


class ProjectTarget(_AggregateTarget):

    def __init__(self, targets, project_name):
        super().__init__(targets)
        self.name = f'project/{project_name}'
        self.deps = set()
        self._path_to_resource_tgt = {}

    def add_resource_tgt(self, path, tgt):
        self._path_to_resource_tgt[path] = tgt

    @property
    def resources(self):
        return {
            path: tgt.result
            for path, tgt
            in self._path_to_resource_tgt.items()
            }
