from pathlib import Path

from hyperapp.boot.boot import boot

TEST_DIR = Path(__file__).parent.resolve()
RESOURCES_ROOT = TEST_DIR / 'resources'


def test_simple():
    result = boot(Path(RESOURCES_ROOT / 'simple/projects.yaml'), 'sample:main:main', [23])
    assert result == 123
