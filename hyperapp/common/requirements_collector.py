from .visitor import Visitor
from .htypes import (
    tObject,
    tProxyObject,
    tHandle,
    tViewHandle,
    )


class RequirementsCollector(Visitor):

    def collect( self, t, value ):
        self.collected_requirements = set()
        self.visit(t, value)
        return list([registry, key] for registry, key in self.collected_requirements)

    def visit_hierarchy_obj( self, t, tclass, value ):
        if t is tObject:
            self.collected_requirements.add(('object', value.objimpl_id))
            if isinstance(value, tProxyObject):
                for iface in value.facets:
                    self.collected_requirements.add(('interface', iface))
        if t is tHandle and isinstance(value, tViewHandle):
            self.collected_requirements.add(('handle', value.view_id))
