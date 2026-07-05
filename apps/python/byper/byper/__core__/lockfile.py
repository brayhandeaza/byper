import json
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests
from packaging.utils import canonicalize_name
from ruamel.yaml import YAML

from byper.__core__.constants import LOCKFILE_NAME, get_lockfile_path
from byper.__core__.project_env import find_project_root, run_project_pip, run_project_python

if TYPE_CHECKING:
    from byper.__core__.utils.logger import Logger

Logger = getattr(__import__("byper.__core__.utils.logger", fromlist=["Logger"]), "Logger")


def _normalize(name: str) -> str:
    """Normalize a package name for comparison: lowercase, dashes to underscores."""
    return name.lower().replace("-", "_")


def _is_legacy_format(packages: dict) -> bool:
    """Detect legacy lockfile format where values are plain version strings."""
    if not packages:
        return False
    first_val = next(iter(packages.values()), None)
    return isinstance(first_val, str)


def _normalize_legacy_packages(packages: dict) -> dict:
    """Convert legacy {name: version_str} to new {name@version: {metadata}}."""
    result = {}
    for name, version in packages.items():
        key = f"{name}@{version}"
        result[key] = {
            "name": name,
            "version": str(version) if version else "",
            "source": "pypi",
            "resolved": None,
            "integrity": None,
            "direct": True,
            "group": "main",
            "dependencies": {},
        }
    return result


def _fetch_package_metadata(name: str, version: str) -> dict | None:
    """Fetch resolved URL and integrity from PyPI JSON API."""
    try:
        url = f"https://pypi.org/pypi/{name}/{version}/json"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return None

        data = resp.json()
        urls = data.get("urls", [])
        if not urls:
            return None

        wheel = None
        sdist = None
        for u in urls:
            if u.get("packagetype") == "bdist_wheel" and not wheel:
                wheel = u
            elif u.get("packagetype") == "sdist" and not sdist:
                sdist = u

        selected = wheel or sdist
        if not selected:
            return None

        result = {"resolved": selected.get("url", None)}
        digests = selected.get("digests", {})
        if "sha256" in digests:
            result["integrity"] = f"sha256:{digests['sha256']}"
        return result

    except Exception:
        return None


