import shutil
import subprocess
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
HYPERAPP_DIR = TEST_DIR.parents[1]


def test_failed_build_exits_nonzero_after_writing_available_resources(tmp_path):
    workspace = shutil.copytree(TEST_DIR / 'resources' / 'classification_projects', tmp_path / 'workspace')
    result = subprocess.run([
        sys.executable, '-m', 'hyperapp.boot.boot', str(HYPERAPP_DIR / 'projects.yaml'), 'rc:boot:boot.attr',
        str(workspace / 'workspace.yaml'), '--workers', '1',
        ], cwd=HYPERAPP_DIR.parent, capture_output=True, text=True)
    assert result.returncode == 1, (result.stderr, result.stdout[-2000:])
    assert (workspace / 'library/subject.resources.yaml').read_bytes() == (
        workspace / 'library/subject.resources.expected.yaml').read_bytes()
