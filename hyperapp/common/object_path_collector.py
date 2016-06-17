from .visitor import Visitor
from .htypes import (
    tObject,
    tProxyObject,
    )


class ObjectPathCollector(Visitor):

    def collect( self, t, value ):
        self.collected_paths = set()
        self.visit(t, value)
        return [list(path) for path in self.collected_paths]

    def visit_hierarchy_obj( self, t, tclass, value ):
        if t is tObject and isinstance(value, tProxyObject):
            self.collected_paths.add(tuple(value.path))
