import os
import sys
from pathlib import Path

import pytest

from byper.__core__.project_env import (
    build_project_env,
    find_project_root,
    get_packages_dir,
    get_project_bin_dir,
    get_project_python,
    get_project_site_packages,
)


def test_find_project_root_from_subdirectory(tmp_path: Path):
    (tmp_path / "requirements.yaml").write_text("name: project\n")
    nested = tmp_path / "src" / "nested"
    nested.mkdir(parents=True)

    os.chdir(nested)
    root = find_project_root()
    assert root == tmp_path


def test_find_project_root_falls_back_to_cwd(tmp_path: Path):
    os.chdir(tmp_path)
    root = find_project_root()
    assert root == tmp_path


def test_get_project_python_unix(tmp_path: Path):
    if sys.platform == "win32":
        pytest.skip("Unix-only test")
    python = get_project_python(tmp_path)
    assert python == tmp_path / "packages" / "bin" / "python"


def test_get_project_bin_dir_unix(tmp_path: Path):
    if sys.platform == "win32":
        pytest.skip("Unix-only test")
    bin_dir = get_project_bin_dir(tmp_path)
    assert bin_dir == tmp_path / "packages" / "bin"


def test_build_project_env_prepends_bin_dir(tmp_path: Path):
    env = build_project_env(tmp_path)
    bin_dir = str(get_project_bin_dir(tmp_path))
    assert env["VIRTUAL_ENV"] == str(get_packages_dir(tmp_path))
    assert env["PATH"].startswith(bin_dir)
    assert os.pathsep in env["PATH"]


def test_get_project_site_packages_returns_path(tmp_path: Path):
    site_packages = get_project_site_packages(tmp_path)
    assert "site-packages" in str(site_packages)
