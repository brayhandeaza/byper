import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from typing import Optional

import requests

from byper.__core__.constants import BYPER_BIN_DIR, BYPER_HOME, BYPER_PYTHONS_DIR
from byper.__core__.python_version import (
    Requirement,
    format_version,
    get_python_version_info,
    is_compatible,
    parse_version_string,
)

IS_WINDOWS = sys.platform == "win32"

BUILD_STANDALONE_REPO = "astral-sh/python-build-standalone"
BUILD_STANDALONE_API = f"https://api.github.com/repos/{BUILD_STANDALONE_REPO}/releases"

_DOWNLOADS_CACHE_FILE = BYPER_HOME / "cache" / "python-downloads.json"


def _detect_platform_target() -> str:
    """Return the python-build-standalone platform triple for this machine."""
    system = platform.system()
    machine = platform.machine()

    if system == "Darwin":
        if machine == "arm64":
            return "aarch64-apple-darwin"
        return "x86_64-apple-darwin"

    if system == "Linux":
        if machine == "aarch64":
            return "aarch64-unknown-linux-gnu"
        return "x86_64-unknown-linux-gnu"

    if system == "Windows":
        if machine in ("ARM64", "aarch64"):
            return "aarch64-pc-windows-msvc"
        return "x86_64-pc-windows-msvc"

    raise RuntimeError(f"Unsupported platform: {system} {machine}")


def _make_asset_name(version: str, target: str) -> str:
    """Build the expected asset filename for a python-build-standalone release."""
    return f"cpython-{version}-{target}-install_only.tar.gz"


def _parse_version_from_filename(filename: str) -> Optional[str]:
    """Extract the version string from a python-build-standalone asset name.

    e.g. ``cpython-3.12.8+20250101-aarch64-apple-darwin-install_only.tar.gz``
         → ``"3.12.8"``
    """
    if not filename.startswith("cpython-"):
        return None
    rest = filename[len("cpython-"):]
    parts = rest.split("-", 1)
    if not parts:
        return None
    version_raw = parts[0]
    if "+" in version_raw:
        version_raw = version_raw.split("+")[0]
    if version_raw.count(".") >= 2:
        return version_raw
    return None


def _find_download_url(version_spec: str, target: str) -> tuple[str, str]:
    """Find the download URL for the latest Python matching *version_spec*."""
    from byper.__core__.utils.logger import Logger

    requirement = parse_version_string(version_spec)
    Logger.log(f"🔍 Searching for Python {version_spec}...", level="info")

    cache_key = f"{version_spec}::{target}"
    cached = _get_cached_download(cache_key)
    if cached is not None:
        url, resolved = cached
        parts = tuple(int(p) for p in resolved.split("."))
        if is_compatible(parts, requirement):
            Logger.log(f"✅ Found Python {resolved} (cached)", level="success")
            return url, resolved

    # Fast path: try the latest release first (tiny payload).
    latest_url, latest_version = _search_latest_release(requirement, target)
    if latest_url is not None and latest_version is not None:
        resolved = format_version(latest_version)
        _cache_download(cache_key, latest_url, resolved)
        Logger.log(f"✅ Found Python {resolved}", level="success")
        return latest_url, resolved

    # Slower path: scan the most recent 5 releases.
    best_url, best_version = _search_releases(requirement, target, 5)
    if best_url is not None and best_version is not None:
        resolved = format_version(best_version)
        _cache_download(cache_key, best_url, resolved)
        Logger.log(f"✅ Found Python {resolved}", level="success")
        return best_url, resolved

    raise RuntimeError(
        f"No compatible Python {version_spec} release found for {target}."
    )


def _get_cache_file() -> Path:
    _DOWNLOADS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    return _DOWNLOADS_CACHE_FILE


def _get_cached_download(key: str) -> Optional[tuple[str, str]]:
    cache_file = _get_cache_file()
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text())
        entry = data.get(key)
        if entry is None:
            return None
        return entry["url"], entry["version"]
    except Exception:
        return None


