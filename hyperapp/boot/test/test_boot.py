import re
import traceback
from pathlib import Path

from hyperapp.boot.resource.python_module import DynModuleResourceImportError
from hyperapp.boot.boot import boot

TEST_DIR = Path(__file__).parent.resolve()
RESOURCES_ROOT = TEST_DIR / 'resources'


def test_simple():
    result = boot(Path(RESOURCES_ROOT / 'simple/projects.yaml'), 'sample:main:main')([23])
    assert result == 2300


def test_imports():
    result = boot(Path(RESOURCES_ROOT / 'imports/projects.yaml'), 'sample:main:main')([23])
    assert result == 2300


def test_import_error():
    try:
        _ = boot(Path(RESOURCES_ROOT / 'import_error/projects.yaml'), 'sample:main:main')
    except DynModuleResourceImportError as x:
        assert isinstance(x.original_error, AssertionError)
        assert x.original_error.args == ('sample-error',)
        expected_tb = [
            'File ".+/hyperapp/boot/test/resources/import_error/main.dyn.py", line 4, in <module>',
            '  main()',
            'File ".+/hyperapp/boot/test/resources/import_error/main.dyn.py", line 2, in main',
            "  assert False, 'sample-error'",
            ]
        tb_lines = ''.join(x.tb).splitlines()
        for line, expected in zip(tb_lines, expected_tb):
            assert re.match('.*' + expected, line)


def test_run_error():
    try:
        _ = boot(Path(RESOURCES_ROOT / 'run_error/projects.yaml'), 'sample:main:main')(['a-param'])
    except AssertionError as x:
        assert isinstance(x, AssertionError)
        assert x.args == ('sample-error:a-param',)
        expected_tb = [
            'File ".+/hyperapp/boot/test/resources/run_error/main.dyn.py", line 2, in main',
            r'  fn\(args\[0\]\)',
            'File ".+/hyperapp/boot/test/resources/run_error/main.dyn.py", line 6, in fn',
            "  assert False, f'sample-error:{value}'",
            ]
        tb = traceback.format_tb(x.__traceback__)[3:]  # 1 entry from test_boot and 2 from boot module.
        tb_lines = ''.join(tb).splitlines()
        print(''.join(tb))
        for line, expected in zip(tb_lines, expected_tb):
            assert re.match('.*' + expected, line)
