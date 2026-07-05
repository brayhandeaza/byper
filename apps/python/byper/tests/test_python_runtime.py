import platform
import sys
from pathlib import Path
from unittest import mock

import pytest

from byper.__core__.python_runtime import (
    _compute_best_runtimes,
    _create_windows_python_cmd,
    _detect_platform_target,
    _find_python_binary,
    _make_asset_name,
    _parse_version_from_filename,
    _write_pip_shim,
    _write_python_shim,
    format_alternatives,
    format_install_message,
    get_runtime_dir,
    is_runtime_installed,
    list_installed_runtimes,
    refresh_global_shims,
    resolve_runtime,
)
from byper.__core__.python_version import parse_version_string


def test_detect_platform_target():
    target = _detect_platform_target()
    system = platform.system().lower()
    machine = platform.machine().lower()

    if sys.platform == "darwin":
        if machine == "arm64":
            assert target == "aarch64-apple-darwin"
        else:
            assert target == "x86_64-apple-darwin"
    elif sys.platform == "linux":
        if machine == "aarch64":
            assert target == "aarch64-unknown-linux-gnu"
        else:
            assert target == "x86_64-unknown-linux-gnu"


def test_make_asset_name():
    name = _make_asset_name("3.12.8", "aarch64-apple-darwin")
    assert name == "cpython-3.12.8-aarch64-apple-darwin-install_only.tar.gz"


def test_parse_version_from_filename_valid():
    filename = "cpython-3.12.8+20250101-aarch64-apple-darwin-install_only.tar.gz"
    version = _parse_version_from_filename(filename)
    assert version == "3.12.8"


def test_parse_version_from_filename_without_build():
    filename = "cpython-3.12.8-aarch64-apple-darwin-install_only.tar.gz"
    version = _parse_version_from_filename(filename)
    assert version == "3.12.8"


def test_parse_version_from_filename_invalid():
    assert _parse_version_from_filename("not-a-cpython-file.tar.gz") is None
    assert _parse_version_from_filename("") is None


def test_get_runtime_dir():
    path = get_runtime_dir("3.12.8")
    assert path.name == "3.12.8"
    assert "pythons" in str(path)


def test_is_runtime_installed_not_exists():
    assert is_runtime_installed("99.99.99") is False


def test_list_installed_runtimes_empty_when_no_runtimes(tmp_path: Path):
    with mock.patch("byper.__core__.python_runtime.BYPER_PYTHONS_DIR", tmp_path), \
         mock.patch("byper.__core__.python_runtime._link_system_pythons"):
        runtimes = list_installed_runtimes()
        assert runtimes == {}


def test_list_installed_runtimes_missing_python_binary(tmp_path: Path):
    runtime_dir = tmp_path / "3.12.8"
    runtime_dir.mkdir(parents=True)

    with mock.patch("byper.__core__.python_runtime.BYPER_PYTHONS_DIR", tmp_path), \
         mock.patch("byper.__core__.python_runtime._link_system_pythons"):
        runtimes = list_installed_runtimes()
        assert runtimes == {}


def test_resolve_runtime_none_when_no_match():
    runtimes = {"3.11.5": Path("/fake/3.11.5")}
    with mock.patch("byper.__core__.python_runtime.list_installed_runtimes", return_value=runtimes):
        requirement = parse_version_string("3.12")
        result = resolve_runtime(requirement)
        assert result is None


def test_resolve_runtime_finds_matching():
    runtimes = {
        "3.12.3": Path("/fake/3.12.3"),
        "3.12.8": Path("/fake/3.12.8"),
        "3.11.5": Path("/fake/3.11.5"),
    }
    with mock.patch("byper.__core__.python_runtime.list_installed_runtimes", return_value=runtimes):
        requirement = parse_version_string("3.12")
        result = resolve_runtime(requirement)
        assert result is not None
        assert result[0] == "3.12.8"


def test_detect_platform_target_windows_x86_64():
    with mock.patch("platform.system", return_value="Windows"), \
         mock.patch("platform.machine", return_value="AMD64"):
        assert _detect_platform_target() == "x86_64-pc-windows-msvc"


def test_detect_platform_target_windows_arm64():
    with mock.patch("platform.system", return_value="Windows"), \
         mock.patch("platform.machine", return_value="ARM64"):
        assert _detect_platform_target() == "aarch64-pc-windows-msvc"


def test_make_asset_name_windows():
    name = _make_asset_name("3.12.8", "x86_64-pc-windows-msvc")
    assert name == "cpython-3.12.8-x86_64-pc-windows-msvc-install_only.tar.gz"


def test_find_python_binary_windows_exe(tmp_path: Path):
    exe = tmp_path / "python.exe"
    exe.touch()
    with mock.patch("byper.__core__.python_runtime.IS_WINDOWS", True):
        assert _find_python_binary(tmp_path) == exe


def test_find_python_binary_windows_cmd_fallback(tmp_path: Path):
    cmd = tmp_path / "python.cmd"
    cmd.touch()
    with mock.patch("byper.__core__.python_runtime.IS_WINDOWS", True):
        assert _find_python_binary(tmp_path) == cmd


def test_find_python_binary_windows_prefers_exe(tmp_path: Path):
    exe = tmp_path / "python.exe"
    cmd = tmp_path / "python.cmd"
    exe.touch()
    cmd.touch()
    with mock.patch("byper.__core__.python_runtime.IS_WINDOWS", True):
        assert _find_python_binary(tmp_path) == exe


