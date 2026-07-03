import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import webbrowser
from configparser import ConfigParser
from pathlib import Path
from typing import TYPE_CHECKING

from colorama import Fore, Style

from byper.__core__.constants import ENVIRONMENT_DIRECTORY, LOCKFILE_NAME, REQUIREMENTS_FILE, VERSION
from byper.__core__.constants import get_lockfile_path
from byper.__core__.lockfile import LockfileManager
from byper.__core__.project_env import (
    ensure_project_environment,
    find_project_root,
    get_packages_dir,
    get_project_python,
    get_project_python_version_info,
    get_required_python,
    run_in_project,
    run_project_pip,
    run_project_python,
    validate_project_environment,
)
from byper.__core__.python_version import describe_requirement, format_version, is_compatible

if TYPE_CHECKING:
    from byper.__core__.environment import Environment
    from byper.__core__.installation import Installation
    from byper.__core__.manifest import Manifest
    from byper.__core__.tasks import Tasks
    from byper.__core__.utils.logger import Logger

Environment = getattr(__import__("byper.__core__.environment", fromlist=["Environment"]), "Environment")
Installation = getattr(__import__("byper.__core__.installation", fromlist=["Installation"]), "Installation")
Manifest = getattr(__import__("byper.__core__.manifest", fromlist=["Manifest"]), "Manifest")
Tasks = getattr(__import__("byper.__core__.tasks", fromlist=["Tasks"]), "Tasks")
Logger = getattr(__import__("byper.__core__.utils.logger", fromlist=["Logger"]), "Logger")


