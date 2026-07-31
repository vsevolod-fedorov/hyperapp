from pathlib import Path

from hyperapp.boot.boot import boot

TEST_DIR = Path(__file__).parent.resolve()


def test_boot():
    result = boot(TEST_DIR / 'projects.yaml', 'test:boot:boot')([23])
    assert result == 123
