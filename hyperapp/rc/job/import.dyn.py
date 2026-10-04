
class ImportJob:

    def __init__(self, path):
        self._path = path

    def __repr__(self):
        return f"<ImportJob: {self._path}>"