def _has_module(module: str) -> bool:
    result = run_project_pip(
        ["show", module],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    return result.returncode == 0


def _safely_remove_packages_dir(packages: Path) -> None:
    """Remove packages/ with safety validation."""
    resolved = packages.resolve()
    project_root = find_project_root().resolve()

    if resolved.parent != project_root:
        Logger.log(f"❌ Safety check: {resolved} is not inside project root {project_root}", level="error")
        sys.exit(1)

    if resolved.name != ENVIRONMENT_DIRECTORY:
        Logger.log(f"❌ Safety check: expected directory name '{ENVIRONMENT_DIRECTORY}', got '{resolved.name}'", level="error")
        sys.exit(1)

    shutil.rmtree(resolved)
    Logger.log("✅ packages/ removed.", level="success")


class Commands:
    @staticmethod
    def doctor():
        Logger.log("🧠 Running environment diagnostics...")

        project_root = find_project_root()

        py_version = sys.version.split()[0]
        Logger.log(f"↪ Python version (CLI): {py_version}", indent=1)

        Logger.log(f"↪ Project root: {project_root}", indent=1)

        manifest = Manifest.load_requirements_manifest()
        raw_python = manifest.get("python")
        required = get_required_python()
        if raw_python is None:
            Logger.log("Python requirement: not set", indent=1)
        else:
            Logger.log(f"Python requirement: {raw_python}", indent=1)

        packages_exists = (project_root / ENVIRONMENT_DIRECTORY).is_dir()
        if packages_exists:
            Logger.log(f"↪ Local environment found at: {project_root / ENVIRONMENT_DIRECTORY}", indent=1)
        else:
            Logger.log("↪ packages/ environment folder does not exist", indent=1, level="warn")

        project_python = get_project_python(project_root)
        project_info = get_project_python_version_info(project_root)
        if project_info is None:
            Logger.log("Project Python: not found", indent=1)
            Logger.log(f"Python path: {project_python}", indent=1)
        else:
            installed_version, impl = project_info
            Logger.log(f"Project Python: {format_version(installed_version)}", indent=1)
            Logger.log(f"Implementation: {impl}", indent=1)
            Logger.log(f"Python path: {project_python}", indent=1)

            if required is None or is_compatible(installed_version, required):
                Logger.log("Status: OK", indent=1, level="success")
            else:
                Logger.log("Status: ERROR", indent=1, level="error")
                Logger.log(
                    f"The local environment was created with Python {format_version(installed_version)},\n"
                    f"but this project requires Python {describe_requirement(required)}.\n\n"
                    "Run:\n"
                    "  byper reset",
                    indent=1,
                    level="error",
                )
                sys.exit(1)

        try:
            socket.create_connection(("pypi.org", 443), timeout=3)
            Logger.log("↪ Internet connectivity: OK", indent=1)
        except Exception:
            Logger.log("↪ Internet connectivity: failed", indent=1, level="warn")

        is_git = (project_root / ".git").is_dir()
        Logger.log(f"↪ Git repository: {'found' if is_git else 'not found'}", indent=1)

        Environment.find_nested_venv()

        if packages_exists:
            Environment.outdated_packages()
            Manifest.load_installed_manifest()
            Commands._check_requirements_consistency(project_root)

        Logger.log(f"↪ Project Python executable: {project_python}", indent=1)

    @staticmethod
    def _check_requirements_consistency(project_root: Path):
        manifest = Manifest.load_requirements_manifest()
        expected = manifest.get("dependencies", {})
        if not expected:
            return

        result = run_project_pip(
            ["list", "--format=json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if result.returncode != 0:
            return

        installed = {
            pkg["name"].lower().replace("-", "_"): pkg["version"]
            for pkg in json.loads(result.stdout)
        }

        broken = []
        for name, version in expected.items():
            normalized = name.lower().replace("-", "_")
            actual = installed.get(normalized)
            if actual is None:
                broken.append((name, version, "not installed"))
            elif version and actual != version:
                broken.append((name, version, actual))

        if broken:
            Logger.log("↪ Mismatched packages:", indent=2, level="warn")
            for name, expected_version, actual in broken:
                Logger.log(f"- {name}: expected {expected_version}, got {actual}", indent=3, level="warn")

    @staticmethod
    def register_command():
        parser = argparse.ArgumentParser(add_help=False, prog="byper")
        subparsers = parser.add_subparsers(dest="command")

        def _parser_error(message):
            Logger.log(f"❌ {message}", level="error")
            Commands.print_help(exit_code=1)

        parser.error = _parser_error
        parser.add_argument("-h", "--help", action="store_true", help="Show help")
        parser.add_argument("--u-all", "--upgrade-all", action="store_true", help="Upgrade all packages to latest version")
        parser.add_argument("-v", "--version", help="Print byper version", action="store_true")

        subparsers.add_parser("install", help="Install dependencies")
        subparsers.add_parser("tree", help="Print directory tree")
        subparsers.add_parser("login", help="PyPI login")
        subparsers.add_parser("logout", help="PyPI logout")
        subparsers.add_parser("publish", help="Publish package to PyPI")
        subparsers.add_parser("refresh", help="Refresh environment packages")
        subparsers.add_parser("build", help="Build distribution packages")

        list_parser = subparsers.add_parser("list", help="List packages")
        for flag in ["--outdated", "--freeze", "--cache", "-c"]:
            list_parser.add_argument(flag, action="store_true", help="Specify output format or path")

        tasks_parser = subparsers.add_parser("task", help="Run task")
        tasks_parser.add_argument("name")

        init_parser = subparsers.add_parser("init", help="Initialize byper project")
        init_parser.add_argument("name", nargs="?", default=None)
        init_parser.add_argument("-y", action="store_true", help="Skip confirmation prompt")

        add_parser = subparsers.add_parser("add", help="Add package to dependencies")
        add_parser.add_argument("packages", nargs="+")
        add_parser.add_argument("flags", nargs=argparse.REMAINDER, help="Additional flags")
        add_parser.add_argument("--no-cache", action="store_true", help="Don't use cached packages")
        add_parser.add_argument("--upgrade", "-u", action="store_true", help="Upgrade packages to latest version")

        cache_parser = subparsers.add_parser("cache", help="Manage pip cache")
        cache_parser.add_argument("action", choices=["list", "clear", "dir"], help="Cache action")

        wheel_parser = subparsers.add_parser("wheel", help="Build wheel file for packages")
        wheel_parser.add_argument("packages", nargs="+")

        run_parser = subparsers.add_parser("run", help="Run script")
        run_parser.add_argument("script")

        remove_parser = subparsers.add_parser("remove", help="Remove package from dependencies")
        remove_parser.add_argument("packages", nargs="+")
        remove_parser.add_argument("flags", nargs=argparse.REMAINDER, help="Additional flags")

        subparsers.add_parser("path", help="Show project paths")
        subparsers.add_parser("python", help="Show project Python info")

        reset_parser = subparsers.add_parser("reset", help="Rebuild packages/")
        reset_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

        doctor_parser = subparsers.add_parser("doctor", help="Run dependencies diagnostics")
        doctor_parser.add_argument("--fix", action="store_true", help="Attempt to fix issues automatically")
        doctor_parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompts")

        return parser

    @staticmethod
    def upgrade_all():
        packages = Environment.outdated_packages(False)

        if not packages:
            Logger.log("✅ All packages are up to date.", level="success", indent=1)
            return

        Logger.log(f"↪ Upgrading {len(packages)} outdated package(s)", indent=1)

        for package in packages:
            Logger.log(f"\n🔄 Upgrading: {package}", indent=2)
            result = run_project_pip(
                ["install", "--upgrade", package],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in result.stdout.splitlines():
                Logger.log(line.strip(), level="command", indent=3)

            if result.returncode != 0:
                Logger.log(f"❌ Failed to upgrade {package}", level="error", indent=3)

        Logger.log("✅ Finished upgrading packages", level="success", indent=1)

    @staticmethod
    def print_help(exit_code: int = 0):
        Logger.log("List of Byper commands and options:", level="info")
        Logger.log("Commands:",                           level="info")

        Logger.log("byper init [name] [-y]                Initialize Byper project", indent=2, level="command")
        Logger.log("byper build                           Build distribution packages", indent=2, level="command")
        Logger.log("byper add <packages> [--no-cache]     Add package(s) to dependencies", indent=2, level="command")
        Logger.log("byper remove <packages>               Remove package(s) from dependencies", indent=2, level="command")
        Logger.log("byper install                         Install dependencies", indent=2, level="command")
        Logger.log("byper run <script>                    Run script", indent=2, level="command")
        Logger.log("byper task <name>                     Run a custom Byper task", indent=2, level="command")
        Logger.log("byper tree                            Print directory tree", indent=2, level="command")
        Logger.log("byper list                            List installed packages", indent=2, level="command")
        Logger.log("byper cache <list|clear|dir>          Manage pip cache", indent=2, level="command")
        Logger.log("byper doctor [--fix] [--yes]          Run dependencies diagnostics", indent=2, level="command")
        Logger.log("byper refresh                         Refresh environment packages", indent=2, level="command")
        Logger.log("byper publish                         Publish package to PyPI", indent=2, level="command")
        Logger.log("byper login                           PyPI login", indent=2, level="command")
        Logger.log("byper logout                          PyPI logout", indent=2, level="command")
        Logger.log("byper path                            Show project paths", indent=2, level="command")
        Logger.log("byper python                          Show project Python info", indent=2, level="command")
        Logger.log("byper reset [-y]                      Rebuild packages/", indent=2, level="command")
        Logger.log("byper                                 Run Byper itself to install dependencies from requirements.yaml", indent=2, level="command")

        Logger.log("\nFlags:",                            level="info")
        Logger.log("-h, --help                            Show help message", indent=2, level="command")
        Logger.log("-v, --version                         Print Byper version", indent=2, level="command")
        Logger.log("--no-cache                            Install packages without using cache", indent=2, level="command")
        Logger.log("-u, --upgrade                         Upgrade specified packages to latest version", indent=2, level="command")
        Logger.log("--u-all, --upgrade-all                Upgrade all packages to latest version", indent=2, level="command")
        Logger.log("-y                                    Skip confirmation prompts (used with init)", indent=2, level="command")

        exit(exit_code)

    @staticmethod
    def print_directory_tree(start_path=".", prefix="", excluded_dirs=None):
        if excluded_dirs is None:
            excluded_dirs = {ENVIRONMENT_DIRECTORY}

        try:
            entries = sorted(os.listdir(start_path))
        except OSError as e:
            print(f"{Fore.RED}Error accessing {start_path}: {e}{Style.RESET_ALL}")
            return

        files = []
        dirs = []

        for entry in entries:
            full_path = os.path.join(start_path, entry)
            if os.path.isdir(full_path):
                dirs.append(entry)
            else:
                files.append(entry)

        for index, directory in enumerate(dirs):
            is_last = index == len(dirs) - 1 and not files
            connector = "└── " if is_last else "├── "

            if directory in excluded_dirs:
                print(f"{prefix}{connector}{Fore.LIGHTBLACK_EX}{directory}/*{Style.RESET_ALL}")
            else:
                print(f"{prefix}{connector}{Fore.CYAN}{directory}/{Style.RESET_ALL}")
                new_prefix = f"{prefix}    " if is_last else f"{prefix}│   "
                Commands.print_directory_tree(
                    os.path.join(start_path, directory), new_prefix, excluded_dirs
                )

        for index, file in enumerate(files):
            is_last = index == len(files) - 1
            connector = "└── " if is_last else "├── "
            print(f"{prefix}{connector}{Fore.GREEN}{file}{Style.RESET_ALL}")

    @staticmethod
    def remove_package(package: str, flags: str | None = None):
        try:
            Installation.uninstall(package, flags)
        except Exception as e:
            Logger.log(f"❌ {package} failed to remove: {e}", level="error")

    @staticmethod
    def add_package(package: str, download: bool = False, no_cache: bool = False, upgrade: bool = False, flags: str | None = None):
        Installation.install(package, download, no_cache, upgrade, flags)

    @staticmethod
    def install():
        if not os.path.exists(REQUIREMENTS_FILE):
            Logger.log(f"❌ {REQUIREMENTS_FILE} not found in {os.getcwd()}", level="error")
            return

        ensure_project_environment()

        # Decide whether to install from lockfile
        lockfile_path = get_lockfile_path(find_project_root())
        if lockfile_path.exists():
            try:
                locked = LockfileManager.load_lockfile_manifest()
                manifest = Manifest.load_requirements_manifest()
                expected = manifest.get("dependencies", {})
                manifest_python = manifest.get("python")
                locked_python = LockfileManager.get_lockfile_python()

                lockfile_usable = locked == expected

                if manifest_python and lockfile_usable:
                    if not locked_python:
                        Logger.log(
                            "⚠️ Lockfile missing Python information, installing from requirements.yaml",
                            level="warn",
                        )
                        lockfile_usable = False
                    elif locked_python.get("required") != manifest_python:
                        Logger.log(
                            "🔁 Lockfile Python requirement changed, installing from requirements.yaml",
                            level="warn",
                        )
                        lockfile_usable = False

                if lockfile_usable:
                    Logger.log("📦 Installing from lockfile", level="install")
                    LockfileManager.install_from_lockfile()
                    return
                else:
                    Logger.log("🔁 Lockfile out of sync, installing from requirements.yaml", level="warn")
            except ValueError as e:
                Logger.log(f"❌ {e}", level="error")
                return

        Installation.install_from_requirements(show_log=True)

    @staticmethod
    def reinstall():
        Installation.install_from_requirements()

    @staticmethod
    def init(name: str | None = None, skip: bool = False):
        if name:
            os.makedirs(name, exist_ok=True)
            os.chdir(name)

        if not os.path.exists(REQUIREMENTS_FILE):
            project_name = name or os.path.basename(os.getcwd())

            name = project_name
            version = "0.0.1"
            description = None
            entry = "main.py"
            author = None
            license = "MIT"

            if not skip:
                name = input(f"name (default = {project_name}): ").strip() or project_name
                version = input(f"version (default = 0.0.1): ").strip() or "0.0.1"
                description = input(f"description: ").strip() or None
                entry = input("entry file (default = main.py): ").strip() or "main.py"
                author = input("author: ").strip() or None
                license = input("license (default = MIT): ").strip() or "MIT"

            manifest = {
                "name": project_name,
                "version": version,
                "description": description,
                "entry": entry,
                "author": author,
                "license": license,
                "scripts": {"start": f"python {entry}"},
            }

            Manifest.save_manifest(manifest)
            ensure_project_environment()

            with open(entry, "w") as f:
                f.write("print('Hello, world!')")

            if not skip:
                create_git = input("create git repository? (y/n): ").strip().lower()
                while create_git not in ["y", "n"]:
                    print("Invalid input. Please enter 'y' or 'n'.")
                    create_git = input("create git repository? (y/n): ").strip().lower()

                if create_git == "y":
                    process = subprocess.Popen(
                        ["git", "init"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                    )
                    process.wait()

                    Logger.log("📝 Git repository:")
                    for line in process.stdout:
                        Logger.log(f"→ {line.strip()}", level="command", indent=1)

                    print(f"Initialized {REQUIREMENTS_FILE} environment in {os.getcwd()}")

        else:
            Logger.log(f"{REQUIREMENTS_FILE} manifest already exists in {os.getcwd()}")

            if not os.path.exists(ENVIRONMENT_DIRECTORY):
                Logger.log(
                    f"📂 Creating missing {ENVIRONMENT_DIRECTORY} environment",
                    indent=1,
                    level="command",
                )
                ensure_project_environment()
                Logger.log(
                    f"✅ {ENVIRONMENT_DIRECTORY} environment created",
                    indent=1,
                    level="success",
                )

    @staticmethod
    def cache(action: str):
        result = run_project_pip(
            ["cache", action],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in result.stdout.splitlines():
            Logger.log(line.strip(), level="command")
        if result.returncode != 0:
            Logger.log("❌ pip cache command failed", level="error")

    @staticmethod
    def wheel(name: str):
        if not _has_module("wheel"):
            Logger.log("❌ 'wheel' is not installed in the project environment.", level="error")
            Logger.log("   Run: byper add wheel", level="command")
            return

        result = run_project_pip(
            ["wheel", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for line in result.stdout.splitlines():
            Logger.log(line.strip(), level="command")
        if result.returncode != 0:
            Logger.log(f"❌ Failed to build wheel for {name}", level="error")

    @staticmethod
    def list(flags=None):
        flags = flags or []
        args_list = [f"--{arg}" if arg == "outdated" else arg for arg in flags]
        show_cache = "cache" in args_list

        pip_args = ["cache", "list"] if show_cache else ["list"] + [arg for arg in flags if arg]
        result = run_project_pip(
            pip_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        for index, line in enumerate(result.stdout.splitlines()):
            if index == 0:
                Logger.log(line.strip(), level="success")
            else:
                Logger.log(line.strip(), level="command")

        if result.returncode != 0:
            Logger.log("❌ pip list failed", level="error")

    @staticmethod
    def run_script(_script: str):
        validate_project_environment()

        script = Manifest.load_script_from_manifest(_script)
        if not script:
            print(f"Script '{_script}' not found in manifest.")
            return

        run_in_project(script, check=True)

    @staticmethod
    def run_python_file(file_path: str):
        if not file_path.endswith(".py"):
            Logger.log("❌ Only Python files (.py) can be executed.", level="debug")
            return

        project_python = get_project_python()
        if not project_python.exists():
            Logger.log(f"❌ No byper environment found at {os.getcwd()}", level="debug")
            return

        try:
            run_project_python([file_path], check=True)
        except subprocess.CalledProcessError as e:
            Logger.log(f"❌ Script exited with error: {e.stderr}", level="error")

    @staticmethod
    def login():
        Logger.log("🔐 PyPI Login Setup", newline=True, level="install")
        Logger.log("To upload packages to PyPI, you need an API token.")
        Logger.log("You can generate one here:")
        Logger.log(
            "→ https://pypi.org/manage/account/#api-tokens",
            indent=1,
            newline=True,
            level="command",
        )

        Logger.log("Opening link in your browser...", level="command")
        webbrowser.open("https://pypi.org/manage/account/#api-tokens")

        from colorama import Fore, Style
        prompt = f"{Fore.BLUE}Enter your PyPI API token (starts with 'pypi-'): {Style.RESET_ALL}"
        token = input(prompt).strip()

        if not token.startswith("pypi-"):
            Logger.log("⚠️ Warning: This doesn't look like a valid PyPI API token", level="warn")
            return

        pypirc_path = os.path.expanduser("~/.pypirc")
        config = ConfigParser()

        if os.path.exists(pypirc_path):
            config.read(pypirc_path)

        config["distutils"] = {"index-servers": "pypi"}
        config["pypi"] = {"username": "__token__", "password": token}

        with open(pypirc_path, "w") as f:
            config.write(f)

        Logger.log(
            f"\n✅ Login successful. Your PyPI token has been saved to {pypirc_path}.",
            level="success",
            newline=True,
        )

    @staticmethod
    def logout():
        pypirc_path = os.path.expanduser("~/.pypirc")
        if os.path.exists(pypirc_path):
            os.remove(pypirc_path)
            Logger.log(f"✅ PyPI credentials removed from {pypirc_path}", level="success")
        else:
            Logger.log(f"❌ PyPI credentials not found at {pypirc_path}", level="error")

    @staticmethod
    def build(dist_dir="dist"):
        project_root = Path.cwd()
        dist_path = project_root / dist_dir

        if dist_path.exists():
            shutil.rmtree(dist_path)

        if not _has_module("build"):
            Logger.log("❌ 'build' is not installed in the project environment.", level="error")
            Logger.log("   Run: byper add build", level="command")
            return False

        project_python = get_project_python()
        Logger.log(f"📦 Building distribution using project Python: {project_python}")

        try:
            run_project_python(["-m", "build"], check=True)
            Logger.log("✅ Build completed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            Logger.log(f"❌ Build failed: {e}", level="error")
            return False

    @staticmethod
    def publish(dist_dir="dist"):
        project_root = Path.cwd()
        dist_path = project_root / dist_dir
        pypirc = Path.home() / ".pypirc"

        Logger.log("🚀 Preparing to upload your package to PyPI...\n")

        if not pypirc.exists():
            Logger.log("❌ PyPI credentials not found. Please run the login command first.")
            return

        if not (project_root / "setup.py").exists() and not (project_root / "pyproject.toml").exists():
            Logger.log("❌ No setup.py or pyproject.toml found. Cannot proceed.")
            return

        if not _has_module("twine"):
            Logger.log("❌ 'twine' is not installed in the project environment.", level="error")
            Logger.log("   Run: byper add twine", level="command")
            return

        build_ok = Commands.build(dist_dir)
        if not build_ok:
            return

        Logger.log("📤 Uploading via twine using project Python...")

        try:
            result = run_project_python(
                ["-m", "twine", "upload", f"{dist_path}/*"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=True,
            )
            Logger.log(result.stdout, level="command")
            Logger.log("✅ Successfully uploaded to PyPI!", level="success")
        except subprocess.CalledProcessError as e:
            Logger.log("❌ Upload failed.", level="error")
            if e.stdout:
                Logger.log(e.stdout, level="error")

    @staticmethod
    def path():
        project_root = find_project_root()
        packages = get_packages_dir(project_root)
        lockfile_path = get_lockfile_path(project_root)
        project_python = get_project_python(project_root)

        Logger.log(f"Project root: {project_root}")
        Logger.log(f"Packages: {packages}")
        Logger.log(f"Python: {project_python}")
        Logger.log(f"Lockfile: {lockfile_path}")

    @staticmethod
    def python_info():
        project_root = find_project_root()
        manifest = Manifest.load_requirements_manifest()
        raw_python = manifest.get("python")
        required = get_required_python()

        if raw_python is None:
            Logger.log("Requirement: not set")
        else:
            Logger.log(f"Requirement: {raw_python}")

        project_python = get_project_python(project_root)
        project_info = get_project_python_version_info(project_root)
        if project_info is None:
            Logger.log("Resolved: not found")
            Logger.log("Implementation: N/A")
            Logger.log(f"Path: {project_python}")
            Logger.log("Status: no environment")
        else:
            installed_version, impl = project_info
            Logger.log(f"Resolved: {format_version(installed_version)}")
            Logger.log(f"Implementation: {impl}")
            Logger.log(f"Path: {project_python}")

            if required is None or is_compatible(installed_version, required):
                Logger.log("Status: OK")
            else:
                Logger.log("Status: ERROR")
                Logger.log(
                    f"The local environment was created with Python {format_version(installed_version)},\n"
                    f"but this project requires Python {describe_requirement(required)}.\n\n"
                    "Run:\n"
                    "  byper reset",
                    level="error",
                )

    @staticmethod
    def _confirm_action(prompt: str, yes: bool = False) -> bool:
        if yes:
            return True
        try:
            answer = input(f"{prompt} [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return False
        return answer in ("y", "yes")

    @staticmethod
    def reset(yes: bool = False):
        project_root = find_project_root()
        packages = get_packages_dir(project_root)

        if not packages.exists():
            Logger.log("📦 No packages/ environment to reset. Creating one...")
            ensure_project_environment()
            Commands.install()
            return

        if not Commands._confirm_action("This will remove and rebuild packages/.\nContinue?", yes=yes):
            Logger.log("Canceled.", level="warn")
            return

        _safely_remove_packages_dir(packages)

        Logger.log("🔄 Rebuilding environment...")
        ensure_project_environment()
        Commands._refresh_stubs()
        Commands.install()

    @staticmethod
    def doctor_fix(yes: bool = False):
        project_root = find_project_root()
        packages = get_packages_dir(project_root)
        fixed_anything = False

        # 1. Check for environment version mismatch (requires full reset).
        required = get_required_python()
        if packages.exists() and required is not None:
            project_info = get_project_python_version_info(project_root)
            if project_info is not None:
                installed_version, _impl = project_info
                if not is_compatible(installed_version, required):
                    Logger.log(
                        f"⚠️ Environment Python {format_version(installed_version)} "
                        f"does not meet requirement {describe_requirement(required)}.",
                        level="warn",
                    )
                    if Commands._confirm_action(
                        "Fixing this requires removing and rebuilding packages/.\nContinue?", yes=yes
                    ):
                        _safely_remove_packages_dir(packages)
                        ensure_project_environment()
                        Commands._refresh_stubs()
                        Commands.install()
                        fixed_anything = True
                    else:
                        Logger.log("Run:\n  byper reset", level="command")
                    return

        # 2. Create packages/ if missing.
        if not packages.exists():
            Logger.log("📦 Creating missing packages/ environment...", level="install")
            ensure_project_environment()
            fixed_anything = True

        # 3. Regenerate lockfile if missing.
        lockfile_path = get_lockfile_path(project_root)
        if not lockfile_path.exists():
            Logger.log("📦 Regenerating byper.lock...", level="install")
            Commands.install()
            fixed_anything = True
        else:
            # Install dependencies.
            Commands.install()

        # 4. Refresh stubs.
        Commands._refresh_stubs()

        if fixed_anything:
            Logger.log("✅ Issues fixed.", level="success")
        else:
            Logger.log("✅ No issues found.", level="success")

    @staticmethod
    def _refresh_stubs():
        from byper.__core__.helpers import generate_env_stub, generate_tasks_stub

        try:
            generate_tasks_stub()
            generate_env_stub()
        except Exception:
            pass

    @staticmethod
    def refresh():
        try:
            Logger.log("🔄 Refreshing Byper stubs...")
            Commands._refresh_stubs()
            Logger.log("✅ Stubs refreshed!", level="success")
        except Exception as e:
            Logger.log(f"❌ Failed to refresh stubs: {e}", level="error")
