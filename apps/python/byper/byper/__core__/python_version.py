import re
import shutil
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"

Requirement = list[tuple[str, tuple[int, ...]]]


def _parse_version_parts(version_str: str) -> tuple[int, ...]:
    """Parse a simple version string like '3.12' or '3.12.4' into a tuple."""
    if not version_str:
        raise ValueError("Empty Python version string")

    parts = [part.strip() for part in str(version_str).split(".")]
    if not parts:
        raise ValueError(f"Invalid Python version string: {version_str!r}")

    try:
        ints = tuple(int(part) for part in parts if part != "")
    except ValueError as exc:
        raise ValueError(f"Invalid Python version string: {version_str!r}") from exc

    if len(ints) < 1:
        raise ValueError(f"Invalid Python version string: {version_str!r}")

    return ints


def _compare_versions(a: tuple[int, ...], b: tuple[int, ...]) -> int:
    """Compare two version tuples. Returns -1, 0, or 1."""
    max_len = max(len(a), len(b))
    a_padded = a + (0,) * (max_len - len(a))
    b_padded = b + (0,) * (max_len - len(b))
    if a_padded < b_padded:
        return -1
    elif a_padded > b_padded:
        return 1
    return 0


def parse_version_string(version_str: str) -> Requirement:
    """Parse a Python version requirement string.

    Supports both simple and constraint-based formats:

        ``"3.12"``        → ``>=3.12,<3.13``  (any 3.12.x)
        ``"3.12.4"``      → ``==3.12.4``       (exact)
        ``">=3.12,<3.13"``→ both constraints
        ``">=3.12"``      → minimum version
        ``"<3.13"``       → maximum version
        ``"^3.12"``       → ``>=3.12,<3.13``  (compatible release)
        ``"~3.12.4"``     → ``>=3.12.4,<3.13`` (tilde range)
    """
    version_str = str(version_str).strip()
    if not version_str:
        raise ValueError("Empty Python version string")

    # Caret range: ^3.12 → >=3.12,<3.13
    if version_str.startswith("^"):
        ver = _parse_version_parts(version_str[1:])
        if len(ver) == 1:
            return [(">=", ver), ("<", (ver[0] + 1,))]
        elif len(ver) == 2:
            return [(">=", ver), ("<", (ver[0], ver[1] + 1))]
        else:
            return [(">=", ver), ("<", (ver[0], ver[1] + 1))]

    # Tilde range: ~3.12.4 → >=3.12.4,<3.13
    if version_str.startswith("~"):
        ver = _parse_version_parts(version_str[1:])
        return [(">=", ver), ("<", (ver[0], ver[1] + 1))]

    # Constraint-based format: >=3.12,<3.13 or >=3.12
    if any(op in version_str for op in (">=", "<=", "!=", "==", ">", "<")):
        constraints: Requirement = []
        parts = [p.strip() for p in version_str.split(",") if p.strip()]

        for part in parts:
            match = re.match(r"(>=|<=|!=|==|>|<)\s*(.*)", part)
            if not match:
                raise ValueError(f"Invalid version constraint: {part!r}")
            op = match.group(1)
            ver_str = match.group(2).strip()
            if not ver_str:
                raise ValueError(f"Invalid version constraint: {part!r}")
            ver = _parse_version_parts(ver_str)
            constraints.append((op, ver))

        if not constraints:
            raise ValueError(f"Invalid version requirement: {version_str!r}")
        return constraints

    # Simple format: "3.12" or "3.12.4"
    ver = _parse_version_parts(version_str)

    if len(ver) >= 3:
        return [("==", ver)]
    return [(">=", ver), ("<", (ver[0], ver[1] + 1))]


def format_version(version_info: tuple[int, ...]) -> str:
    """Format a version tuple as 'major.minor.patch'."""
    return ".".join(str(part) for part in version_info)


def describe_requirement(requirement: Requirement) -> str:
    """Return a human-readable description of a Python requirement."""
    if len(requirement) == 1:
        op, ver = requirement[0]
        return f"{op}{format_version(ver)}"
    parts = [f"{op}{format_version(ver)}" for op, ver in requirement]
    return ", ".join(parts)


