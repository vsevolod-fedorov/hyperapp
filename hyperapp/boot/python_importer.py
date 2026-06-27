import importlib
import importlib.abc
import importlib.util
import logging
import sys

from hyperapp.boot.htypes import HException

log = logging.getLogger(__name__)


ROOT_PACKAGE = 'hyperapp.dynamic'


class PythonModuleImportError(Exception):

    def __init__(self, message, original_error, import_name):
        super().__init__(message)
        self.original_error = original_error
        self.import_name = import_name


def is_sub_path(sub_path, full_path):
    for x, y in zip(
        sub_path.split('.'),
        full_path.split('.'),
        ):
        if x != y:
            return False
    return True


class _PackageLoader:
    is_package = True

    def create_module(self, spec):
        return None  # Use default semantics.

    def exec_module(self, module):
        pass


class _DynModuleLoader:
    is_package = True

    def __init__(self, source, file_path):
        self._source = source
        self._file_path = file_path

    def create_module(self, spec):
        return None  # Use default semantics.

    def exec_module(self, module):
        log.debug('Executing code module: %s', self._file_path)
        # Using compile allows associate file path with loaded module.
        ast = compile(self._source, self._file_path, 'exec')
        # Assign special globals here:
        # module.__dict__['__module_source__'] = self._code_module.source
        # module.__dict__['__module_ref__'] = self._code_module_ref
        module.__dict__['__file__'] = self._file_path
        exec(ast, module.__dict__)


class _Finder(importlib.abc.MetaPathFinder):

    def __init__(self, fullname_to_loader):
        self._fullname_to_loader = fullname_to_loader

    def find_spec(self, fullname, path, target=None):
        log.debug('find_spec fullname=%r path=%r target=%r', fullname, path, target)
        loader = self._fullname_to_loader.get(fullname)
        if loader:
            return importlib.util.spec_from_loader(fullname, loader, is_package=loader.is_package)


class PythonImporter:

    def __init__(self):
        pass

    def import_module(self, module_name, source, file_path, import_loaders):
        fullname_to_loader = {
            **self._package_loaders(import_loaders),
            **import_loaders,
            ROOT_PACKAGE: _PackageLoader(),
            module_name: _DynModuleLoader(source, file_path),
            }
        finder = _Finder(fullname_to_loader)
        sys.meta_path.append(finder)
        log.debug('Import python module: %s', module_name)
        try:
            try:
                return importlib.import_module(module_name)
            except:
                for full_name in list(sys.modules):
                    if full_name.startswith(module_name):
                        # Do not keep submodules if module import failed.
                        # Import recorder should be reloaded with new resources.
                        del sys.modules[full_name]
                raise
            finally:
                sys.meta_path.remove(finder)
        except HException:
            raise
        except Exception as x:
            raise PythonModuleImportError(str(x), x, module_name) from x

    def _package_loaders(self, loaders):
        package_names = set()
        for fullname in loaders:
            name_parts = fullname.split('.')
            for i in range(1, len(name_parts)):
                package_names.add('.'.join(name_parts[:i]))
        return {
            fullname: _PackageLoader()
            for fullname in package_names
            }
