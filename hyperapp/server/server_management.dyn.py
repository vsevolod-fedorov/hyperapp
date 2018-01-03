# server management module: used to expose commands from all modules in one list

import logging
from ..common.interface import core as core_types
from ..common.interface import server_management as server_management_types
from ..common.interface import hyper_ref as href_types
from ..common.interface import ref_list as ref_list_types
from ..common.url import Url
from ..common.local_server_paths import LOCAL_SERVER_REF_LIST_URL_PATH, save_url_to_file
from .object import Object, SmallListObject
from .module import Module
from .command import command

log = logging.getLogger(__name__)


MODULE_NAME = 'management'
REF_LIST_RESOLVER_SERVICE_CLASS_NAME = 'ref_list_resolver'


class CommandList(SmallListObject):

    iface = server_management_types.server_management
    objimpl_id = 'proxy_list'

    @classmethod
    def get_path(cls):
        return this_module.make_path()

    def __init__(self, module_registry):
        SmallListObject.__init__(self, core_types)
        self._module_registry = module_registry

    def fetch_all_elements(self, request):
        return list(map(self.cmd2element, self._module_registry.get_all_modules_commands()))

    def cmd2element(self, cmd):
        commands = [self.command_open]
        id = '%s.%s' % (cmd.module_name, cmd.id)
        return self.Element(self.Row(id, cmd.module_name, cmd.text, cmd.desc), commands)

    @command('open', kind='element')
    def command_open(self, request):
        module_name, command_id = request.params.element_key.split('.')
        module = self._module_registry.get_module_by_name(module_name)
        return module.run_command(request, command_id)


class RefListResolverService(Object):

    iface = ref_list_types.ref_list_resolver
    class_name = REF_LIST_RESOLVER_SERVICE_CLASS_NAME

    @classmethod
    def get_path(cls):
        return this_module.make_path(cls.class_name)

    def __init__(self, module_registry):
        Object.__init__(self)
        self._module_registry = module_registry

    def resolve(self, path):
        path.check_empty()
        return self
    
    @command('get_ref_list')
    def command_get_ref_list(self, request):
        ref_list_id = request.params.ref_list_id
        ref_item_list = [ref_list_types.ref_item(id='%s.%s' % (command.module_name, command.id),
                                                 ref=command.id.encode())
                          for command in self._module_registry.get_all_modules_commands()]
        ref_item_list = [
            ref_list_types.ref_item('fs', b'test-fs-ref'),
            ref_list_types.ref_item('blog', b'test-blog-ref'),
            ] + ref_item_list
        return request.make_response_result(ref_list=ref_list_types.ref_list(ref_list=ref_item_list))

    
class ThisModule(Module):

    def __init__(self, services):
        Module.__init__(self, MODULE_NAME)
        self._module_registry = services.module_registry
        self._server = services.server
        self._tcp_server = services.tcp_server
        self._management_service = RefListResolverService(services.module_registry)

    def resolve(self, iface, path):
        class_name = path.pop_str_opt()
        if class_name and class_name == RefListResolverService.class_name:
            return self._management_service.resolve(path)
        path.check_empty()
        return CommandList(self._module_registry)

    def init_phase2(self):
        public_key = self._server.get_public_key()
        url = Url(RefListResolverService.iface, public_key, RefListResolverService.get_path())
        url_with_routes = url.clone_with_routes(self._tcp_server.get_routes())
        url_path = save_url_to_file(url_with_routes, LOCAL_SERVER_REF_LIST_URL_PATH)
        log.info('Management service url is saved to: %s', url_path)


def get_management_url(public_key):
    return Url(CommandList.iface, public_key, CommandList.get_path())
