import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Optional

from byper.__core__.constants import ENVIRONMENT_DIRECTORY, REQUIREMENTS_FILE
from byper.__core__.utils.logger import Logger


IS_WINDOWS = platform.system() == "Windows"


def get_required_python() -> tuple[int, ...] | None:
    """Return the Python version required by the current project, if any."""
    from byper.__core__.manifest import Manifest
    from byper.__core__.python_version import parse_version_string

    manifest = Manifest.load_requirements_manifest()
    raw = manifest.get("python")
    if not raw:
        return None

    try:
        return parse_version_string(str(raw))
    except ValueError:
        Logger.log(f"❌ Invalid python version in {REQUIREMENTS_FILE}: {raw}", level="error")
        sys.exit(1)


def get_project_python_version_info(
    project_root: Optional[Path | str] = None,
) -> tuple[tuple[int, int, int], str] | None:
    """Return the version and implementation of the project's local Python."""
    from byper.__core__.python_version import get_python_version_info

    project_python = get_project_python(project_root)
    if not project_python.exists():
        return None

    return get_python_version_info([str(project_python)])


def get_project_python_lock_info(project_root: Optional[Path | str] = None) -> dict | None:
    """Build the python section to store in the lockfile.

    Returns ``None`` when the project does not declare a Python version.
    """
    from byper.__core__.manifest import Manifest
    from byper.__core__.python_version import (
        find_compatible_python,
        format_version,
        is_compatible,
        PythonNotFoundError,
    )

    required = get_required_python()
    if required is None:
        return None

    manifest = Manifest.load_requirements_manifest()
    raw_required = manifest.get("python")

    info = {
        "required": str(raw_required),
    }

    # Prefer the version actually used by the local environment.
    project_info = get_project_python_version_info(project_root)
    if project_info:
        installed_version, impl = project_info
        if is_compatible(installed_version, required):
            info["resolved"] = format_version(installed_version)
            info["implementation"] = impl
            return info

    # Otherwise report the first compatible interpreter we can find.
    try:
        _cmd, version_info, impl = find_compatible_python(required)
        info["resolved"] = format_version(version_info)
        info["implementation"] = impl
    except PythonNotFoundError:
        info["resolved"] = None
        info["implementation"] = None

    return info


def validate_project_environment(project_root: Optional[Path | str] = None) -> None:
    """Validate that an existing environment matches the required Python version."""
    from byper.__core__.python_version import (
        describe_requirement,
        format_version,
        is_compatible,
    )

    required = get_required_python()
    if required is None:
        return

    project_info = get_project_python_version_info(project_root)
    if project_info is None:
        return

    installed_version, _impl = project_info
    if is_compatible(installed_version, required):
        return

    message = (
        f"The local environment was created with Python {format_version(installed_version)},\n"
        f"but this project requires Python {describe_requirement(required)}.\n\n"
        "Delete packages/ and run:\n"
        "  byper install"
    )
    Logger.log(f"❌ {message}", level="error")
    sys.exit(1)

def _get_byper_package_path() -> Path:
    """Get the filesystem path to the ``byper`` package directory."""
    spec = importlib.util.find_spec("byper")
    if spec is not None and spec.origin is not None:
        return Path(spec.origin).resolve().parent
    # Fallback: walk up from this file's location.
    return Path(__file__).resolve().parent.parent


# Directory that must be on PYTHONPATH so project subprocesses can import byper.
BYPER_PACKAGE_ROOT = _get_byper_package_path().parent


def find_project_root(start_path: Optional[Path | str] = None) -> Path:
    """Busca hacia arriba el directorio que contiene requirements.yaml.

    Si no se encuentra, retorna el directorio de trabajo actual para mantener
    compatibilidad con el comportamiento anterior.
    """
    path = Path(start_path or os.getcwd()).resolve()
    for candidate in [path, *path.parents]:
        if (candidate / REQUIREMENTS_FILE).is_file():
            return candidate
    return path


def get_packages_dir(project_root: Optional[Path | str] = None) -> Path:
    root = Path(project_root or find_project_root())
    return root / ENVIRONMENT_DIRECTORY


def get_project_bin_dir(project_root: Optional[Path | str] = None) -> Path:
    packages = get_packages_dir(project_root)
    return packages / ("Scripts" if IS_WINDOWS else "bin")


def get_project_python(project_root: Optional[Path | str] = None) -> Path:
    bin_dir = get_project_bin_dir(project_root)
    return bin_dir / ("python.exe" if IS_WINDOWS else "python")


def get_project_pip(project_root: Optional[Path | str] = None) -> list[str]:
    """Retorna la lista de argumentos para invocar pip del proyecto."""
    return [str(get_project_python(project_root)), "-m", "pip"]


@lru_cache(maxsize=32)
def get_project_site_packages(project_root: Optional[Path | str] = None) -> Path:
    """Obtiene el directorio site-packages del environment local.

    Si el environment no existe, retorna la ruta teórica basada en la versión
    del intérprete actual como fallback.
    """
    root = Path(project_root or find_project_root())
    python = get_project_python(root)

    if python.exists():
        try:
            result = subprocess.run(
                [str(python), "-c", "import site, sys; print(site.getsitepackages()[0])"],
                capture_output=True,
                text=True,
                check=False,
            )
            path = result.stdout.strip()
            if path and Path(path).exists():
                return Path(path)
        except Exception:
            pass

    # Fallback teórico basado en la versión del intérprete actual.
    version = f"{sys.version_info.major}.{sys.version_info.minor}"
    return get_packages_dir(root) / "lib" / f"python{version}" / "site-packages"


