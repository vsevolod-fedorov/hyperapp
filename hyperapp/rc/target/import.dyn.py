from . import htypes


class ImportTarget:

    def __init__(self, path, source):
        self._path = path
        self._source = source

    @property
    def job(self):
        return htypes.import_job.import_job(
            path=self._path.piece,
            source=self._source,
            )