def get_python_version_info(executable: list[str]) -> tuple[tuple[int, int, int], str] | None:
    """Return ((major, minor, patch), implementation) for a Python executable.

    The executable argument must be a list such as ['python3.12'] or
    ['py', '-3.12'] so that Windows ``py`` launcher invocations work.
    """
    code = (
        "import sys, platform; "
        "print('.'.join(str(v) for v in sys.version_info[:3])); "
        "print(platform.python_implementation())"
    )
    try:
        result = subprocess.run(
            executable + ["-c", code],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return None

    try:
        version_parts = tuple(int(part) for part in lines[0].split(".") if part != "")
    except ValueError:
        return None

    if len(version_parts) < 2:
        return None

    # Ensure we always return a (major, minor, patch) tuple.
    version = (version_parts[0], version_parts[1], version_parts[2] if len(version_parts) > 2 else 0)
    return version, lines[1]


def is_compatible(installed: tuple[int, int, int], requirement: Requirement) -> bool:
    """Check whether an installed Python satisfies all constraints.

    Constraints may include: ``>=``, ``>``, ``<=``, ``<``, ``==``, ``!=``.
    """
    for op, ver in requirement:
        cmp = _compare_versions(installed, ver)
        if op == ">=" and cmp < 0:
            return False
        if op == ">" and cmp <= 0:
            return False
        if op == "<=" and cmp > 0:
            return False
        if op == "<" and cmp >= 0:
            return False
        if op == "==" and cmp != 0:
            return False
        if op == "!=" and cmp == 0:
            return False
    return True


def _candidate_commands() -> list[list[str]]:
    """Return the list of Python executables to probe, in priority order."""
    candidates: list[list[str]] = []

    # Prefer the interpreter currently running byper when it is compatible.
    if sys.executable:
        candidates.append([sys.executable])

    if IS_WINDOWS:
        for version in ("3.13", "3.12", "3.11", "3.10"):
            candidates.append(["py", f"-{version}"])
        for name in ("python", "python3"):
            candidates.append([name])
    else:
        for version in ("3.13", "3.12", "3.11", "3.10"):
            candidates.append([f"python{version}"])
        for name in ("python3", "python"):
            candidates.append([name])

    return candidates


def list_installed_pythons() -> list[tuple[list[str], tuple[int, int, int], str]]:
    """List candidate Python executables that actually run on this machine."""
    found: list[tuple[list[str], tuple[int, int, int], str]] = []
    seen_paths: set[str] = set()

    for cmd in _candidate_commands():
        executable_name = cmd[0]
        executable_path = shutil.which(executable_name)
        if not executable_path:
            continue

        # Avoid reporting the exact same binary multiple times.
        lookup_key = f"{executable_path} {' '.join(cmd[1:])}" if len(cmd) > 1 else executable_path
        if lookup_key in seen_paths:
            continue
        seen_paths.add(lookup_key)

        info = get_python_version_info(cmd)
        if info is None:
            continue

        found.append((cmd, info[0], info[1]))

    return found


def format_no_compatible_python(
    requirement: Requirement,
    found: list[tuple[list[str], tuple[int, int, int], str]],
) -> str:
    """Format the error shown when no compatible Python is found."""
    lines = [
        f"This project requires Python {describe_requirement(requirement)}, "
        "but no compatible Python was found.",
        "",
        "Found:",
    ]

    if not found:
        lines.append("- (no Python executables were found)")
    else:
        for cmd, version_info, _impl in found:
            executable_path = shutil.which(cmd[0]) or " ".join(cmd)
            lines.append(f"- Python {format_version(version_info)} at {executable_path}")

    lines.extend([
        "",
        f"Install a compatible Python and run:",
        "  byper install",
    ])

    return "\n".join(lines)


class PythonNotFoundError(Exception):
    """Raised when no compatible Python interpreter is available."""

    def __init__(
        self,
        requirement: Requirement,
        found: list[tuple[list[str], tuple[int, int, int], str]],
    ):
        self.requirement = requirement
        self.found = found
        super().__init__(format_no_compatible_python(requirement, found))


def find_compatible_python(
    requirement: Requirement,
) -> tuple[list[str], tuple[int, int, int], str]:
    """Find a Python executable that satisfies all constraints.

    Returns a tuple of (executable_args, version_info, implementation).
    Raises ``PythonNotFoundError`` if no compatible interpreter is found.
    """
    for cmd, version_info, impl in list_installed_pythons():
        if is_compatible(version_info, requirement):
            return cmd, version_info, impl

    raise PythonNotFoundError(requirement, list_installed_pythons())
