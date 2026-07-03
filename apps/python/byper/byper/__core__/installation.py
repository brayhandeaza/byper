import json
import subprocess
from typing import TYPE_CHECKING

import requests
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from byper.__core__.helpers import is_vcs_url
from byper.__core__.lockfile import LockfileManager
from byper.__core__.project_env import (
    ensure_project_environment,
    get_project_python_lock_info,
    run_project_pip,
)

if TYPE_CHECKING:
    from byper.__core__.manifest import Manifest
    from byper.__core__.utils.logger import Logger

Manifest = getattr(__import__("byper.__core__.manifest", fromlist=["Manifest"]), "Manifest")
Logger = getattr(__import__("byper.__core__.utils.logger", fromlist=["Logger"]), "Logger")


class Installation:
    @staticmethod
    def install(
        package: str,
        download: bool = False,
        no_cache: bool = False,
        upgrade: bool = False,
        flags: str | None = None,
        update_manifest: bool = True,
    ) -> tuple[str | None, str | None]:
        try:
            Logger.log(f"\n📦 {'Downloading' if download else 'Installing'} {package}")
            ensure_project_environment()

            is_url = is_vcs_url(package)
            name = package
            version: str | None = None

            if not is_url:
                name, version = Installation.resolve_installable_version(package)
                if version is None and "==" not in package and ">=" not in package and "<=" not in package:
                    raise RuntimeError(f"Could not resolve a compatible version for '{package}'")

            version_spec = f"=={version}" if version and not is_url else ""

            pip_args = ["download" if download else "install"]
            if upgrade:
                pip_args.append("--upgrade")
            pip_args.append(f"{name}{version_spec}")
            if no_cache:
                pip_args.append("--no-cache-dir")
            if flags:
                pip_args.extend(flags.split())

            result = run_project_pip(
                pip_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            for line in result.stdout.splitlines():
                if "Successfully installed" in line or "Successfully downloaded" in line:
                    Logger.log(line.strip(), level="success", indent=1)
                else:
                    Logger.log(line.strip(), level="command", indent=1)

            if result.returncode != 0:
                raise RuntimeError(f"pip failed with exit code {result.returncode}")

            # Determine the actually installed version
            installed_version = Installation.get_installed_version(name) if not is_url else ""
            final_version = installed_version or version or ""

            if update_manifest:
                manifest = Manifest.load_requirements_manifest()
                manifest.setdefault("dependencies", {})[name] = final_version
                dependencies = dict(manifest.get("dependencies", {}))
                Manifest.save_manifest(manifest)
                LockfileManager.sync_lockfile(
                    dependencies,
                    python_info=get_project_python_lock_info(),
                )

            return name, final_version

        except Exception as e:
            Logger.log(f"❌ {package} {'download' if download else 'installation'} failed: {e}", level="error")
            return None, None

    @staticmethod
    def install_from_requirements(show_log: bool = False, no_cache: bool = False):
        ensure_project_environment()
        manifest = Manifest.load_requirements_manifest()
        dependencies = dict(manifest.get("dependencies", {}))

        if dependencies:
            if show_log:
                Logger.log("📦 Installing dependencies", level="install")

            for package_name, version in dependencies.items():
                if Installation.is_package_installed(package_name):
                    if show_log:
                        Logger.log(f"✅ {package_name} is already installed.", level="command", indent=1)
                    continue

                spec = f"{package_name}=={version}" if version else package_name
                Installation.install(spec, no_cache=no_cache, update_manifest=False)

        # Sync lockfile with current dependencies after install
        LockfileManager.sync_lockfile(dependencies, python_info=get_project_python_lock_info())

    @staticmethod
    def uninstall(package: str, flags: str | None = None):
        ensure_project_environment()

        # Normalize to the actual package name if possible
        name = Installation.resolve_installable_version(package)[0]
        if not name:
            name = package

        Logger.log(f"\n📦 Uninstalling {name}", level="install")

        remove_cache = bool(flags and "--rm-cache" in flags)

        result = run_project_pip(
            ["uninstall", "-y", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for line in result.stdout.splitlines():
            if "Successfully uninstalled" in line:
                Logger.log(line.strip(), level="remove", indent=1)
            else:
                Logger.log(line.strip(), level="command", indent=1)

        if result.returncode != 0:
            raise RuntimeError(f"Failed to uninstall {name}")

        if remove_cache:
            cache_result = run_project_pip(
                ["cache", "remove", name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            Logger.log(f"\n📦 Removing {name} from cache", level="success")
            Logger.log(cache_result.stdout.strip(), level="command", indent=1)

        manifest = Manifest.load_requirements_manifest()
        dependencies: dict = dict(manifest.get("dependencies", {}))

        if name in dependencies:
            del dependencies[name]
            manifest["dependencies"] = dependencies
            Manifest.save_manifest(manifest)

        LockfileManager.remove_from_lockfile(name)

    @staticmethod
    def is_package_installed(package: str) -> bool:
        result = run_project_pip(
            ["show", package],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return result.returncode == 0

    @staticmethod
    def get_installed_version(package: str) -> str | None:
        result = run_project_pip(
            ["show", package],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()

        return None

    @staticmethod
    def resolve_installable_version(requirement_str: str):
        requirement = Requirement(requirement_str)
        try:
            name = requirement.name
            specifier: SpecifierSet = requirement.specifier

            url = f"https://pypi.org/pypi/{name}/json"
            resp = requests.get(url, timeout=10)
            if resp.status_code != 200:
                return name, None

            all_versions = sorted(
                [
                    Version(v)
                    for v in resp.json()["releases"].keys()
                    if not Version(v).is_prerelease
                ],
                reverse=True,
            )

            compatible_versions = [str(v) for v in all_versions if v in specifier]
            if compatible_versions:
                return name, compatible_versions[0]
            else:
                return name, None

        except Exception:
            return requirement.name, None
