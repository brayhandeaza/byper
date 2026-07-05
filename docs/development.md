# Byper Development

## What is Byper

Byper is an **environment/project workflow manager** for Python. It is not a new package manager and does not replace pip, PyPI, or Python's virtual environments. Byper is built on top of Python's existing ecosystem:

- Uses `venv` to create the project's local environment (`packages/`).
- Uses `pip` to install dependencies from PyPI.
- Uses `requirements.yaml` as a practical manifest, similar to `package.json`.
- The user does not need to manually activate the environment.
- Everything runs through the `byper` command.

## What Byper is NOT

- Does not replace `pip`.
- Does not replace `venv` / `virtualenv`.
- Does not replace PyPI.
- It is not a Python runtime of its own.

## Environments Architecture

There are two distinct environments:

1. **Environment where the Byper CLI is installed**
   - Normally the global Python or a system environment.
   - This is where the `byper` command and its dependencies (`colorama`, `requests`, `packaging`, etc.) live.

2. **Project local environment (`packages/`)**
   - Byper creates this automatically in the project root.
 - This is where the project's dependencies are installed.
 - Byper itself is also installed in editable mode in this environment so that imports like `from byper.env import ...` and `from byper.tasks import ...` work within the project.

Main architectural rule:

> All project-related commands must internally use the Python from the local environment `packages/`, never the global Python from the PATH.

## Project root detection

Byper searches for the `requirements.yaml` file by walking up from the current working directory. If found, that folder is the project root. If not, it assumes the current directory as the root.

Helpers in `byper/__core__/project_env.py`:

- `find_project_root()`
- `get_packages_dir()`
- `get_project_python()`
- `get_project_bin_dir()`

## Creation of the local environment

When `byper init` or any command that requires the environment is executed, Byper:

1. Creates a venv with `python -m venv packages/`.
2. Installs Byper in editable mode in that venv so that env/tasks imports work.

## Running Python within the project environment

All project subprocesses run with:

- `VIRTUAL_ENV` pointing to `packages/`.
- `packages/bin` (or `packages/Scripts` on Windows) at the beginning of `PATH`.
- `PYTHONPATH` includes the Byper package root.

Helpers:

- `run_project_python(args)` → runs `packages/bin/python <args>`.
- `run_project_pip(args)` → runs `packages/bin/python -m pip <args>`.
- `run_in_project(cmd)` → runs a shell command with the environment activated.

## Format of `requirements.yaml`

```yaml
name: my-project
version: 0.0.1
description: Optional description
entry: main.py
author: Your name
license: MIT

scripts:
  start: python main.py

tasks:
  deploy:
    - byper run test
    - { call: src.deploy.run, kwargs: { env: prod } }
    - { file: scripts/finalize.py }

env:
  from_file: .env
  API_URL: https://api.example.com

dependencies:
  requests: 2.32.5
```

Supported fields: `name`, `version`, `description`, `entry`, `author`, `license`, `scripts`, `tasks`, `env`, `dependencies`.

## Lockfile format

The lockfile is called `Lockfile` (no extension) and uses YAML:

```yaml
packages:
  requests: 2.32.5
  colorama: 0.4.6
```

The main key is `packages`. If it's corrupt or uses a different key, `byper install` shows a clear error.

## Flow of `byper install <pkg>`

1. Validates that the local environment exists.
2. Installs only the new package with `run_project_pip(["install", ...])`.
3. Reads the final installed version.
4. Updates `requirements.yaml`.
5. Updates `Lockfile`.
6. Respects `--upgrade` and `--no-cache`.

## Flow of `byper install`

1. If a valid `Lockfile` exists and is synced with `requirements.yaml`, install from the lockfile.
2. If no lockfile exists, install from `requirements.yaml` and generate the lockfile.
3. If the lockfile is corrupt, shows a clear error.
4. Does not reinstall packages that are already present with the correct version.

## Flow of `byper run`

1. Reads the script from `requirements.yaml`.
2. Executes the shell command with `run_in_project`, so that `python` resolves to the Python from the local environment.

## Flow of `byper task`

Supports several types of steps:

- Lines of arbitrary Python (executed in the current process).
- `byper run <script>`.
- `{ file: "path/to/file.py" }` → executes with `run_project_python`.
- `{ call: "module.function", args: [...], kwargs: {...} }` → executes the function within the project Python.

## Env

Environment variables defined in `requirements.yaml` can be imported:

```python
from byper.env import DEBUG
```

They are also injected into `os.environ`. They support loading from a `.env` file using `from_file`.

## Build / Publish

- `byper build` uses `packages/bin/python -m build`.
- `byper publish` uses `packages/bin/python -m twine upload ...`.
- If `build` or `twine` are not installed in the local environment, Byper shows a clear message indicating how to install them (`byper install build`, `byper install twine`).

## How to run tests

From the repo root or from `apps/python/byper`:

```bash
cd apps/python/byper
python -m pytest tests -v
```

Tests use temporary directories and verify that commands use the Python from the local environment (`packages/bin/python`).
