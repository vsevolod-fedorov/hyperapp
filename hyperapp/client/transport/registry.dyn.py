import logging

from hyperapp.client.module import ClientModule

from .code_registry import CodeRegistry

log = logging.getLogger(__name__)


class ThisModule(ClientModule):

    def __init__(self, module_name, services, config):
        super().__init__(module_name, services)
        services.transport_registry = CodeRegistry('transport', services.async_web, services.types)
