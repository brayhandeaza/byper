import sys

import pytest
import yaml

from byper.__core__.python_version import (
    PythonNotFoundError,
    Requirement,
    describe_requirement,
    find_compatible_python,
    format_version,
    get_python_version_info,
    is_compatible,
    list_installed_pythons,
    parse_version_string,
)


# ---------------------------------------------------------------------------
# parse_version_string — simple formats (backward compatible)
# ---------------------------------------------------------------------------

def test_parse_version_string_major_minor():
    assert parse_version_string("3.12") == [(">=", (3, 12)), ("<", (3, 13))]


def test_parse_version_string_exact():
    assert parse_version_string("3.12.4") == [("==", (3, 12, 4))]


def test_parse_version_string_rejects_invalid():
    with pytest.raises(ValueError):
        parse_version_string("abc")


# ---------------------------------------------------------------------------
# parse_version_string — constraint formats
# ---------------------------------------------------------------------------

def test_parse_constraint_gte():
    assert parse_version_string(">=3.12") == [(">=", (3, 12))]


def test_parse_constraint_gt():
    assert parse_version_string(">3.11") == [(">", (3, 11))]


def test_parse_constraint_lt():
    assert parse_version_string("<3.13") == [("<", (3, 13))]


def test_parse_constraint_lte():
    assert parse_version_string("<=3.12.4") == [("<=", (3, 12, 4))]


def test_parse_constraint_eq():
    assert parse_version_string("==3.12.4") == [("==", (3, 12, 4))]


def test_parse_constraint_neq():
    assert parse_version_string("!=3.12.4") == [("!=", (3, 12, 4))]


def test_parse_constraint_range():
    assert parse_version_string(">=3.12,<3.13") == [
        (">=", (3, 12)),
        ("<", (3, 13)),
    ]


def test_parse_constraint_range_with_spaces():
    assert parse_version_string(">=3.12, <3.13") == [
        (">=", (3, 12)),
        ("<", (3, 13)),
    ]


def test_parse_constraint_caret():
    assert parse_version_string("^3.12") == [(">=", (3, 12)), ("<", (3, 13))]


def test_parse_constraint_caret_major():
    assert parse_version_string("^3") == [(">=", (3,)), ("<", (4,))]


def test_parse_constraint_tilde():
    assert parse_version_string("~3.12.4") == [(">=", (3, 12, 4)), ("<", (3, 13))]


def test_parse_constraint_rejects_malformed():
    with pytest.raises(ValueError):
        parse_version_string(">=3.12, <")

    with pytest.raises(ValueError):
        parse_version_string(">>3.12")


# ---------------------------------------------------------------------------
# describe_requirement
# ---------------------------------------------------------------------------

def test_describe_requirement_major_minor():
    assert describe_requirement([(">=", (3, 12)), ("<", (3, 13))]) == ">=3.12, <3.13"


def test_describe_requirement_exact():
    assert describe_requirement([("==", (3, 12, 4))]) == "==3.12.4"


def test_describe_requirement_gte():
    assert describe_requirement([(">=", (3, 12))]) == ">=3.12"


# ---------------------------------------------------------------------------
# is_compatible
# ---------------------------------------------------------------------------

def test_is_compatible_major_minor():
    req = parse_version_string("3.12")
    assert is_compatible((3, 12, 8), req) is True
    assert is_compatible((3, 12, 0), req) is True
    assert is_compatible((3, 13, 0), req) is False
    assert is_compatible((3, 11, 9), req) is False


def test_is_compatible_exact():
    req = parse_version_string("3.12.4")
    assert is_compatible((3, 12, 4), req) is True
    assert is_compatible((3, 12, 5), req) is False
    assert is_compatible((3, 12, 3), req) is False


def test_is_compatible_gte():
    req = parse_version_string(">=3.12")
    assert is_compatible((3, 12, 0), req) is True
    assert is_compatible((3, 12, 8), req) is True
    assert is_compatible((3, 13, 0), req) is True
    assert is_compatible((3, 11, 9), req) is False


def test_is_compatible_gt():
    req = parse_version_string(">3.12")
    assert is_compatible((3, 12, 1), req) is True
    assert is_compatible((3, 13, 0), req) is True
    assert is_compatible((3, 12, 0), req) is False
    assert is_compatible((3, 11, 9), req) is False


def test_is_compatible_lt():
    req = parse_version_string("<3.13")
    assert is_compatible((3, 12, 9), req) is True
    assert is_compatible((3, 12, 0), req) is True
    assert is_compatible((3, 13, 0), req) is False
    assert is_compatible((3, 14, 0), req) is False


def test_is_compatible_lte():
    req = parse_version_string("<=3.12.4")
    assert is_compatible((3, 12, 4), req) is True
    assert is_compatible((3, 12, 3), req) is True
    assert is_compatible((3, 11, 9), req) is True
    assert is_compatible((3, 12, 5), req) is False
    assert is_compatible((3, 13, 0), req) is False


def test_is_compatible_eq():
    req = parse_version_string("==3.12.4")
    assert is_compatible((3, 12, 4), req) is True
    assert is_compatible((3, 12, 0), req) is False
    assert is_compatible((3, 12, 5), req) is False


def test_is_compatible_neq():
    req = parse_version_string("!=3.12.4")
    assert is_compatible((3, 12, 4), req) is False
    assert is_compatible((3, 12, 5), req) is True
    assert is_compatible((3, 11, 0), req) is True


def test_is_compatible_range():
    req = parse_version_string(">=3.12,<3.13")
    assert is_compatible((3, 12, 0), req) is True
    assert is_compatible((3, 12, 9), req) is True
    assert is_compatible((3, 11, 9), req) is False
    assert is_compatible((3, 13, 0), req) is False


def test_is_compatible_caret():
    req = parse_version_string("^3.12")
    assert is_compatible((3, 12, 0), req) is True
    assert is_compatible((3, 12, 9), req) is True
    assert is_compatible((3, 13, 0), req) is False
    assert is_compatible((3, 11, 9), req) is False


# ---------------------------------------------------------------------------
# format_version
# ---------------------------------------------------------------------------

def test_format_version():
    assert format_version((3, 12, 4)) == "3.12.4"
    assert format_version((3, 12)) == "3.12"


# ---------------------------------------------------------------------------
# get_python_version_info
# ---------------------------------------------------------------------------

def test_get_python_version_info_for_current_interpreter():
    info = get_python_version_info([sys.executable])
    assert info is not None
    version, impl = info
    assert version[:2] == sys.version_info[:2]
    assert impl == "CPython" or impl


# ---------------------------------------------------------------------------
# list_installed_pythons
# ---------------------------------------------------------------------------

def test_list_installed_pythons_includes_current():
    found = list_installed_pythons()
    executables = [cmd[0] for cmd, _version, _impl in found]
    assert sys.executable in executables


# ---------------------------------------------------------------------------
# find_compatible_python
# ---------------------------------------------------------------------------

def test_find_compatible_python_accepts_current_major_minor():
    current = sys.version_info
    req = parse_version_string(f">={current.major}.{current.minor}")
    cmd, version, impl = find_compatible_python(req)
    assert is_compatible(version, req)
    assert impl


def test_find_compatible_python_exact_current():
    current = sys.version_info
    req = parse_version_string(f"=={current.major}.{current.minor}.{current.micro}")
    cmd, version, impl = find_compatible_python(req)
    assert is_compatible(version, req)


def test_find_compatible_python_raises_for_unlikely_version():
    with pytest.raises(PythonNotFoundError):
        find_compatible_python(parse_version_string(">99.99"))
