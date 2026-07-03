import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from byper.__core__.constants import LOCKFILE_NAME, get_lockfile_path
from byper.__core__.project_env import find_project_root
from ruamel.yaml import YAML

if TYPE_CHECKING:
    from byper.__core__.utils.logger import Logger

Logger = getattr(__import__("byper.__core__.utils.logger", fromlist=["Logger"]), "Logger")


class LockfileManager:
    @staticmethod
    def _resolve_project_root(project_root: Optional[Path | str] = None) -> Path:
        return Path(project_root or find_project_root()).resolve()

    @staticmethod
    def load_lockfile_data(project_root: Optional[Path | str] = None):
        """Load the full lockfile contents as a dictionary."""
        lockfile_path = get_lockfile_path(LockfileManager._resolve_project_root(project_root))
        if not lockfile_path.exists():
            return {}

        yaml = YAML()
        with open(lockfile_path, "r") as f:
            data = yaml.load(f) or {}

        if not isinstance(data, dict):
            raise ValueError(f"Lockfile {lockfile_path.name} is corrupt: root is not a mapping")

        return data

    @staticmethod
    def load_lockfile_manifest(project_root: Optional[Path | str] = None):
        data = LockfileManager.load_lockfile_data(project_root)

        packages = data.get("packages", {})
        if packages is None:
            packages = {}

        if not isinstance(packages, dict):
            raise ValueError(f"Lockfile {LOCKFILE_NAME} is corrupt: 'packages' is not a mapping")

        return dict(packages)

    @staticmethod
    def get_lockfile_python(project_root: Optional[Path | str] = None):
        """Return the python section from the lockfile, if present."""
        data = LockfileManager.load_lockfile_data(project_root)
        python = data.get("python")
        if isinstance(python, dict):
            return dict(python)
        return None

    @staticmethod
    def write_lockfile(package_name: str, version: str, project_root: Optional[Path | str] = None):
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        lockfile_path = get_lockfile_path(LockfileManager._resolve_project_root(project_root))
        if lockfile_path.exists():
            with open(lockfile_path, "r") as f:
                data = yaml.load(f) or {}
        else:
            data = {}

        if not isinstance(data, dict):
            data = {}

        data.setdefault("packages", {})[package_name] = version

        with open(lockfile_path, "w") as f:
            yaml.dump(data, f)

    @staticmethod
    def remove_from_lockfile(package_name: str, project_root: Optional[Path | str] = None):
        lockfile_path = get_lockfile_path(LockfileManager._resolve_project_root(project_root))
        if not lockfile_path.exists():
            return

        yaml = YAML()
        with open(lockfile_path, "r") as f:
            data = yaml.load(f) or {}

        if not isinstance(data, dict):
            return

        packages = data.get("packages", {})
        if not isinstance(packages, dict) or package_name not in packages:
            return

        del packages[package_name]

        if not packages:
            data = {}
        else:
            data["packages"] = packages

        with open(lockfile_path, "w") as f:
            yaml.dump(data, f)

    @staticmethod
    def sync_lockfile(
        dependencies: dict,
        python_info: dict | None = None,
        project_root: Optional[Path | str] = None,
    ):
        """Overwrite the lockfile with the current dependency map."""
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        lockfile_path = get_lockfile_path(LockfileManager._resolve_project_root(project_root))
        existing = LockfileManager.load_lockfile_data(project_root)

        data: dict = {"lock_version": 1, "packages": dict(dependencies)}
        if python_info is not None:
            data["python"] = python_info
        elif existing.get("python"):
            data["python"] = dict(existing["python"])

        with open(lockfile_path, "w") as f:
            yaml.dump(data, f)

    @staticmethod
    def install_from_lockfile(project_root: Optional[Path | str] = None):
        packages = LockfileManager.load_lockfile_manifest(project_root)

        if not packages:
            Logger.log(f"🔍 Lockfile {LOCKFILE_NAME} empty or not found.", level="warn")
            return

        from byper.__core__.installation import Installation

        for pkg, version in packages.items():
            if not version:
                Logger.log(f"❌ Lockfile entry for {pkg} has no version", level="error")
                continue
            try:
                Installation.install(f"{pkg}=={version}", update_manifest=False)
            except Exception as e:
                Logger.log(f"❌ Failed to install {pkg}=={version}: {e}", level="error")

        Logger.log(f"✅ Installed dependencies from {LOCKFILE_NAME}", level="success")
