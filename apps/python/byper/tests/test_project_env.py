import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

from byper.__core__.project_env import (
    build_project_env,
    find_project_root,
    get_packages_dir,
    get_project_bin_dir,
    get_project_python,
    get_project_site_packages,
    get_required_python_raw,
    run_project_pip,
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


def test_build_project_env_disables_pip_version_check(tmp_path: Path):
    env = build_project_env(tmp_path)
    assert env["PIP_DISABLE_PIP_VERSION_CHECK"] == "1"


def test_run_project_pip_includes_disable_flag():
    with mock.patch("byper.__core__.project_env.run_project_python") as mock_run:
        run_project_pip(["install", "colorama"])
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert "--disable-pip-version-check" in args
        assert args[:3] == ["-m", "pip", "--disable-pip-version-check"]


def test_run_project_pip_env_keeps_caller_env(tmp_path: Path):
    with mock.patch("byper.__core__.project_env.run_project_python") as mock_run:
        run_project_pip(["list"], env={"CUSTOM_VAR": "1"})
        kwargs = mock_run.call_args[1]
        assert kwargs["env"] == {"CUSTOM_VAR": "1"}


def test_get_required_python_raw_no_manifest(tmp_path: Path):
    os.chdir(tmp_path)
    raw = get_required_python_raw()
    assert raw is None


def test_get_required_python_raw_with_version(tmp_path: Path):
    os.chdir(tmp_path)
    (tmp_path / "requirements.yaml").write_text(
        'name: test\nversion: 0.0.1\npython: "3.12"\n'
    )
    raw = get_required_python_raw()
    assert raw == "3.12"
