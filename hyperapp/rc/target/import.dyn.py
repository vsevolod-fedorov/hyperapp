from .code.import_job import ImportJob


class ImportTarget:

    def __init__(self, path):
        self._path = path

    @property
    def job(self):
        return ImportJob(self._path)
