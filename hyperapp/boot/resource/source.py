from functools import cached_property


class ResourceModuleSource:

    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    def __repr__(self):
        return f"<ResourceModuleSource: {self._name}>"

    def __eq__(self, rhs):
        return type(rhs) is ResourceModuleSource and rhs._name == self._name

    @cached_property
    def __hash__(self):
        return hash(('resource-module-source', self._name))