def _cache_download(key: str, url: str, version: str) -> None:
    cache_file = _get_cache_file()
    data: dict = {}
    if cache_file.exists():
        try:
            data = json.loads(cache_file.read_text())
        except Exception:
            data = {}
    data[key] = {"url": url, "version": version}
    try:
        cache_file.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def _search_latest_release(
    requirement, target: str
) -> tuple[Optional[str], Optional[tuple[int, ...]]]:
    """Search only the latest release. Very fast, tiny payload."""
    for attempt in range(1, 3):
        try:
            resp = requests.get(
                f"{BUILD_STANDALONE_API}/latest",
                timeout=10,
            )
            resp.raise_for_status()
            break
        except requests.RequestException:
            if attempt < 2:
                time.sleep(1)
    else:
        return None, None

    release = resp.json()
    if not isinstance(release, dict):
        return None, None

    return _extract_best_asset(release.get("assets", []), requirement, target)


def _extract_best_asset(
    assets: list,
    requirement: Requirement,
    target: str,
) -> tuple[Optional[str], Optional[tuple[int, ...]]]:
    best_url: Optional[str] = None
    best_version: Optional[tuple[int, ...]] = None

    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name", "")
        if not name.endswith(f"-{target}-install_only.tar.gz"):
            continue

        version_str = _parse_version_from_filename(name)
        if version_str is None:
            continue

        try:
            version_parts = tuple(int(p) for p in version_str.split("."))
        except ValueError:
            continue

        if not is_compatible(version_parts, requirement):
            continue

        if best_version is None or version_parts > best_version:
            best_version = version_parts
            best_url = asset.get("browser_download_url")

    return best_url, best_version


def _search_releases(
    requirement, target: str, per_page: int
) -> tuple[Optional[str], Optional[tuple[int, ...]]]:
    params = {"per_page": per_page}
    last_error: Optional[str] = None

    for attempt in range(1, 4):
        try:
            resp = requests.get(BUILD_STANDALONE_API, params=params, timeout=10)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            last_error = str(e)
            if attempt < 3:
                time.sleep(2 ** attempt)
    else:
        raise RuntimeError(
            f"Could not reach GitHub after 3 attempts: {last_error}"
        )

    releases = resp.json()
    if not isinstance(releases, list):
        return None, None

    best_url: Optional[str] = None
    best_version: Optional[tuple[int, ...]] = None

    for release in releases:
        if not isinstance(release, dict):
            continue
        url, version = _extract_best_asset(
            release.get("assets", []), requirement, target
        )
        if version is not None and (best_version is None or version > best_version):
            best_version = version
            best_url = url

    return best_url, best_version


def _download_file(url: str, dest: Path) -> None:
    """Download a file from *url* to *dest* with progress reporting."""
    from byper.__core__.utils.logger import Logger

    filename = url.split("/")[-1]
    try:
        with requests.get(url, stream=True, timeout=300) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            mb = f" ({total / 1024 / 1024:.0f} MB)" if total else ""
            Logger.log(f"⬇️  Downloading {filename}{mb}...", level="install")
            downloaded = 0
            last_pct = -1
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = int(downloaded * 100 / total)
                        if pct > last_pct:
                            last_pct = pct
                            bar_len = 30
                            filled = int(bar_len * downloaded / total)
                            bar = "█" * filled + "░" * (bar_len - filled)
                            sys.stdout.write(f"\r  [{bar}] {pct}%")
                            sys.stdout.flush()
            if total:
                sys.stdout.write("\n")
                sys.stdout.flush()
    except requests.RequestException as e:
        if dest.exists():
            dest.unlink()
        raise RuntimeError(f"Download failed: {e}")


def _extract_tarball(archive: Path, dest_dir: Path) -> None:
    """Extract a .tar.gz archive into *dest_dir*, flattening a single top-level dir."""
    from byper.__core__.utils.logger import Logger

    Logger.log(f"📦 Extracting {archive.name}...", level="install")
    dest_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive, "r:gz") as tf:
        members = tf.getmembers()
        tf.extractall(path=dest_dir, filter="data")

    if not members:
        return

    top_name = members[0].name.split("/")[0]
    if not top_name or top_name == ".":
        return

    nested = dest_dir / top_name
    if nested.is_dir() and nested.name != "bin":
        for child in nested.iterdir():
            target = dest_dir / child.name
            if target.exists():
                if target.is_dir():
                    shutil.rmtree(target, ignore_errors=True)
                else:
                    target.unlink(missing_ok=True)
            shutil.move(str(child), str(target))
        nested.rmdir()

    python_bin = _find_python_binary(dest_dir)
    if python_bin.exists() and not IS_WINDOWS:
        python_bin.chmod(0o755)