def _collect_dependencies(name: str) -> dict:
    """Collect declared dependencies from installed package metadata.

    Runs inside the *project* Python (packages/bin/python) so we read the
    project venv metadata, never the global interpreter.
    """
    try:
        code = (
            "import importlib.metadata as md\n"
            "import json\n"
            "from packaging.utils import canonicalize_name\n"
            f"dist = md.distribution('{name}')\n"
            "reqs = dist.requires or []\n"
            "deps = {}\n"
            "for r in reqs:\n"
            "    parts = r.split(';', 1)\n"
            "    spec = parts[0].strip()\n"
            "    marker = parts[1].strip() if len(parts) > 1 else ''\n"
            "    if 'extra ==' in marker:\n"
            "        continue\n"
            "    pkg_parts = spec.split()\n"
            "    pkg_name = canonicalize_name(pkg_parts[0])\n"
            "    pkg_version = ' '.join(pkg_parts[1:]) if len(pkg_parts) > 1 else ''\n"
            "    if pkg_version:\n"
            "        deps[pkg_name] = pkg_version\n"
            "    else:\n"
            "        deps[pkg_name] = '*'\n"
            "print(json.dumps(deps))\n"
        )
        result = run_project_python(
            ["-c", code],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return json.loads(result.stdout)
    except Exception:
        pass
    return {}


def _get_installed_version_map() -> dict:
    """Return {normalized_name: version_str} for packages in the project venv."""
    try:
        result = run_project_pip(
            ["list", "--format=json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            installed = json.loads(result.stdout)
            return {
                _normalize(pkg["name"]): pkg["version"]
                for pkg in installed
            }
    except Exception:
        pass
    return {}


def _build_dependency_graph(
    roots: dict,
) -> tuple[dict, dict]:
    """Walk the dependency graph from roots, returning only reachable packages.

    Args:
        roots: {normalized_name: version_str} — direct dependencies.

    Returns:
        (graph_packages, graph_deps) where:
        - graph_packages: {normalized_name: installed_version} for all graph nodes.
        - graph_deps: {normalized_name: {dep_name: version_spec}} for each node.
    """
    installed_map = _get_installed_version_map()

    # BFS over declared dependencies
    visited: dict[str, str] = {}  # name -> installed_version
    dep_map: dict[str, dict] = {}  # name -> {dep_name: version_spec}
    queue: list[str] = []

    # Seed queue with roots that are actually installed
    for norm_name, version in roots.items():
        installed_ver = installed_map.get(norm_name)
        if installed_ver:
            visited[norm_name] = installed_ver
            queue.append(norm_name)

    while queue:
        current = queue.pop(0)
        if current in dep_map:
            continue

        # Find the original package name to query metadata
        original_name = current
        # Look up the installed name (might differ in case/dash)
        for inst_name in installed_map:
            if _normalize(inst_name) == current:
                original_name = inst_name
                break

        deps = _collect_dependencies(original_name)
        dep_map[current] = deps

        for dep_name in deps:
            if dep_name in visited:
                continue
            inst_ver = installed_map.get(dep_name)
            if inst_ver:
                visited[dep_name] = inst_ver
                queue.append(dep_name)

    return visited, dep_map


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
        """Return a flat {name: version_str} dict regardless of lockfile format."""
        data = LockfileManager.load_lockfile_data(project_root)
        packages = data.get("packages", {})
        if packages is None:
            packages = {}
        if not isinstance(packages, dict):
            raise ValueError(f"Lockfile {LOCKFILE_NAME} is corrupt: 'packages' is not a mapping")

        if _is_legacy_format(packages):
            Logger.log("Legacy byper.lock format detected. Regenerating lockfile.", level="warn")
            return dict(packages)

        result = {}
        for key, entry in packages.items():
            if isinstance(entry, dict):
                name = entry.get("name", key.split("@")[0])
                version = entry.get("version", "")
            else:
                name = key.split("@")[0]
                version = str(entry) if entry else ""
            result[_normalize(name)] = version
        return result

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
        """Add a single package entry in the new structured format."""
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

        packages = data.get("packages", {})
        if not isinstance(packages, dict):
            packages = {}

        if _is_legacy_format(packages):
            Logger.log("Legacy byper.lock format detected. Regenerating lockfile.", level="warn")
            packages = _normalize_legacy_packages(packages)

        norm = _normalize(package_name)
        key = f"{norm}@{version}"
        meta = _fetch_package_metadata(package_name, version) or {}

        packages[key] = {
            "name": package_name,
            "version": version,
            "source": "pypi",
            "resolved": meta.get("resolved"),
            "integrity": meta.get("integrity"),
            "direct": True,
            "group": "main",
            "dependencies": _collect_dependencies(package_name),
        }

        data["packages"] = packages
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
        if not isinstance(packages, dict):
            return

        normalized = _normalize(package_name)
        if _is_legacy_format(packages):
            if normalized in packages:
                del packages[normalized]
            if package_name in packages:
                del packages[package_name]
        else:
            to_remove = []
            for key, entry in packages.items():
                if isinstance(entry, dict):
                    entry_name = _normalize(entry.get("name", ""))
                else:
                    entry_name = _normalize(key.split("@")[0])
                if entry_name == normalized:
                    to_remove.append(key)
            for key in to_remove:
                del packages[key]

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
        """Generate the lockfile from the dependency graph rooted at requirements.yaml."""
        root = LockfileManager._resolve_project_root(project_root)
        lockfile_path = get_lockfile_path(root)

        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.indent(mapping=2, sequence=4, offset=2)
        yaml.width = 4096

        existing = LockfileManager.load_lockfile_data(project_root)

        # Normalize root names
        roots = {_normalize(k): v for k, v in dependencies.items()}

        # Build dependency graph from roots
        graph_packages, graph_deps = _build_dependency_graph(roots)

        structured: dict = {}

        for norm_name, installed_version in graph_packages.items():
            is_direct = norm_name in roots
            key = f"{norm_name}@{installed_version}"
            meta = _fetch_package_metadata(norm_name, installed_version) or {}

            structured[key] = {
                "name": norm_name,
                "version": installed_version,
                "source": "pypi",
                "resolved": meta.get("resolved"),
                "integrity": meta.get("integrity"),
                "direct": is_direct,
                "group": "main",
                "dependencies": graph_deps.get(norm_name, {}),
            }

        data: dict = {"lock_version": 1, "packages": structured}
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

        for name, version in packages.items():
            if not version:
                Logger.log(f"❌ Lockfile entry for {name} has no version", level="error")
                continue
            try:
                Installation.install(f"{name}=={version}", update_manifest=False)
            except Exception as e:
                Logger.log(f"❌ Failed to install {name}=={version}: {e}", level="error")

        Logger.log(f"✅ Installed dependencies from {LOCKFILE_NAME}", level="success")
