from . import htypes


class ImportTarget:

    @classmethod
    def ensure(cls, targets, path, source):
        idx = 0
        name = f'import/{path.project}/{"/".join(path.path)}/{idx}'
        try:
            return targets[name]
        except KeyError:
            pass
        tgt = cls(targets, name, idx, path, source)
        targets[name] = tgt
        return tgt

    def __init__(self, targets, name, idx, path, source):
        self._targets = targets
        self._name = name
        self._idx = idx
        self._path = path
        self._source = source

    def __repr__(self):
        return f"<Target:{self._name}>"

    @property
    def name(self):
        return self._name

    @property
    def ready(self):
        return True

    @property
    def job(self):
        return htypes.import_job.import_job(
            target=self._name,
            path=self._path.piece,
            source=self._source,
            )
