import logging
from .module import ServerModule

log = logging.getLogger(__name__)


MODULE_NAME = 'server_info'


class RouteResolver(object):

    def __init__(self):
        self._source_list = []

    def add_source(self, source):
        self._source_list.append(source)

    def resolve(self, service_ref):
        transport_ref_set = set()
        for source in self._source_list:
            transport_ref_set |= source.resolve(service_ref)
        return transport_ref_set


class ThisModule(ServerModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME)
        services.route_resolver = RouteResolver()
