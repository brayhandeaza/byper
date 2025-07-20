import importlib
import os
from pathlib import Path
import subprocess
from typing import TYPE_CHECKING
from byper.__core__.constants import LOCKFILE
from ruamel.yaml import YAML
import yaml


if TYPE_CHECKING:
    from byper.__core__.environment import Environment
    from byper.__core__.utils.logger import Logger
    from byper.__core__.commands import Commands

Environment = getattr(importlib.import_module("byper.__core__.environment"), "Environment")
Logger = getattr(importlib.import_module("byper.__core__.utils.logger"), "Logger")
Commands = getattr(importlib.import_module("byper.__core__.commands"), "Commands")


class Lockfile:
    @staticmethod
    def load_lockfile_manifest():
        if not os.path.exists(LOCKFILE):
            return {}

        yaml = YAML()
        with open(LOCKFILE, "r") as f:
            data = yaml.load(f) or {}

        packages = data.get("packages", {})
        return dict(packages)

    @staticmethod
    def write_lockfile(package: dict):
        lock_entry = {
            package["name"]: {
                "version": package["version"],
                "filename": package["filename"],
                "filetype": package["filetype"],
                "url": package["url"],
                "hash": package["hash"],
                "bin_files": package.get("bin_files", []),
                "dependencies": package.get("dependencies", []),
            }
        }

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        # Load existing lockfile data if it exists
        if Path(LOCKFILE).exists():
            with open(LOCKFILE, "r") as f:
                data = yaml.load(f) or {}

        else:
            data = {}

        data.setdefault("packages", {}).update(lock_entry)

        with open(LOCKFILE, "w") as f:
            yaml.dump(data, f)

    @staticmethod
    def remove_from_lockfile(package_name: str):
        lockfile_path = Path(LOCKFILE)
        if not lockfile_path.exists():
            Logger.log("🔍 Lockfile does not exist.", level="warn")
            return

        with open(lockfile_path, "r") as f:
            try:
                data = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                Logger.log(f"🗑️ Failed to parse lockfile: {e}", level="error")
                return

        packages = data.get("packages", {})
        if package_name not in packages:
            return

        package = packages.get(package_name, {})
        bin_files = package.get("bin_files", [])

        # Remove installed bin files
        for bin_file in bin_files:
            file_path = f"{Environment.get_install_dir()}/bin/{bin_file}"
            if os.path.exists(file_path):
                os.remove(file_path)

        del packages[package_name]

        # Clean up if no packages left
        if not packages:
            data = {}
        else:
            data["packages"] = packages

        with open(lockfile_path, "w") as f:
            yaml.safe_dump(data, f, sort_keys=False)

    @staticmethod
    def install_from_lockfile():

        if not os.path.exists(LOCKFILE):
            print(f"Lockfile {LOCKFILE} not found.")
            return
        with open(LOCKFILE, "r") as f:
            lock_data = yaml.safe_load(f)
        packages = lock_data.get("package", {})
        for pkg, info in packages.items():
            version = info.get("version")
            try:
                Commands.add_package(f"{pkg}=={version}")
            except subprocess.CalledProcessError:
                print(f"Failed to install {pkg}=={version}")
        print(f"Installed dependencies from {LOCKFILE}")
