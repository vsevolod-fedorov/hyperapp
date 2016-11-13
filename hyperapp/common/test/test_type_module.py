import os.path
import unittest
from hyperapp.common.htypes import (
    tInt,
    tString,
    Field,
    TRecord,
    TList,
    TClass,
    tObject,
    tBaseObject,
    tTypeDef,
    t_named,
    make_meta_type_registry,
    builtin_type_registry,
    )
from hyperapp.common.visual_rep import pprint
from hyperapp.common.type_module import (
    resolve_typedefs_from_yaml_file,
    load_types_file,
    resolve_typedefs,
    )


class TypeModuleTest(unittest.TestCase):

    def setUp( self ):
        self.meta_type_registry = make_meta_type_registry()

    def make_fpath( self, module_name ):
        return os.path.join(os.path.dirname(__file__), module_name)

    def test_yaml_module( self ):
        type_registry = builtin_type_registry()
        fpath = self.make_fpath('test_module1.types.yaml')
        registry = resolve_typedefs_from_yaml_file(self.meta_type_registry, type_registry, fpath)

        self.assertTrue(registry.has_name('some_int'))
        self.assertEqual(tInt, registry.get_name('some_int'))

        self.assertTrue(registry.has_name('simple_class'))
        self.assertEqual(TClass(tObject, 'simple', TRecord([])), registry.get_name('simple_class'))

        self.assertTrue(registry.has_name('text_object'))
        self.assertEqual(TClass(tObject, 'text', TRecord(base=tBaseObject, fields=[Field('text', tString)])),
                         registry.get_name('text_object'))

    def test_types_module( self ):
        type_registry = builtin_type_registry()
        used_modules1, typedefs1, registry1 = load_types_file(self.meta_type_registry, type_registry, self.make_fpath('test_module1.types'))

        self.assertTrue(registry1.has_name('some_int'))
        self.assertEqual(tInt, registry1.get_name('some_int'))

        self.assertTrue(registry1.has_name('simple_class'))
        self.assertEqual(TClass(tObject, 'simple_2', TRecord([])), registry1.get_name('simple_class'))

        self.assertTrue(registry1.has_name('text_object'))
        self.assertEqual(TClass(tObject, 'text_2', TRecord(base=tBaseObject, fields=[Field('text', tString)])),
                         registry1.get_name('text_object'))

        self.assertEqual([], used_modules1)

        used_modules2, typedefs2, registry2 = load_types_file(self.meta_type_registry, type_registry, self.make_fpath('test_module2.types'))

