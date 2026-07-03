import os
import subprocess
import sys
from pathlib import Path

BYPER_ROOT = Path(__file__).parent.parent.resolve()


def run_byper(
    *args,
    cwd: Path,
    env: dict | None = None,
    check: bool = True,
    input: str | None = None,
) -> subprocess.CompletedProcess:
    """Run the byper CLI from source using the current Python interpreter."""
    full_env = (env or os.environ).copy()
    existing = full_env.get("PYTHONPATH", "")
    full_env["PYTHONPATH"] = f"{BYPER_ROOT}{os.pathsep}{existing}" if existing else str(BYPER_ROOT)

    return subprocess.run(
        [sys.executable, "-m", "byper"] + list(args),
        cwd=cwd,
        env=full_env,
        text=True,
        capture_output=True,
        input=input,
        check=check,
    )
