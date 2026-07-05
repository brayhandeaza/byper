import shutil
import time
from pathlib import Path

import pytest
import yaml

from helpers import run_byper


# A set of small-to-medium packages that together bring in a sizeable
# transitive dependency graph.  The goal is to exercise resolution, lockfile
# generation and installation with many packages without relying on a single
# giant dependency.
MANY_DEPENDENCIES = [
    "certifi",
    "charset-normalizer",
    "click",
    "colorama",
    "idna",
    "importlib-metadata",
    "jinja2",
    "markupsafe",
    "packaging",
    "pathspec",
    "pyparsing",
    "pyyaml",
    "requests",
    "six",
    "tomli",
    "typing-extensions",
    "urllib3",
    "zipp",
]


def _write_many_dependencies(project_root: Path) -> None:
    requirements = project_root / "requirements.yaml"
    manifest = yaml.safe_load(requirements.read_text())
    manifest["dependencies"] = {pkg: "*" for pkg in MANY_DEPENDENCIES}
    requirements.write_text(yaml.dump(manifest, sort_keys=False))


@pytest.mark.performance
@pytest.mark.network
class TestPerformanceWithManyDependencies:
    def test_install_many_dependencies(self, initialized_project: Path, capsys):
        """Measure how long it takes to install a project with many dependencies."""
        _write_many_dependencies(initialized_project)

        start = time.perf_counter()
        result = run_byper("install", cwd=initialized_project)
        elapsed = time.perf_counter() - start

        assert result.returncode == 0, result.stderr
        assert (initialized_project / "byper.lock").exists()

        with capsys.disabled():
            print(
                f"\n[PERFORMANCE] byper install with {len(MANY_DEPENDENCIES)} "
                f"direct dependencies took {elapsed:.2f}s"
            )

    def test_reinstall_from_lockfile(self, initialized_project: Path, capsys):
        """Measure how long it takes to reinstall from an existing lockfile."""
        _write_many_dependencies(initialized_project)
        first = run_byper("install", cwd=initialized_project)
        assert first.returncode == 0, first.stderr
        assert (initialized_project / "byper.lock").exists()

        # Wipe the local environment but keep the lockfile.
        packages = initialized_project / "packages"
        if packages.exists():
            shutil.rmtree(packages)

        start = time.perf_counter()
        result = run_byper("install", cwd=initialized_project)
        elapsed = time.perf_counter() - start

        assert result.returncode == 0, result.stderr
        assert (packages / "bin" / "python").exists() or (packages / "Scripts" / "python.exe").exists()

        with capsys.disabled():
            print(
                f"\n[PERFORMANCE] byper install from lockfile took {elapsed:.2f}s"
            )

    def test_lockfile_is_created_quickly(self, initialized_project: Path, capsys):
        """Measure lockfile generation time on top of an existing environment."""
        _write_many_dependencies(initialized_project)
        install = run_byper("install", cwd=initialized_project)
        assert install.returncode == 0, install.stderr

        lockfile = initialized_project / "byper.lock"
        lockfile.unlink(missing_ok=True)
        assert not lockfile.exists()

        start = time.perf_counter()
        result = run_byper("install", cwd=initialized_project)
        elapsed = time.perf_counter() - start

        assert result.returncode == 0, result.stderr
        assert lockfile.exists()

        with capsys.disabled():
            print(
                f"\n[PERFORMANCE] lockfile regeneration took {elapsed:.2f}s"
            )
