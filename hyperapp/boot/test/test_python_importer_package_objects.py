from hyperapp.boot.python_importer import PythonImporter


def test_single():
    imports = {
        'a.b.c.d': 123,
        }
    name_to_objects = PythonImporter._make_package_objects(imports)
    assert dict(name_to_objects) == {
        'a.b.c': {'d': 123},
        'a.b': {'c': {'d': 123}},
        'a': {'b': {'c': {'d': 123}}},
        }


def test_three():
    imports = {
        'a.b.c.a': 11,
        'a.b.c.b': 22,
        'a.b.c.c': 33,
        }
    name_to_objects = PythonImporter._make_package_objects(imports)
    assert dict(name_to_objects) == {
        'a.b.c': {'a': 11, 'b': 22, 'c': 33},
        'a.b': {'c': {'a': 11, 'b': 22, 'c': 33}},
        'a': {'b': {'c': {'a': 11, 'b': 22, 'c': 33}}},
        }