def build_project_env(
    project_root: Optional[Path | str] = None,
    base_env: Optional[dict[str, str]] = None,
) -> dict[str, str]:
    """Construye un environ para subprocess con el venv local activado."""
    env = (base_env or os.environ).copy()
    packages = get_packages_dir(project_root)
    bin_dir = get_project_bin_dir(project_root)

    env["VIRTUAL_ENV"] = str(packages)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"

    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        env["PYTHONPATH"] = f"{BYPER_PACKAGE_ROOT}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = str(BYPER_PACKAGE_ROOT)

    return env


def ensure_project_environment(project_root: Optional[Path | str] = None) -> Path:
    """Crea el environment local si no existe y asegura que byper sea importable."""
    from byper.__core__.python_version import (
        describe_requirement,
        find_compatible_python,
        format_version,
        PythonNotFoundError,
    )

    packages = get_packages_dir(project_root)
    if packages.exists():
        validate_project_environment(project_root)
        return packages

    required = get_required_python()

    if required is not None:
        Logger.log(
            f"🔍 Python requirement: {describe_requirement(required)}",
            level="info",
        )
        try:
            executable, version_info, impl = find_compatible_python(required)
        except PythonNotFoundError as exc:
            Logger.log(f"❌ {exc}", level="error")
            sys.exit(1)

        resolved = format_version(version_info)
        Logger.log(
            f"✅ Using Python {resolved} ({impl}) from {' '.join(executable)}",
            level="success",
        )
    else:
        executable = [sys.executable]

    Logger.log(f"📦 Creando environment local: {packages}", level="install")
    subprocess.check_call(executable + ["-m", "venv", str(packages)])
    Logger.log("✅ Environment creado", level="success")

    # Install byper into the project environment so aliases/env work in project subprocesses.
    Logger.log("📦 Instalando byper en el environment local", level="install")
    _install_byper_into_project(packages.parent)
    Logger.log("✅ byper instalado en el environment local", level="success")

    return packages


def _install_byper_into_project(project_root: Path) -> None:
    """Make the ``byper`` package importable inside the project's venv."""
    source_root = _find_byper_project_root()
    project_pip = [str(get_project_python(project_root)), "-m", "pip", "install", "--quiet"]

    if source_root is not None:
        subprocess.check_call(project_pip + ["-e", str(source_root)])
        return

    # Installed globally — copy the package and install its dependencies.
    byper_pkg = _get_byper_package_path()

    result = subprocess.run(
        [str(get_project_python(project_root)), "-c", "import site; print(site.getsitepackages()[0])"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        Logger.log("⚠️ Could not determine project site-packages", level="warn")
        return

    target = Path(result.stdout.strip()) / "byper"
    if target.exists():
        if target.is_symlink():
            target.unlink()
        else:
            shutil.rmtree(target)
    shutil.copytree(str(byper_pkg), str(target))

    # Install byper's dependencies into the project venv.
    try:
        from importlib.metadata import distribution
    except ImportError:
        from importlib_metadata import distribution

    try:
        dist = distribution("byper")
        requires = getattr(dist, "requires", None)
        if requires:
            dep_names = []
            for req in requires:
                dep_names.append(str(req))
            if dep_names:
                subprocess.check_call(project_pip + dep_names)
    except Exception:
        Logger.log("⚠️ Could not install byper dependencies into project environment", level="warn")


def _find_byper_project_root() -> Path | None:
    """Find the byper source root (containing pyproject.toml or setup.py)."""
    current = Path(__file__).resolve().parent  # __core__/
    for _ in range(10):
        if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
            return current
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def run_project_python(
    args: list[str],
    *,
    project_root: Optional[Path | str] = None,
    env: Optional[dict[str, str]] = None,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Ejecuta el Python del environment local con los argumentos dados."""
    python = get_project_python(project_root)
    if not python.exists():
        raise FileNotFoundError(
            f"No se encontró el Python del proyecto: {python}. "
            "Ejecuta 'byper install' primero."
        )

    validate_project_environment(project_root)

    project_env = build_project_env(project_root, base_env=env)
    return subprocess.run([str(python)] + list(args), env=project_env, **kwargs)


def run_project_pip(
    args: list[str],
    *,
    project_root: Optional[Path | str] = None,
    env: Optional[dict[str, str]] = None,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Ejecuta pip dentro del Python del environment local."""
    return run_project_python(
        ["-m", "pip", "--disable-pip-version-check"] + list(args),
        project_root=project_root,
        env=env,
        **kwargs,
    )


def run_in_project(
    cmd: str,
    *,
    project_root: Optional[Path | str] = None,
    env: Optional[dict[str, str]] = None,
    **kwargs,
) -> subprocess.CompletedProcess:
    """Ejecuta un comando shell con el environment local activado en PATH."""
    project_env = build_project_env(project_root, base_env=env)
    return subprocess.run(cmd, shell=True, env=project_env, **kwargs)


def is_project_environment_ready(project_root: Optional[Path | str] = None) -> bool:
    return get_project_python(project_root).exists()
