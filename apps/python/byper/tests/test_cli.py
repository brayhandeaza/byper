import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from byper.__core__.project_env import run_project_python
from helpers import run_byper


# ---------------------------------------------------------------------------
# Basic project lifecycle
# ---------------------------------------------------------------------------

def test_init_creates_project(empty_project: Path):
    result = run_byper("init", "-y", cwd=empty_project)
    assert result.returncode == 0
    assert (empty_project / "requirements.yaml").is_file()
    assert (empty_project / "main.py").is_file()
    assert (empty_project / "packages" / "bin" / "python").is_file()


def test_install_creates_packages(empty_project: Path):
    run_byper("init", "-y", cwd=empty_project)
    result = run_byper("install", cwd=empty_project)
    assert result.returncode == 0
    assert (empty_project / "packages" / "bin" / "python").is_file()


# ---------------------------------------------------------------------------
# Dependency management
# ---------------------------------------------------------------------------

@pytest.mark.network
class TestDependencyFlow:
    PACKAGE = "colorama"

    def test_add_updates_requirements_and_lockfile(self, initialized_project: Path):
        result = run_byper("add", self.PACKAGE, cwd=initialized_project)
        assert result.returncode == 0

        requirements = (initialized_project / "requirements.yaml").read_text()
        assert self.PACKAGE in requirements

        lockfile = (initialized_project / "byper.lock").read_text()
        assert f"{self.PACKAGE}:" in lockfile

    def test_add_installs_in_project_environment(self, initialized_project: Path):
        run_byper("add", self.PACKAGE, cwd=initialized_project)
        result = subprocess.run(
            [str(initialized_project / "packages" / "bin" / "python"), "-m", "pip", "show", self.PACKAGE],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert f"Name: {self.PACKAGE}" in result.stdout

    def test_remove_updates_requirements_and_lockfile(self, initialized_project: Path):
        run_byper("add", self.PACKAGE, cwd=initialized_project)
        result = run_byper("remove", self.PACKAGE, cwd=initialized_project)
        assert result.returncode == 0

        requirements = (initialized_project / "requirements.yaml").read_text()
        assert self.PACKAGE not in requirements

        lockfile = (initialized_project / "byper.lock").read_text()
        assert self.PACKAGE not in lockfile

    def test_install_uses_lockfile_when_synced(self, initialized_project: Path):
        run_byper("add", self.PACKAGE, cwd=initialized_project)
        result = run_byper("install", cwd=initialized_project)
        assert result.returncode == 0
        assert "Installing from lockfile" in result.stdout

    def test_add_respects_upgrade(self, initialized_project: Path):
        run_byper("add", f"{self.PACKAGE}==0.4.5", cwd=initialized_project)
        result = run_byper("add", self.PACKAGE, "--upgrade", cwd=initialized_project)
        assert result.returncode == 0
        version = (initialized_project / "requirements.yaml").read_text()
        assert "0.4.5" not in version or "0.4.6" in version


# ---------------------------------------------------------------------------
# Local environment execution
# ---------------------------------------------------------------------------

def _project_python(initialized_project: Path) -> str:
    return str(initialized_project / "packages" / "bin" / "python")


def test_list_uses_project_pip(initialized_project: Path):
    result = run_byper("list", cwd=initialized_project)
    assert result.returncode == 0
    assert "Package" in result.stdout


def test_run_script_uses_project_python(initialized_project: Path):
    (initialized_project / "requirements.yaml").write_text(
        "name: test\nversion: 0.0.1\nentry: main.py\nlicense: MIT\n\nscripts:\n  who: python -c \"import sys; print(sys.executable)\"\n"
    )
    result = run_byper("run", "who", cwd=initialized_project)
    assert result.returncode == 0
    assert _project_python(initialized_project) in result.stdout


def test_run_python_file_uses_project_python(initialized_project: Path):
    (initialized_project / "main.py").write_text("import sys\nprint(sys.executable)\n")
    result = run_byper("main.py", cwd=initialized_project)
    assert result.returncode == 0
    assert _project_python(initialized_project) in result.stdout


class TestTasks:
    @pytest.fixture
    def task_project(self, initialized_project: Path) -> Path:
        (initialized_project / "runner.py").write_text("import sys\nprint('runner:', sys.executable)\n")
        (initialized_project / "tasks.py").write_text(
            "def greet(name='world'):\n"
            "    import sys\n"
            "    print(f'Hello {name} from {sys.executable}')\n"
        )
        (initialized_project / "requirements.yaml").write_text(
            "name: tasktest\nversion: 0.0.1\nentry: main.py\nlicense: MIT\n\n"
            "tasks:\n"
            "  demo:\n"
            "    - { file: runner.py }\n"
            "    - { call: tasks.greet, kwargs: { name: Byper } }\n"
        )
        return initialized_project

    def test_task_file_uses_project_python(self, task_project: Path):
        result = run_byper("task", "demo", cwd=task_project)
        assert result.returncode == 0
        assert _project_python(task_project) in result.stdout

    def test_task_call_works(self, task_project: Path):
        result = run_byper("task", "demo", cwd=task_project)
        assert result.returncode == 0
        assert "Hello Byper from" in result.stdout


class TestEnv:
    def test_env_import(self, initialized_project: Path):
        (initialized_project / "requirements.yaml").write_text(
            "name: envtest\nversion: 0.0.1\nentry: main.py\nlicense: MIT\n\nenv:\n  DEBUG: \"true\"\n"
        )
        run_byper("install", cwd=initialized_project)
        result = run_project_python(
            ["-c", "from byper.env import DEBUG; print('DEBUG=', DEBUG)"],
            project_root=initialized_project,
            cwd=initialized_project,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert result.returncode == 0
        assert "DEBUG= true" in result.stdout


def test_aliases_no_longer_generates_module(initialized_project: Path):
    (initialized_project / "tasks.py").write_text(
        "def greet(name):\n"
        "    print(f'Hello {name}')\n"
    )
    (initialized_project / "requirements.yaml").write_text(
        "name: aliastest\nversion: 0.0.1\nentry: main.py\nlicense: MIT\n\naliases:\n  greeter: tasks.greet\n"
    )
    result = run_byper("refresh", cwd=initialized_project)
    assert result.returncode == 0

    try:
        import byper.aliases
        assert False, "byper.aliases should no longer exist"
    except ImportError:
        pass

    result = run_byper("install", cwd=initialized_project)
    assert result.returncode == 0


def test_refresh_does_not_generate_aliases(initialized_project: Path):
    (initialized_project / "requirements.yaml").write_text(
        "name: test\nversion: 0.0.1\nentry: main.py\nlicense: MIT\n\naliases:\n  foo: bar\n"
    )
    result = run_byper("refresh", cwd=initialized_project)
    assert result.returncode == 0
    assert "Aliases refreshed" not in result.stdout
    assert "Refreshing byper aliases" not in result.stdout


def test_aliases_warning_in_manifest(initialized_project: Path):
    (initialized_project / "requirements.yaml").write_text(
        "name: test\nversion: 0.0.1\nentry: main.py\nlicense: MIT\n\naliases:\n  utils: src.utils\n"
    )
    result = run_byper("install", cwd=initialized_project)
    assert "`aliases` is no longer supported" in result.stdout


# ---------------------------------------------------------------------------
# Lockfile
# ---------------------------------------------------------------------------

def test_lockfile_write_and_read(initialized_project: Path):
    run_byper("add", "colorama", cwd=initialized_project)
    lockfile = (initialized_project / "byper.lock").read_text()
    assert "packages:" in lockfile
    assert "colorama:" in lockfile


def test_lockfile_corrupt_shows_error(initialized_project: Path):
    (initialized_project / "byper.lock").write_text("not a mapping")
    result = run_byper("install", cwd=initialized_project, check=False)
    assert result.returncode != 0 or "corrupt" in result.stderr or "corrupt" in result.stdout


# ---------------------------------------------------------------------------
# Doctor
# ---------------------------------------------------------------------------

def test_doctor_uses_project_pip(initialized_project: Path):
    result = run_byper("doctor", cwd=initialized_project)
    assert result.returncode == 0
    assert _project_python(initialized_project) in result.stdout


# ---------------------------------------------------------------------------
# Build / Publish
# ---------------------------------------------------------------------------

@pytest.mark.network
class TestBuildPublish:
    def test_build_uses_project_python(self, initialized_project: Path):
        run_byper("add", "build", cwd=initialized_project)
        (initialized_project / "pyproject.toml").write_text(
            "[project]\nname = \"demo\"\nversion = \"0.0.0\"\n"
        )
        result = run_byper("build", cwd=initialized_project, check=False)
        assert _project_python(initialized_project) in (result.stdout + result.stderr)

    def test_publish_suggests_twine_not_path_python(self, initialized_project: Path):
        (initialized_project / "pyproject.toml").write_text(
            "[project]\nname = \"demo\"\nversion = \"0.0.0\"\n"
        )
        env = os.environ.copy()
        env["PATH"] = "/usr/bin:/bin"  # keep a minimal PATH so python itself still works
        result = run_byper("publish", cwd=initialized_project, check=False, env=env)
        combined = result.stdout + result.stderr
        assert "byper add twine" in combined
        assert "No such file or directory" not in combined


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

def test_cache_command_accessible(initialized_project: Path):
    result = run_byper("cache", "dir", cwd=initialized_project)
    assert result.returncode == 0
    assert "Caches" in result.stdout or "cache" in result.stdout.lower()


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

@pytest.mark.network
def test_add_nonexistent_package_fails(initialized_project: Path):
    result = run_byper("add", "this-package-does-not-exist-12345", cwd=initialized_project, check=False)
    assert result.returncode != 0 or "failed" in result.stdout.lower()


def test_invalid_requirements_yaml(initialized_project: Path):
    (initialized_project / "requirements.yaml").write_text("not: valid: yaml: [")
    result = run_byper("install", cwd=initialized_project, check=False)
    assert result.returncode != 0


def test_unknown_command(empty_project: Path):
    result = run_byper("not-a-command", cwd=empty_project, check=False)
    assert result.returncode != 0


# ---------------------------------------------------------------------------
# byper path / python / reset / doctor --fix
# ---------------------------------------------------------------------------

class TestPathAndPython:
    def test_path_shows_project_routes(self, initialized_project: Path):
        result = run_byper("path", cwd=initialized_project)
        assert result.returncode == 0
        assert "Project root:" in result.stdout
        assert "Packages:" in result.stdout
        assert "Python:" in result.stdout
        assert "Lockfile:" in result.stdout

    def test_python_shows_info(self, initialized_project: Path):
        result = run_byper("python", cwd=initialized_project)
        assert result.returncode == 0
        assert "Status:" in result.stdout


class TestReset:
    def test_reset_with_yes_flag(self, initialized_project: Path):
        packages = initialized_project / "packages"
        assert packages.is_dir()
        result = run_byper("reset", "-y", cwd=initialized_project)
        assert result.returncode == 0
        assert packages.is_dir()

    def test_reset_cancels_on_no(self, initialized_project: Path):
        packages = initialized_project / "packages"
        assert packages.is_dir()
        # Simulate typing "no"
        result = run_byper("reset", cwd=initialized_project, check=False, input="n\n")
        assert packages.is_dir()

    def test_reset_recreates_packages(self, initialized_project: Path):
        packages = initialized_project / "packages"
        (packages / "bin" / "python").unlink(missing_ok=True)
        (packages / "bin" / "pip").unlink(missing_ok=True)
        result = run_byper("reset", "-y", cwd=initialized_project)
        assert result.returncode == 0
        assert (packages / "bin" / "python").exists()

    def test_reset_installs_from_lockfile(self, initialized_project: Path):
        result = run_byper("reset", "-y", cwd=initialized_project)
        assert result.returncode == 0

    def test_reset_updates_lockfile(self, initialized_project: Path):
        lock = initialized_project / "byper.lock"
        if lock.exists():
            lock.unlink()
        result = run_byper("reset", "-y", cwd=initialized_project)
        assert result.returncode == 0
        assert lock.exists()


class TestDoctorFix:
    def test_doctor_fix_no_issues(self, initialized_project: Path):
        result = run_byper("doctor", "--fix", "-y", cwd=initialized_project)
        assert result.returncode == 0

    def test_doctor_fix_creates_packages(self, initialized_project: Path):
        packages = initialized_project / "packages"
        shutil.rmtree(packages, ignore_errors=True)
        assert not packages.exists()
        result = run_byper("doctor", "--fix", "-y", cwd=initialized_project)
        assert result.returncode == 0
        assert packages.exists()

    def test_doctor_fix_regenerates_lockfile(self, initialized_project: Path):
        lock = initialized_project / "byper.lock"
        lock.unlink(missing_ok=True)
        result = run_byper("doctor", "--fix", "-y", cwd=initialized_project)
        assert result.returncode == 0
        assert lock.exists()


class TestErrorMessage:
    def test_incompatible_version_suggests_reset(self, tmp_path: Path):
        (tmp_path / "requirements.yaml").write_text("name: test\nversion: 0.0.1\n")
        run_byper("install", cwd=tmp_path)
        (tmp_path / "requirements.yaml").write_text(
            'name: test\nversion: 0.0.1\npython: "99.99"\n'
        )
        result = run_byper("install", cwd=tmp_path, check=False)
        combined = result.stdout + result.stderr
        assert "byper reset" in combined

