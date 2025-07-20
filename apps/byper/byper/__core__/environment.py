import importlib
import os
from pathlib import Path
import subprocess
import sys
from typing import TYPE_CHECKING
from byper.__core__.constants import ENVIRONMENT_DIRECTORY

if TYPE_CHECKING:
    from byper.__core__.utils.logger import Logger

Logger = getattr(importlib.import_module("byper.__core__.utils.logger"), "Logger")


class Environment:
    @staticmethod
    def find_nested_venv():
        other_envs = []
        for root, dirs, files in os.walk(os.getcwd()):
            rel_root = os.path.relpath(root, os.getcwd())

            # Skip Packages/ itself
            if rel_root == "Packages" or rel_root.startswith("Packages" + os.sep):
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
        output = subprocess.Popen(
            ["pip", "list", "--outdated"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        output.wait()

        Logger.log("↪ Outdated packages:", indent=1, level="warn" if is_warn else "")
        packages = []
        for line in output.stdout:
            if line.startswith("Package") or line.startswith("----"):
                Logger.log(f"  {line.strip()}", indent=2, level="command")

            else:
                Logger.log(f"↪ {line.strip()}", indent=2, level="command")
                packages.append(line.strip().split(" ")[0])

        return packages

    @staticmethod
    def get_install_dir():
        return f"Packages/lib/python{Environment.get_python_version()}/site-packages"

    @staticmethod
    def get_env_python():
        return os.path.join(ENVIRONMENT_DIRECTORY, "bin", "python")

    @staticmethod
    def ensure_dirs(workspace: str = "./"):
        if not os.path.exists(workspace + ENVIRONMENT_DIRECTORY):
            subprocess.check_call(
                [sys.executable, "-m", "venv", workspace + ENVIRONMENT_DIRECTORY]
            )

    @staticmethod
    def get_library_root():
        return Path(__file__).resolve().parent.parent

    @staticmethod
    def get_cache_dir():
        cache_dir = Environment.get_library_root() / ".cache/packages"
        cache_dir.mkdir(parents=True, exist_ok=True)

        return cache_dir
