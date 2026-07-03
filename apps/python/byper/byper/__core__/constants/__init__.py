from pathlib import Path


ENVIRONMENT_DIRECTORY = "packages"
REQUIREMENTS_FILE = "requirements.yaml"
LOCKFILE_NAME = "byper.lock"
VERSION = "1.0.0"


def get_lockfile_path(project_root: Path | str) -> Path:
    """Return the absolute path to the project's lockfile."""
    return Path(project_root).resolve() / LOCKFILE_NAME
