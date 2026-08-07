import importlib
import importlib.abc
import importlib.util
import logging
import sys
import traceback
from types import SimpleNamespace

from hyperapp.boot.htypes import HException

log = logging.getLogger(__name__)


ROOT_PACKAGE = 'hyperapp.dynamic'


class DynModuleImportError(Exception):

    def __init__(self, message, original_error, tb):
        super().__init__(message)
        self.original_error = original_error
        self.tb = tb


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

    def __init__(self, objects=None):
        self._objects = objects

    def create_module(self, spec):
        return None  # Use default semantics.

    # Make submodules automatically imported for use cases like:
    # > from . import htypes
    # > htypes.module.type
    def exec_module(self, module):
        if self._objects:
            module.__dict__.update(self._objects.__dict__)


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
        module.__dict__['__file__'] = self._file_path
        try:
            exec(ast, module.__dict__)
        except Exception as x:
            tb = traceback.format_tb(x.__traceback__)
            raise DynModuleImportError(str(x), x, tb[1:]) from x


class _ImportedObjectLoader:
    is_package = False

    def __init__(self, obj):
        self.obj = obj

    def create_module(self, spec):
        return self.obj

    def exec_module(self, module):
        pass


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

    def import_module(self, module_name, source, file_path, imports):
        module_full_name = f'{ROOT_PACKAGE}.{module_name}'
        package_objects = self._make_package_objects(imports)
        package_loaders = {
            f'{module_full_name}.{name}': _PackageLoader(objects)
            for name, objects in package_objects.items()
            }
        import_loaders = {
            f'{module_full_name}.{name}': _ImportedObjectLoader(obj)
            for name, obj in imports.items()
            }
        fullname_to_loader = {
            **package_loaders,
            **import_loaders,  # Should go after package loaders to override packages.
            ROOT_PACKAGE: _PackageLoader(),  # Should go after package loaders.
            module_full_name: _DynModuleLoader(source, file_path),  # Guess.
            }
        finder = _Finder(fullname_to_loader)
        sys.meta_path.append(finder)
        log.debug('Import python module: %s', module_name)
        try:
            try:
                return importlib.import_module(module_full_name)
            except:
                for full_name in list(sys.modules):
                    if full_name.startswith(module_full_name):
                        # Do not keep submodules if module import failed.
                        # Import recorder should be reloaded with new resources.
                        del sys.modules[full_name]
                raise
            finally:
                sys.meta_path.remove(finder)
        except HException:
            raise

    @staticmethod
    def _make_package_objects(imports):
        name_to_objects = {}
        for name, obj in imports.items():
            name_parts = name.split('.')
            for i in reversed(range(1, len(name_parts))):
                pkg_name = '.'.join(name_parts[:i])
                name = name_parts[i]
                name_to_objects.setdefault(pkg_name, SimpleNamespace())
                setattr(name_to_objects[pkg_name], name, obj)
                obj = name_to_objects[pkg_name]
        return name_to_objects
