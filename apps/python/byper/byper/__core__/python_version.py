import shutil
import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"


def parse_version_string(version_str: str) -> tuple[int, ...]:
    """Parse a simple Python version string such as '3.12' or '3.12.4'."""
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


def format_version(version_info: tuple[int, ...]) -> str:
    """Format a version tuple as 'major.minor.patch'."""
    return ".".join(str(part) for part in version_info)


def describe_requirement(required: tuple[int, ...]) -> str:
    """Return a human-readable description of a Python requirement."""
    if len(required) >= 3:
        return format_version(required)
    return f"{required[0]}.{required[1]}.x" if len(required) == 2 else format_version(required)


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


def is_compatible(installed: tuple[int, int, int], required: tuple[int, ...]) -> bool:
    """Check whether an installed Python satisfies a simple requirement.

    * ``3.12`` matches any ``3.12.x``.
    * ``3.12.4`` matches exactly ``3.12.4``.
    """
    if len(required) >= 3:
        return installed[:3] == required[:3]
    return installed[: len(required)] == required[: len(required)]


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


def format_no_compatible_python(required: tuple[int, ...], found: list[tuple[list[str], tuple[int, int, int], str]]) -> str:
    """Format the error shown when no compatible Python is found."""
    lines = [
        f"This project requires Python {describe_requirement(required)}, but no compatible Python was found.",
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
        f"Install Python {describe_requirement(required)} and run:",
        "  byper install",
    ])

    return "\n".join(lines)


class PythonNotFoundError(Exception):
    """Raised when no compatible Python interpreter is available."""

    def __init__(self, required: tuple[int, ...], found: list[tuple[list[str], tuple[int, int, int], str]]):
        self.required = required
        self.found = found
        super().__init__(format_no_compatible_python(required, found))


def find_compatible_python(required: tuple[int, ...]) -> tuple[list[str], tuple[int, int, int], str]:
    """Find a Python executable that satisfies the given requirement.

    Returns a tuple of (executable_args, version_info, implementation).
    Raises ``PythonNotFoundError`` if no compatible interpreter is found.
    """
    for cmd, version_info, impl in list_installed_pythons():
        if is_compatible(version_info, required):
            return cmd, version_info, impl

    raise PythonNotFoundError(required, list_installed_pythons())
