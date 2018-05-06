from .htypes import (
    TList,
    tTypeDef,
    TypeRegistry,
    TypeResolver,
    )
from .packet_coders import packet_coders
from .type_module_parser import parse_type_module


TYPEDEF_MODULE_ENCODING = 'yaml'


tFileContents = TList(tTypeDef)

def load_typedefs_from_yaml_file(fpath):
    contents = fpath.read_bytes()
    return packet_coders.decode(TYPEDEF_MODULE_ENCODING, contents, tFileContents)

def resolve_typedefs(meta_type_registry, name_resolver, module_name, typedefs):
    assert isinstance(name_resolver, TypeResolver), repr(name_resolver)
    resolved_registry = TypeRegistry()
    resolver = TypeResolver([resolved_registry], next=name_resolver)
    for typedef in typedefs:
        full_name = [module_name, typedef.name]
        t = meta_type_registry.resolve(resolver, typedef.type, full_name)
        resolved_registry.register(typedef.name, t)
    return resolved_registry

def load_types_file(meta_type_registry, type_registry_registry, module_name, fpath):
    contents = fpath.read_text()
    used_modules, typedefs, loaded_types = parse_type_module(meta_type_registry, type_registry_registry, module_name, fpath, contents)
    return (used_modules, typedefs, loaded_types)
