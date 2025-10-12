import importlib
import subprocess
from typing import TYPE_CHECKING
import requests
from byper.__core__.helpers import is_vcs_url
from packaging.requirements import Requirement
from packaging.version import Version
from packaging.specifiers import SpecifierSet

if TYPE_CHECKING:
    from byper.__core__.manifest import Manifest
    from byper.__core__.environment import Environment
    from byper.__core__.utils.logger import Logger


Environment = getattr(importlib.import_module("byper.__core__.environment"), "Environment")
Manifest = getattr(importlib.import_module("byper.__core__.manifest"), "Manifest")
Logger = getattr(importlib.import_module("byper.__core__.utils.logger"), "Logger")


class Installation:
    @staticmethod
    def install(package: str, no_cache: bool = False, upgrade: bool = False, flags=None) -> str | None:
        try:
            Logger.log(f"\n📦 Installing {package}")
            Environment.ensure_dirs()
            name = package
            version = ""

            is_url = is_vcs_url(package)

            if not is_url:
                manifest: dict = Manifest.load_requirements_manifest()
                name, version = Installation.resolve_installable_version(package)
                is_installed = Installation.is_package_installed(name)


            # Install package using env Python
            version_to_install = f"=={version}" if version else ""

            args = list(
                filter(
                    None,
                    [
                        Environment.get_env_python(),
                        "-m",
                        "pip",
                        "install",
                        "--upgrade" if upgrade else None,
                        f"{name}{version_to_install if is_url else ''}",
                        "--disable-pip-version-check",
                        "--no-cache-dir" if no_cache else None,
                        flags if flags else None,
                    ],
                )
            )

            process = subprocess.Popen(
                args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
            )

            last_line = ""
            for line in process.stdout:
                last_line = line.strip()

                if "Successfully installed" in last_line:
                    Logger.log(f"✅ {line.strip()}", level="success", indent=1)

                else:
                    Logger.log(line.strip(), level="command", indent=1)

            if is_installed:
                Logger.log(
                    f"✅ {name}=={version} is already installed.",
                    level="install",
                    indent=1,
                )

            if process.stderr:
                for line in process.stderr:
                    Logger.log(f"❌ {line.strip()}", level="error", indent=1)

            process.wait()

            manifest.setdefault("dependencies", {})[name] = version
            Manifest.save_manifest(manifest)

            return name, version

        except Exception as e:
            print(f"❌ {e}")
            return None, None

    @staticmethod
    def reinstall_from_requirements(show_logdown: bool = False, no_cache: bool = False):
        try:
            Environment.ensure_dirs()
            manifest = Manifest.load_requirements_manifest()
            dependencies = dict(manifest.get("dependencies", {}))

            if not dependencies:
                return

            if show_logdown and len(dependencies) > 0:
                Logger.log(f"📦 Reinstalling dependencies", level="install")

            for m_package, version in dependencies.items():
                is_installed = Installation.is_package_installed(m_package)

                if not is_installed:
                    package_to_install = f"{m_package}=={version}"
                    Installation.install(package_to_install, no_cache)

                else:
                    if show_logdown:
                        Logger.log(
                            f"✅ {m_package} is already installed.",
                            level="command",
                            indent=1,
                        )

        except subprocess.CalledProcessError as e:
            Logger.log(f"❌ Failed to install dependencies: {e}", level="error")
            raise Exception

    @staticmethod
    def uninstall(package: str) -> str | None:
        try:
            Environment.ensure_dirs()
            name, _ = Installation.resolve_installable_version(package)

            Logger.log(f"\n📦 Uninstalling {package}", level="install")

            process = subprocess.Popen(
                [
                    Environment.get_env_python(),
                    "-m",
                    "pip",
                    "--disable-pip-version-check",
                    "uninstall",
                    "-y",
                    f"{name}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )

            last_line = ""
            for line in process.stdout:
                last_line = line.strip()

                if "Successfully uninstalled" in last_line:
                    Logger.log(f"❌ {line.strip()}", level="remove", indent=1)

                else:
                    Logger.log(line.strip(), level="command", indent=1)

            if process.stderr:
                for line in process.stderr:
                    Logger.log(f"❌ {line.strip()}", level="error", indent=1)

            process.wait()

            manifest = Manifest.load_requirements_manifest()
            dependencies: dict = dict(manifest.get("dependencies", {}))

            if name in dependencies:
                del dependencies[name]

                manifest["dependencies"] = dependencies
                Manifest.save_manifest(manifest)

        except subprocess.CalledProcessError as e:
            raise ValueError(e.stderr)

    @staticmethod
    def is_package_installed(package: str):
        try:
            env_python = Environment.get_env_python()
            subprocess.run(
                [env_python, "-m", "pip", "show", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True,
            )

            return True

        except subprocess.CalledProcessError as e:
            return False

    @staticmethod
    def resolve_installable_version(requirement_str: str):
        requirement = Requirement(requirement_str)
        try:
            name = requirement.name
            specifier: SpecifierSet = requirement.specifier

            url = f"https://pypi.org/pypi/{name}/json"
            resp = requests.get(url)
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
