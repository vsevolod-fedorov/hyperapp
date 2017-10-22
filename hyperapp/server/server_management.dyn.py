# server management module: used to expose commands from all modules in one list

from ..common.interface import core as core_types
from ..common.interface import server_management as server_management_types
from ..common.url import Url
from .object import SmallListObject
from .module import Module
from .command import command


MODULE_NAME = 'management'


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


class ThisModule(Module):

    def __init__(self, services):
        Module.__init__(self, MODULE_NAME)
        self._module_registry = services.module_registry

    def resolve(self, iface, path):
        path.check_empty()
        return CommandList(self._module_registry)


def get_management_url(public_key):
    return Url(CommandList.iface, public_key, CommandList.get_path())
