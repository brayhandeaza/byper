from pathlib import Path

import pytest

from helpers import run_byper


@pytest.fixture
def empty_project(tmp_path: Path) -> Path:
    """Return an empty directory to be used as a Byper project root."""
    return tmp_path


@pytest.fixture
def initialized_project(tmp_path: Path) -> Path:
    """Return a Byper project after running `byper init -y`."""
    run_byper("init", "-y", cwd=tmp_path)
    return tmp_path


@pytest.fixture
def run_byper_fixture():
    return run_byper