def _link_system_pythons() -> None:
    """Create symlinks in ``~/.byper/pythons/`` for system Python installations.

    This makes globally installed Pythons visible through the byper runtime
    directory, so ``list_installed_runtimes()`` and ``_byper_managed_candidates()``
    can find them without showing raw system paths.
    """
    from byper.__core__.python_version import (
        format_version,
        get_python_version_info,
        list_installed_pythons,
    )

    BYPER_PYTHONS_DIR.mkdir(parents=True, exist_ok=True)
    seen_versions: set[str] = set()

    for cmd, version_info, _impl in list_installed_pythons():
        version_str = format_version(version_info)
        if version_str in seen_versions:
            continue
        seen_versions.add(version_str)

        runtime_dir = BYPER_PYTHONS_DIR / version_str
        python_link = runtime_dir / ("python.exe" if IS_WINDOWS else "python")

        if python_link.exists() or (IS_WINDOWS and (runtime_dir / "python.cmd").exists()):
            continue

        source_path = cmd[0]
        try:
            found = __import__("shutil").which(source_path)
        except Exception:
            found = None
        if not found:
            continue

        info = get_python_version_info([str(found)])
        if info is None:
            continue

        actual_version_str = format_version(info[0])
        if actual_version_str != version_str:
            continue

        runtime_dir.mkdir(parents=True, exist_ok=True)
        try:
            python_link.symlink_to(found)
        except OSError:
            if IS_WINDOWS:
                _create_windows_python_cmd(runtime_dir, found)
            continue


def _create_windows_python_cmd(runtime_dir: Path, target: str) -> None:
    """Create a ``python.cmd`` wrapper when symlinks are unavailable on Windows."""
    cmd_path = runtime_dir / "python.cmd"
    try:
        cmd_path.write_text(f'@echo off\n"{target}" %*\n', encoding="utf-8")
    except OSError:
        pass


