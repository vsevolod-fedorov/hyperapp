import os.path
import simpleyaml as yaml
from ..common.interface.code_repository import (
    tModule,
    code_repository_iface,
    code_repository_browser_iface,
    )
from . import module as module_mod
from .module import ModuleCommand
from .object import Object, SmallListObject


MODULE_NAME = 'code_repository'
DYNAMIC_MODULES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../dynamic_modules'))
DYNAMIC_MODULE_INFO_EXT = '.module.yaml'
CODE_REPOSITORY_CLASS_NAME = 'code_repository'
CODE_REPOSITORY_FACETS = [code_repository_iface, code_repository_browser_iface]


class ModuleRepository(object):

    def __init__( self ):
        self._id2module = {}           # module id -> tModule
        self._requirement2module = {}  # (registry, key) -> tModule
        self._load_dynamic_modules()

    def get_module_list( self ):
        return sorted(self._id2module.values(), key=lambda module: module.id)

    def get_module_by_id( self, id ):
        return self._id2module[id]

    def get_module_by_requirement( self, registry, key ):
        return self._requirement2module.get((registry, key))

    def _load_dynamic_modules( self ):
        for fname in os.listdir(DYNAMIC_MODULES_DIR):
            if fname.endswith(DYNAMIC_MODULE_INFO_EXT):
                self._load_dynamic_module(os.path.join(DYNAMIC_MODULES_DIR, fname))

    def _load_dynamic_module( self, info_path ):
        with open(info_path) as f:
            info = yaml.load(f.read())
        print 'loaded module info:', info
        source_path = os.path.abspath(os.path.join(DYNAMIC_MODULES_DIR, info['source_path']))
        satisfies = [path.split('/') for path in info['satisfies']]
        module = self._load_module(info['id'], info['package'], satisfies, source_path)
        for registry, key in satisfies:
            self._id2module[module.id] = module
            self._requirement2module[(registry, key)] = module

    def _load_module( self, id, package, satisfies, fpath ):
        fpath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', fpath))
        with open(fpath) as f:
            source = f.read()
        return tModule(id=id, package=package, deps=[], satisfies=satisfies, source=source, fpath=fpath)


class CodeRepository(Object):

    iface = code_repository_iface
    facets = CODE_REPOSITORY_FACETS
    class_name = CODE_REPOSITORY_CLASS_NAME

    @classmethod
    def get_path( cls ):
        return module.make_path(cls.class_name)

    def __init__( self, repository ):
        Object.__init__(self)
        self._repository = repository

    def resolve( self, path ):
        path.check_empty()
        return self

    def process_request( self, request ):
        if request.command_id == 'get_modules_by_ids':
            return self.run_command_get_modules_by_ids(request)
        if request.command_id == 'get_modules_by_requirements':
            return self.run_command_get_modules_by_requirements(request)
        return Object.process_request(self, request)

    def run_command_get_modules_by_ids( self, request ):
        print 'run_command_get_modules_by_ids', request.params.module_ids
        return request.make_response_result(
            modules=self.get_modules_by_ids(request.params.module_ids))

    def run_command_get_modules_by_requirements( self, request ):
        print 'run_command_get_modules_by_requirements', request.params.requirements
        return request.make_response_result(
            modules=self.get_modules_by_requirements(request.params.requirements))

    def get_modules_by_ids( self, module_ids ):
        return [self._repository.get_module_by_id(id) for id in module_ids]

    def get_modules_by_requirements( self, requirements ):
        modules = []
        for registry, key in requirements:
            module = self._repository.get_module_by_requirement(registry, key)
            if module:
                modules.append(module)
            else:
                print 'Unknown requirement: %s/%s' % (registry, key)  # May be statically loaded, ignore
        return modules


class CodeRepositoryBrowser(SmallListObject):

    iface = code_repository_browser_iface
    facets = CODE_REPOSITORY_FACETS
    class_name = CODE_REPOSITORY_CLASS_NAME
    objimpl_id = 'list'
    default_sort_column_id = 'id'

    @classmethod
    def get_path( cls ):
        return module.make_path(cls.class_name)

    def __init__( self, repository ):
        SmallListObject.__init__(self)
        self._repository = repository

    def resolve( self, path ):
        path.check_empty()
        return self

    def fetch_all_elements( self ):
        return [self._module2element(module) for module in self._repository.get_module_list()]

    def _module2element( self, module ):
        return self.Element(self.Row(
            module.id,
            os.path.basename(module.fpath),
            module.package,
            ', '.join('.'.join(requirement) for requirement in module.satisfies),
            ))


class CodeRepositoryModule(module_mod.Module):

    def __init__( self ):
        module_mod.Module.__init__(self, MODULE_NAME)

    def resolve( self, iface, path ):
        objname = path.pop_str()
        if objname == CodeRepository.class_name and iface is CodeRepository.iface:
            return code_repository.resolve(path)
        if objname == CodeRepositoryBrowser.class_name and iface is CodeRepositoryBrowser.iface:
            return CodeRepositoryBrowser(module_repository).resolve(path)
        path.raise_not_found()

    def get_commands( self ):
        return [ModuleCommand('code_repository', 'Code repository', 'Browser code repository modules', 'Alt+R', self.name)]

    def run_command( self, request, command_id ):
        if command_id == 'code_repository':
            return request.make_response_handle(CodeRepositoryBrowser(module_repository))
        return Module.run_command(self, request, command_id)


module_repository = ModuleRepository()
code_repository = CodeRepository(module_repository)
module = CodeRepositoryModule()
