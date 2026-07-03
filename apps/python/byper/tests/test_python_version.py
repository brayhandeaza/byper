import sys

import pytest
import yaml

from byper.__core__.python_version import (
    PythonNotFoundError,
    describe_requirement,
    find_compatible_python,
    format_version,
    get_python_version_info,
    is_compatible,
    list_installed_pythons,
    parse_version_string,
)


def test_parse_version_string_major_minor():
    assert parse_version_string("3.12") == (3, 12)


def test_parse_version_string_exact():
    assert parse_version_string("3.12.4") == (3, 12, 4)


def test_parse_version_string_rejects_invalid():
    with pytest.raises(ValueError):
        parse_version_string("abc")


def test_describe_requirement_major_minor():
    assert describe_requirement((3, 12)) == "3.12.x"


def test_describe_requirement_exact():
    assert describe_requirement((3, 12, 4)) == "3.12.4"


def test_is_compatible_major_minor():
    assert is_compatible((3, 12, 8), (3, 12)) is True
    assert is_compatible((3, 12, 0), (3, 12)) is True
    assert is_compatible((3, 13, 0), (3, 12)) is False


def test_is_compatible_exact():
    assert is_compatible((3, 12, 4), (3, 12, 4)) is True
    assert is_compatible((3, 12, 5), (3, 12, 4)) is False


def test_get_python_version_info_for_current_interpreter():
    info = get_python_version_info([sys.executable])
    assert info is not None
    version, impl = info
    assert version[:2] == sys.version_info[:2]
    assert impl == "CPython" or impl


def test_list_installed_pythons_includes_current():
    found = list_installed_pythons()
    executables = [cmd[0] for cmd, _version, _impl in found]
    assert sys.executable in executables


def test_find_compatible_python_accepts_current_major_minor():
    current = sys.version_info
    required = parse_version_string(f"{current.major}.{current.minor}")
    cmd, version, impl = find_compatible_python(required)
    assert is_compatible(version, required)
    assert impl


def test_find_compatible_python_exact_current():
    current = sys.version_info
    required = (current.major, current.minor, current.micro)
    cmd, version, impl = find_compatible_python(required)
    assert version == required


def test_find_compatible_python_raises_for_unlikely_version():
    with pytest.raises(PythonNotFoundError):
        find_compatible_python((99, 99))
