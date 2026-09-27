from pathlib import Path

from hyperapp.boot.boot import boot

TEST_DIR = Path(__file__).parent.resolve()
RESOURCES_ROOT = TEST_DIR / 'resources'
PROJECTS_PATH = TEST_DIR / 'projects.yaml'


def test_rc():
    workspace_path = Path(RESOURCES_ROOT / 'empty_module/workspace.yaml')
    boot(PROJECTS_PATH, 'rc_test:boot:boot.attr')(workspace_path)