def test_create_windows_python_cmd(tmp_path: Path):
    target = r"C:\Program Files\Python312\python.exe"
    _create_windows_python_cmd(tmp_path, target)
    wrapper = tmp_path / "python.cmd"
    assert wrapper.exists()
    content = wrapper.read_text(encoding="utf-8")
    assert '@echo off' in content
    assert f'"{target}" %*' in content


def test_format_install_message_windows():
    path = Path("/fake/3.12.8")
    with mock.patch("byper.__core__.python_runtime.IS_WINDOWS", True):
        message = format_install_message("3.12.8", path)
    assert "Global shims" in message
    assert "setx PATH" in message


def test_format_alternatives_windows():
    with mock.patch("platform.system", return_value="Windows"):
        message = format_alternatives("3.12")
    assert "winget install Python.Python.312" in message
    assert "pyenv install 3.12" in message


def test_compute_best_runtimes(tmp_path: Path):
    runtimes = {
        "3.11.5": tmp_path / "3.11.5",
        "3.12.3": tmp_path / "3.12.3",
        "3.12.8": tmp_path / "3.12.8",
    }
    for runtime_dir in runtimes.values():
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "python").touch()

    best_overall, best_by_major, best_by_minor = _compute_best_runtimes(runtimes)

    assert best_overall[0] == (3, 12, 8)
    assert best_overall[1] == runtimes["3.12.8"] / "python"
    assert best_by_major[3][0] == (3, 12, 8)
    assert best_by_major[3][1] == runtimes["3.12.8"] / "python"
    assert best_by_minor[(3, 11)][0] == (3, 11, 5)
    assert best_by_minor[(3, 11)][1] == runtimes["3.11.5"] / "python"
    assert best_by_minor[(3, 12)][0] == (3, 12, 8)
    assert best_by_minor[(3, 12)][1] == runtimes["3.12.8"] / "python"


def test_write_python_shim_unix(tmp_path: Path):
    python_bin = tmp_path / "python"
    python_bin.touch()
    shim = tmp_path / "python3.12"
    _write_python_shim(shim, python_bin)

    assert shim.exists()
    assert shim.stat().st_mode & 0o111
    content = shim.read_text(encoding="utf-8")
    assert f'exec "{python_bin}" "$@"' in content


def test_write_pip_shim_unix(tmp_path: Path):
    python_bin = tmp_path / "python"
    python_bin.touch()
    shim = tmp_path / "pip3.12"
    _write_pip_shim(shim, python_bin)

    assert shim.exists()
    assert shim.stat().st_mode & 0o111
    content = shim.read_text(encoding="utf-8")
    assert f'exec "{python_bin}" -m pip "$@"' in content


def test_write_python_shim_windows(tmp_path: Path):
    python_bin = tmp_path / "python.exe"
    python_bin.touch()
    shim = tmp_path / "python3.12"
    with mock.patch("byper.__core__.python_runtime.IS_WINDOWS", True):
        _write_python_shim(shim, python_bin)

    cmd_shim = shim.with_suffix(".cmd")
    assert cmd_shim.exists()
    content = cmd_shim.read_text(encoding="utf-8")
    assert f'"{python_bin}" %*' in content


def test_write_pip_shim_windows(tmp_path: Path):
    python_bin = tmp_path / "python.exe"
    python_bin.touch()
    shim = tmp_path / "pip3.12"
    with mock.patch("byper.__core__.python_runtime.IS_WINDOWS", True):
        _write_pip_shim(shim, python_bin)

    cmd_shim = shim.with_suffix(".cmd")
    assert cmd_shim.exists()
    content = cmd_shim.read_text(encoding="utf-8")
    assert f'"{python_bin}" -m pip %*' in content


def test_refresh_global_shims_creates_shims(tmp_path: Path):
    runtimes = {
        "3.12.8": tmp_path / "3.12.8",
    }
    for runtime_dir in runtimes.values():
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "python").touch()

    bin_dir = tmp_path / "bin"
    with mock.patch("byper.__core__.python_runtime.list_installed_runtimes", return_value=runtimes), \
         mock.patch("byper.__core__.python_runtime.BYPER_BIN_DIR", bin_dir):
        refresh_global_shims()

    assert (bin_dir / "python").exists()
    assert (bin_dir / "python3").exists()
    assert (bin_dir / "python3.12").exists()
    assert (bin_dir / "python3.12.8").exists()
    assert (bin_dir / "pip").exists()
    assert (bin_dir / "pip3").exists()
    assert (bin_dir / "pip3.12").exists()
    assert (bin_dir / "pip3.12.8").exists()


def test_refresh_global_shims_best_prefix_wins(tmp_path: Path):
    runtimes = {
        "3.12.3": tmp_path / "3.12.3",
        "3.12.8": tmp_path / "3.12.8",
    }
    for version, runtime_dir in runtimes.items():
        runtime_dir.mkdir(parents=True)
        (runtime_dir / "python").write_text(version)

    bin_dir = tmp_path / "bin"
    with mock.patch("byper.__core__.python_runtime.list_installed_runtimes", return_value=runtimes), \
         mock.patch("byper.__core__.python_runtime.BYPER_BIN_DIR", bin_dir):
        refresh_global_shims()

    content = (bin_dir / "python3.12").read_text(encoding="utf-8")
    assert "3.12.8/python" in content
    assert "3.12.3/python" not in content


def test_format_install_message_mentions_shims():
    path = Path("/fake/3.12.8")
    message = format_install_message("3.12.8", path)
    assert "Global shims" in message
    assert "python3" in message
    assert "python3.12" in message
