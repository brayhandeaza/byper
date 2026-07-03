import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from byper.__core__.project_env import run_project_pip
from helpers import run_byper


CURRENT = sys.version_info
CURRENT_MM = f"{CURRENT.major}.{CURRENT.minor}"
CURRENT_FULL = f"{CURRENT.major}.{CURRENT.minor}.{CURRENT.micro}"


class TestPythonVersion:
    def test_python_major_minor_creates_environment(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text(
            f'name: pytest\nversion: 0.0.1\npython: "{CURRENT_MM}"\n'
        )
        result = run_byper("install", cwd=tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr
        assert (tmp_path / "packages" / "bin" / "python").exists()

        lockfile = yaml.safe_load((tmp_path / "byper.lock").read_text())
        assert lockfile["python"]["required"] == CURRENT_MM
        assert lockfile["python"]["resolved"].startswith(CURRENT_MM)
        assert lockfile["python"]["implementation"] == "CPython"

    def test_python_exact_requires_exact(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text(
            f'name: pytest\nversion: 0.0.1\npython: "{CURRENT_FULL}"\n'
        )
        result = run_byper("install", cwd=tmp_path)
        assert result.returncode == 0, result.stdout + result.stderr

        lockfile = yaml.safe_load((tmp_path / "byper.lock").read_text())
        assert lockfile["python"]["required"] == CURRENT_FULL
        assert lockfile["python"]["resolved"] == CURRENT_FULL

    def test_existing_incompatible_environment_fails(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text("name: pytest\nversion: 0.0.1\n")
        run_byper("install", cwd=tmp_path)
        assert (tmp_path / "packages" / "bin" / "python").exists()

        (tmp_path / "requirements.yaml").write_text(
            'name: pytest\nversion: 0.0.1\npython: "99.99"\n'
        )
        result = run_byper("install", cwd=tmp_path, check=False)
        combined = result.stdout + result.stderr
        assert result.returncode != 0
        assert "99.99" in combined

    def test_doctor_reports_python_requirement_and_project_python(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text(
            f'name: pytest\nversion: 0.0.1\npython: "{CURRENT_MM}"\n'
        )
        run_byper("install", cwd=tmp_path)
        result = run_byper("doctor", cwd=tmp_path)
        assert result.returncode == 0
        assert f"Python requirement: {CURRENT_MM}" in result.stdout
        assert "Project Python:" in result.stdout
        assert "Status: OK" in result.stdout

    def test_no_python_field_uses_current_python(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text("name: pytest\nversion: 0.0.1\n")
        result = run_byper("install", cwd=tmp_path)
        assert result.returncode == 0
        assert (tmp_path / "packages" / "bin" / "python").exists()

        lockfile = yaml.safe_load((tmp_path / "byper.lock").read_text())
        assert "python" not in lockfile

    def test_lockfile_created_next_to_requirements(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text("name: pytest\nversion: 0.0.1\n")
        result = run_byper("install", cwd=tmp_path)
        assert result.returncode == 0
        assert (tmp_path / "byper.lock").exists()
        assert not (tmp_path / "packages" / "byper.lock").exists()

    def test_lockfile_uses_packages_key(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text(
            f'name: pytest\nversion: 0.0.1\npython: "{CURRENT_MM}"\n'
        )
        run_byper("install", cwd=tmp_path)
        lockfile = yaml.safe_load((tmp_path / "byper.lock").read_text())
        assert "packages" in lockfile
        assert "package" not in lockfile

    def test_lockfile_no_legacy_names(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text("name: pytest\nversion: 0.0.1\n")
        run_byper("install", cwd=tmp_path)
        assert (tmp_path / "byper.lock").exists()
        assert not (tmp_path / "Lockfile").exists()
        assert not (tmp_path / "viper.lock").exists()
        assert not (tmp_path / "requirements.lock").exists()

    def test_lockfile_install_from_lockfile(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text(
            "name: pytest\nversion: 0.0.1\n"
            "dependencies:\n"
            "  colorama: \"0.4.6\"\n"
        )
        run_byper("install", cwd=tmp_path)
        lockfile = yaml.safe_load((tmp_path / "byper.lock").read_text())
        packages = lockfile["packages"]
        colorama_key = [k for k in packages if "colorama" in k][0]
        assert packages[colorama_key]["version"] == "0.4.6"

        # Remove the package and reinstall from lockfile
        result = run_project_pip(["uninstall", "-y", "colorama"], project_root=tmp_path)
        assert result.returncode == 0

        result = run_byper("install", cwd=tmp_path)
        assert result.returncode == 0
        assert "Installing from lockfile" in result.stdout
        show = run_project_pip(["show", "colorama"], project_root=tmp_path, stdout=subprocess.PIPE, text=True)
        assert "Name: colorama" in show.stdout