def list_installed_runtimes() -> dict[str, Path]:
    """Return ``{version_string: install_dir}`` for runtimes managed by byper."""
    _link_system_pythons()

    if not BYPER_PYTHONS_DIR.exists():
        return {}

    result: dict[str, Path] = {}
    for entry in sorted(BYPER_PYTHONS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        python_path = _find_python_binary(entry)
        if not python_path.exists():
            continue
        info = get_python_version_info([str(python_path)])
        if info is not None:
            version_str = format_version(info[0])
            result[version_str] = entry
        else:
            result[entry.name] = entry
    return result


def get_runtime_dir(version: str) -> Path:
    """Return the expected install path for a Python runtime version."""
    return BYPER_PYTHONS_DIR / version


def is_runtime_installed(version: str) -> bool:
    """Check if a specific Python runtime version is already installed."""
    runtime_dir = get_runtime_dir(version)
    return _find_python_binary(runtime_dir).exists()


def _compute_best_runtimes(
    runtimes: dict[str, Path]
) -> tuple[
    Optional[tuple[tuple[int, ...], Path]],
    dict[int, tuple[tuple[int, ...], Path]],
    dict[tuple[int, int], tuple[tuple[int, ...], Path]],
]:
    """Find the best runtime for each version prefix.

    Returns ``(best_overall, best_by_major, best_by_minor)``.
    """
    best_overall: Optional[tuple[tuple[int, ...], Path]] = None
    best_by_major: dict[int, tuple[tuple[int, ...], Path]] = {}
    best_by_minor: dict[tuple[int, int], tuple[tuple[int, ...], Path]] = {}

    for version_str, runtime_dir in runtimes.items():
        try:
            parts = tuple(int(p) for p in version_str.split("."))
        except ValueError:
            continue
        if len(parts) < 2:
            continue

        python_bin = _find_python_binary(runtime_dir)
        if not python_bin.exists():
            continue

        entry: tuple[tuple[int, ...], Path] = (parts, python_bin)

        if best_overall is None or parts > best_overall[0]:
            best_overall = entry

        major = parts[0]
        if major not in best_by_major or parts > best_by_major[major][0]:
            best_by_major[major] = entry

        minor_key = (parts[0], parts[1])
        if minor_key not in best_by_minor or parts > best_by_minor[minor_key][0]:
            best_by_minor[minor_key] = entry

    return best_overall, best_by_major, best_by_minor


def _write_python_shim(shim_path: Path, python_bin: Path) -> None:
    """Write a shim that invokes *python_bin*."""
    if IS_WINDOWS:
        cmd_path = shim_path.with_suffix(".cmd")
        cmd_path.write_text(f'@echo off\n"{python_bin}" %*\n', encoding="utf-8")
        return

    shim_path.write_text(
        f'#!/bin/sh\nexec "{python_bin}" "$@"\n',
        encoding="utf-8",
    )
    shim_path.chmod(0o755)


def _write_pip_shim(shim_path: Path, python_bin: Path) -> None:
    """Write a shim that invokes pip via *python_bin*."""
    if IS_WINDOWS:
        cmd_path = shim_path.with_suffix(".cmd")
        cmd_path.write_text(
            f'@echo off\n"{python_bin}" -m pip %*\n',
            encoding="utf-8",
        )
        return

    shim_path.write_text(
        f'#!/bin/sh\nexec "{python_bin}" -m pip "$@"\n',
        encoding="utf-8",
    )
    shim_path.chmod(0o755)


def refresh_global_shims() -> None:
    """Create/update global shims in ``~/.byper/bin/`` for all installed runtimes.

    Generated shims include ``python``, ``python3``, ``python3.12``,
    ``python3.12.8`` and the equivalent ``pip`` variants.  The most recent
    installed version wins for each prefix.
    """
    BYPER_BIN_DIR.mkdir(parents=True, exist_ok=True)
    runtimes = list_installed_runtimes()

    python_shims: dict[str, Path] = {}

    # Exact version shims: python3.12.8, pip3.12.8
    for version_str, runtime_dir in runtimes.items():
        python_bin = _find_python_binary(runtime_dir)
        if python_bin.exists():
            python_shims[f"python{version_str}"] = python_bin

    # Best-prefix shims.
    best_overall, best_by_major, best_by_minor = _compute_best_runtimes(runtimes)
    if best_overall is not None:
        python_shims["python"] = best_overall[1]
    for major, (_, python_bin) in best_by_major.items():
        python_shims[f"python{major}"] = python_bin
    for (major, minor), (_, python_bin) in best_by_minor.items():
        python_shims[f"python{major}.{minor}"] = python_bin

    for name, python_bin in python_shims.items():
        _write_python_shim(BYPER_BIN_DIR / name, python_bin)
        pip_name = name.replace("python", "pip", 1)
        _write_pip_shim(BYPER_BIN_DIR / pip_name, python_bin)


def install_runtime(version_spec: str) -> tuple[str, Path]:
    """Download and install a Python runtime matching *version_spec*.

    Args:
        version_spec: e.g. ``"3.12"`` or ``"3.12.8"``

    Returns:
        ``(resolved_version, install_dir)`` — the actual version installed
        and the directory where it lives.

    Raises:
        RuntimeError: if the download or extraction fails.
    """
    from byper.__core__.utils.logger import Logger

    BYPER_PYTHONS_DIR.mkdir(parents=True, exist_ok=True)

    target = _detect_platform_target()
    url, resolved = _find_download_url(version_spec, target)
    dest_dir = get_runtime_dir(resolved)

    if is_runtime_installed(resolved):
        Logger.log(f"✅ Python {resolved} already installed at {dest_dir}", level="success")
        refresh_global_shims()
        return resolved, dest_dir

    with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
        archive_path = Path(tmp.name)

    try:
        _download_file(url, archive_path)
        _extract_tarball(archive_path, dest_dir)

        python_path = _find_python_binary(dest_dir)
        if not python_path.exists():
            raise RuntimeError(
                f"Python binary not found after extraction at {dest_dir}"
            )

        Logger.log(f"✅ Python {resolved} installed to {dest_dir}", level="success")
        refresh_global_shims()
        return resolved, dest_dir

    finally:
        if archive_path.exists():
            archive_path.unlink(missing_ok=True)


def resolve_runtime(requirement: Requirement) -> Optional[tuple[str, Path]]:
    """Find the best installed byper-managed runtime that satisfies *requirement*.

    Returns ``(version, path)`` or ``None``.
    """
    installed = list_installed_runtimes()
    best_version: Optional[tuple[int, ...]] = None
    best_key: Optional[str] = None

    for version_str, runtime_path in installed.items():
        try:
            parts = tuple(int(p) for p in version_str.split("."))
        except ValueError:
            continue

        if not is_compatible(parts, requirement):
            continue

        if best_version is None or parts > best_version:
            best_version = parts
            best_key = version_str

    if best_key is None:
        return None

    return best_key, installed[best_key]


def get_runtime_python(runtime_dir: Path) -> Path:
    """Return the path to the Python binary inside *runtime_dir*."""
    return _find_python_binary(runtime_dir)


def _find_python_binary(runtime_dir: Path) -> Path:
    """Find the python binary inside *runtime_dir*, checking both layouts."""
    if IS_WINDOWS:
        for exe in ("python.exe", "python.cmd"):
            candidate = runtime_dir / "bin" / exe
            if candidate.exists():
                return candidate
            candidate = runtime_dir / exe
            if candidate.exists():
                return candidate
        return runtime_dir / "python.exe"

    candidate = runtime_dir / "bin" / "python"
    if candidate.exists():
        return candidate
    return runtime_dir / "python"


def format_install_message(version: str, path: Path) -> str:
    """Return the post-install message with PATH instructions."""
    shims_dir = str(BYPER_BIN_DIR)

    if IS_WINDOWS:
        return (
            f"Python {version} installed.\n"
            f"\n"
            f"Global shims were created in:\n"
            f"\n"
            f"  {shims_dir}\n"
            f"\n"
            f"Add this directory to your PATH to use python{version.split('.')[0]}, "
            f"python{'.'.join(version.split('.')[:2])}, pip, etc. from anywhere.\n"
            f"\n"
            f"You can update PATH from Command Prompt with:\n"
            f"\n"
            f"  setx PATH \"%PATH%;{shims_dir}\"\n"
        )

    return (
        f"Python {version} installed.\n"
        f"\n"
        f"Global shims were created in:\n"
        f"\n"
        f"  {shims_dir}\n"
        f"\n"
        f"Add this directory to your PATH to use python{version.split('.')[0]}, "
        f"python{'.'.join(version.split('.')[:2])}, pip, etc. from anywhere:\n"
        f"\n"
        f"  export PATH=\"{shims_dir}:$PATH\"\n"
    )


def format_alternatives(version_spec: str) -> str:
    """Return a message suggesting alternative ways to install Python."""
    system = platform.system()
    lines = [
        f"To use Python {version_spec}, try one of these:",
        "",
    ]

    if system == "Darwin":
        lines.append(f"  brew install python@{version_spec}")
        lines.append(f"     https://brew.sh")
        lines.append("")
    elif system == "Linux":
        lines.append(f"  sudo apt install python{version_spec}          # Debian/Ubuntu")
        lines.append(f"  sudo dnf install python{version_spec}          # Fedora")
        lines.append(f"  sudo pacman -S python{version_spec.replace('.', '')}  # Arch")
        lines.append("")
    elif system == "Windows":
        lines.append(f"  winget install Python.Python.{version_spec.replace('.', '')}")
        lines.append(f"  pyenv install {version_spec}")
        lines.append("")

    lines.append(f"  https://www.python.org/downloads/")
    lines.append(f"  pyenv install {version_spec}")
    lines.append(f"  byper python install {version_spec}  (retry)")

    return "\n".join(lines)
