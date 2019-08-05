import logging
import yaml
from ..common.util import flatten
from ..common.interface import packet as packet_types
from ..common.interface import core as core_types
from ..common.interface import code_repository as code_repository_types
from . import module as module_mod
from .module import ModuleCommand
from .command import command
from .object import Object, SmallListObject
from .resources_loader import ResourcesLoader

log = logging.getLogger(__name__)


MODULE_NAME = 'code_repository'
DYNAMIC_MODULE_INFO_EXT = '.module.yaml'
CODE_REPOSITORY_CLASS_NAME = 'code_repository'
CODE_REPOSITORY_FACETS = [code_repository_types.code_repository, code_repository_types.code_repository_browser]


class ClientModuleRepository(object):

    def __init__(self, dynamic_module_dir):
        self._dynamic_module_dir = dynamic_module_dir
        self._id2module = {}           # module id -> tModule
        self._requirement2module = {}  # (registry, key) -> tModule
        self._load_dynamic_modules()

    def get_module_list(self):
        return sorted(list(self._id2module.values()), key=lambda module: module.id)

    def get_module_by_id(self, module_id):
        return self._id2module[module_id]

    def get_module_by_requirement(self, registry, key):
        return self._requirement2module.get((registry, key))

    def _load_dynamic_modules(self):
        for fname in self._dynamic_module_dir.iterdir():
            if fname.suffix == DYNAMIC_MODULE_INFO_EXT:
                self._load_dynamic_module(self._dynamic_module_dir / fname)

    def _load_dynamic_module(self, info_path):
        with open(info_path) as f:
            info = yaml.safe_load(f.read())
        log.info('loaded client module info: %r', info)
        source_path = os.path.abspath(os.path.join(self._dynamic_module_dir, info['source_path']))
        satisfies = [path.split('/') for path in info['satisfies']]
        module = self._load_module(info['id'], info['package'], satisfies, source_path)
        for registry, key in satisfies:
            self._id2module[module.id] = module
            self._requirement2module[(registry, key)] = module

    def _load_module(self, id, package, satisfies, fpath):
        with open(fpath) as f:
            source = f.read()
        return packet_types.module(id=id, package=package, deps=[], satisfies=satisfies, source=source, fpath=fpath)


class ClientCodeRepository(Object):

    iface = code_repository_types.code_repository
    facets = CODE_REPOSITORY_FACETS
    class_name = CODE_REPOSITORY_CLASS_NAME

    @classmethod
    def get_path(cls):
        return this_module.make_path(cls.class_name)

    def __init__(self, type_module_repository, code_module_repository, resources_loader):
        Object.__init__(self)
        self._code_module_repository = code_module_repository
        self._resources_loader = resources_loader
        self._type_module_repository = type_module_repository

    def resolve(self, path):
        path.check_empty()
        return self

    def get_modules_by_ids(self, module_ids):
        type_modules = []
        code_modules = []
        for module_id in module_ids:
            if self._type_module_repository.has_type_module(module_id):
                type_modules += self._type_module_repository.get_type_module_by_id_with_deps(module_id)
            else:
                code_modules.append(self._code_module_repository.get_module_by_id(module_id))
        return (type_modules, code_modules)

    def get_modules_by_requirements(self, requirements):
        type_modules = []
        code_modules = []
        for registry, key in requirements:
            if registry == 'interface':
                module = self._type_module_repository.get_type_module_by_interface_id(key)
                if module:
                    type_modules.append(module)
                else:
                    log.info('Unknown type requirement: %s:%s', registry, key)  # May be statically loaded, ignore
            else:
                module = self._code_module_repository.get_module_by_requirement(registry, key)
                if module:
                    code_modules.append(module)
                else:
                    log.info('Unknown code requirement: %s:%s', registry, key)  # May be statically loaded, ignore
        return (type_modules, code_modules)

    @command('get_modules_by_ids')
    def command_get_modules_by_ids(self, request, module_ids):
        log.info('command_get_modules_by_ids %r', module_ids)
        type_modules, code_modules = self.get_modules_by_ids(module_ids)
        return self._make_response(request, type_modules, code_modules)

    @command('get_modules_by_requirements')
    def command_get_modules_by_requirements(self, request, requirements):
        log.info('command_get_modules_by_requirements %r', requirements)
        type_modules, code_modules = self.get_modules_by_requirements(requirements)
        return self._make_response(request, type_modules, code_modules)

    def _make_response(self, request, type_modules, code_modules):
        resources = flatten(self._load_module_resources(module) for module in code_modules)
        return request.make_response_result(
            type_modules=type_modules,
            code_modules=code_modules,
            resources=resources)

    def _load_module_resources(self, module):
        resource_id = ['client_module', module.id]
        return self._resources_loader.get_resources(resource_id)


class ClientCodeRepositoryBrowser(SmallListObject):

    iface = code_repository_types.code_repository_browser
    facets = CODE_REPOSITORY_FACETS
    class_name = CODE_REPOSITORY_CLASS_NAME
    impl_id = 'proxy_list'
    default_sort_column_id = 'id'

    @classmethod
    def get_path(cls):
        return this_module.make_path(cls.class_name)

    def __init__(self, repository):
        SmallListObject.__init__(self, core_types)
        self._repository = repository

    def resolve(self, path):
        path.check_empty()
        return self

    def fetch_all_elements(self, request):
        return [self._module2element(module) for module in self._repository.get_module_list()]

    def _module2element(self, module):
        return self.Element(self.Row(
            module.id,
            os.path.basename(module.fpath),
            module.package,
            ', '.join('.'.join(requirement) for requirement in module.satisfies),
            ))


class ThisModule(module_mod.Module):

    def __init__(self, services):
        module_mod.Module.__init__(self, MODULE_NAME)
        self._module_repository = ClientModuleRepository(services.dynamic_module_dir)
        self._client_code_repository = ClientCodeRepository(services.type_module_repository, self._module_repository, services.resources_loader)
        services.module_repository = self._module_repository
        services.client_code_repository = self._client_code_repository

    def resolve(self, iface, path):
        objname = path.pop_str()
        if objname == ClientCodeRepository.class_name and iface is ClientCodeRepository.iface:
            return self._client_code_repository.resolve(path)
        if objname == ClientCodeRepositoryBrowser.class_name and iface is ClientCodeRepositoryBrowser.iface:
            return ClientCodeRepositoryBrowser(self._module_repository).resolve(path)
        path.raise_not_found()

    def get_commands(self):
        return [ModuleCommand('code_repository', 'Code repository', 'Browser code repository modules', 'Alt+R', self.name)]

    def run_command(self, request, command_id):
        if command_id == 'code_repository':
            return request.make_response_object(ClientCodeRepositoryBrowser(self._module_repository))
        return Module.run_command(self, request, command_id)
