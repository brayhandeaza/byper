import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from byper.__core__.constants import ENVIRONMENT_DIRECTORY
from byper.__core__.project_env import (
    build_project_env,
    ensure_project_environment,
    find_project_root,
    get_packages_dir,
    get_project_bin_dir,
    get_project_python,
    get_project_site_packages,
    run_project_pip,
)

if TYPE_CHECKING:
    from byper.__core__.utils.logger import Logger

from byper.__core__.utils.logger import Logger


class Environment:
    @staticmethod
    def find_nested_venv():
        other_envs = []
        for root, dirs, files in os.walk(os.getcwd()):
            rel_root = os.path.relpath(root, os.getcwd())

            # Skip packages/ itself
            if rel_root == ENVIRONMENT_DIRECTORY or rel_root.startswith(
                ENVIRONMENT_DIRECTORY + os.sep
            ):
                continue

            is_env = (
                "pyvenv.cfg" in files
                or "site-packages" in dirs
                or "bin" in dirs
                or "Scripts" in dirs
            )

            if is_env:
                other_envs.append(rel_root)

        if other_envs:
            Logger.log(
                "↪ Found additional virtual environment-like folders:",
                indent=1,
                level="warn",
            )
            for path in other_envs:
                Logger.log(f"↪ {path}", indent=2, level="command")

        return other_envs

    @staticmethod
    def get_python_version():
        return f"{sys.version_info.major}.{sys.version_info.minor}"

    @staticmethod
    def outdated_packages(is_warn: bool = True):
        result = run_project_pip(
            ["list", "--outdated"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )

        Logger.log("↪ Outdated packages:", indent=1, level="warn" if is_warn else "")
        packages = []
        for line in result.stdout.splitlines():
            if line.startswith("Package") or line.startswith("----"):
                Logger.log(f"  {line.strip()}", indent=2, level="command")
            else:
                Logger.log(f"↪ {line.strip()}", indent=2, level="command")
                packages.append(line.strip().split(" ")[0])

        return packages

    @staticmethod
    def get_install_dir():
        return str(get_project_site_packages())

    @staticmethod
    def get_env_python():
        return str(get_project_python())

    @staticmethod
    def get_env_bin_dir():
        return str(get_project_bin_dir())

    @staticmethod
    def ensure_dirs(workspace: str = "./"):
        return ensure_project_environment(workspace)

    @staticmethod
    def get_library_root():
        return Path(__file__).resolve().parent.parent

    @staticmethod
    def get_cache_dir():
        cache_dir = Environment.get_library_root() / ".cache" / "packages"
        cache_dir.mkdir(parents=True, exist_ok=True)

        return cache_dir

    @staticmethod
    def get_project_root():
        return str(find_project_root())
