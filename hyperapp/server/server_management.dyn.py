# server management module: used to expose commands from all modules in one list

import logging
#from ..common.interface import server_management as server_management_types
from ..common.interface import hyper_ref as href_types
from ..common.interface import ref_list as ref_list_types
from ..common.url import Url
from ..common.local_server_paths import (
    LOCAL_SERVER_DYNAMIC_REF_LIST_REF_PATH,
    save_bundle_to_file,
    )
from .object import Object, SmallListObject
from .module import ServerModule
from .command import command

log = logging.getLogger(__name__)


MODULE_NAME = 'management'
DYNAMIC_REF_LIST_SERVICE_ID = 'dynamic_ref_list'
SERVER_MANAGEMENT_REF_LIST_ID = 'server_management'


## class CommandList(SmallListObject):

##     iface = server_management_types.server_management
##     impl_id = 'proxy_list'

##     @classmethod
##     def get_path(cls):
##         return this_module.make_path()

##     def __init__(self, module_registry):
##         SmallListObject.__init__(self, core_types)
##         self._module_registry = module_registry

##     def fetch_all_elements(self, request):
##         return list(map(self.cmd2element, self._module_registry.get_all_modules_commands()))

##     def cmd2element(self, cmd):
##         commands = [self.command_open]
##         id = '%s.%s' % (cmd.module_name, cmd.id)
##         return self.Element(self.Row(id, cmd.module_name, cmd.text, cmd.desc), commands)

##     @command('open', kind='element')
##     def command_open(self, request):
##         module_name, command_id = request.params.element_key.split('.')
##         module = self._module_registry.get_module_by_name(module_name)
##         return module.run_command(request, command_id)


class DynamicRefListService(object):

    def __init__(self):
        self._id2ref_list = {}

    def register_ref_list(self, id, ref_list):
        self._id2ref_list[id] = ref_list
    
    def rpc_get_ref_list(self, request, ref_list_id):
        dynamic_ref_list = self._id2ref_list[ref_list_id]
        ref_list = dynamic_ref_list.get_ref_list()
        return request.make_response_result(ref_list=ref_list_types.ref_list(ref_list=ref_list))


class ManagementRefList(object):

    def __init__(self):
        self._ref_list = []

    def add_ref(self, id, ref):
        self._ref_list.append(ref_list_types.ref_item(id, ref))

    def get_ref_list(self):
        return self._ref_list


class ThisModule(ServerModule):

    def __init__(self, services):
        super().__init__(MODULE_NAME)
        self._module_registry = services.module_registry
        self._dynamic_ref_list_service = DynamicRefListService()
        services.management_ref_list = management_ref_list = ManagementRefList()
        self._dynamic_ref_list_service.register_ref_list(SERVER_MANAGEMENT_REF_LIST_ID, management_ref_list)
        self._init_dynamic_ref_list_service(services)

    def _init_dynamic_ref_list_service(self, services):
        service = href_types.service(DYNAMIC_REF_LIST_SERVICE_ID, ['ref_list', 'ref_list_service'])
        service_ref = services.ref_registry.register_object(href_types.service, service)
        services.service_registry.register(service_ref, self._resolve_dynamic_ref_list_service)

        dynamic_ref_list = ref_list_types.dynamic_ref_list(
            ref_list_service=service_ref,
            ref_list_id=SERVER_MANAGEMENT_REF_LIST_ID,
            )
        dynamic_ref_list_ref = services.ref_registry.register_object(ref_list_types.dynamic_ref_list, dynamic_ref_list)

        ref_collector = services.ref_collector_factory()
        bundle = ref_collector.make_bundle([dynamic_ref_list_ref])
        ref_path = LOCAL_SERVER_DYNAMIC_REF_LIST_REF_PATH
        save_bundle_to_file(bundle, ref_path)
        log.info('Server management ref list ref is saved to: %s', ref_path)

    def _resolve_dynamic_ref_list_service(self):
        return self._dynamic_ref_list_service
