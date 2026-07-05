<p align="center">
  <img 
    src="https://res.cloudinary.com/brayhandeaza/image/upload/v1783294676/projects/byper/ilkowwwnvebkvwzmmmdm.png"
    alt="Byper logo" 
    style="border-radius: 100%"
    width="100px"
    height="100px"
  >
</p>

<h1 style="padding-bottom: 20px" align="center">Byper</h1>


Byper is a **Python environment and workflow manager**. Each project uses its
own local environment ( `packages/` ), a declarative manifest ( `requirements.yaml` ), 
and a reproducible lockfile ( `byper.lock` ). You don't need to activate or
deactivate environments: every byper command automatically uses your project's
Python and dependencies.

* Local environment with `venv` (`packages/`)
* Dependencies declared in `requirements.yaml`
* Lockfile with hashes and PyPI metadata
* Built-in Python version management
* Scripts, tasks, and environment variables in a single file
* Global shims in `~/.byper/bin/`

---

## Installation

Install Byper like any other Python package:

```bash
pip install byper
```

Or from source:

```bash
git clone https://github.com/brayhandeaza/byper.git
cd byper/apps/python/byper
pip install -e .
```

---

## Getting Started

### 1. Create a project

```bash
byper init my-project
```

To skip the interactive wizard and use defaults:

```bash
byper init my-project -y
```

This creates the following structure:

```
my-project/
├── requirements.yaml
├── main.py
└── packages/          # created after running byper install
```

### 2. Install dependencies

Edit `requirements.yaml` :

```yaml
name: my-project
version: 0.0.1
description: My first Byper project

python: "3.12"

dependencies:
  requests: "2.32.5"
  fastapi: "0.116.1"
```

Then install:

```bash
byper install
```

Byper will:

1. Find a compatible Python interpreter (download it if necessary).
2. Create the local environment `packages/`.
3. Install dependencies from PyPI.
4. Generate `byper.lock` with exact versions, URLs, and hashes.

### 3. Run code with the project environment

```bash
byper main.py
```

No need for `source packages/bin/activate` ; byper runs `main.py` with the
Python from `packages/` .

### 4. Add more dependencies

```bash
byper install pydantic
```

With an exact version:

```bash
byper install "pydantic==2.9.0"
```

Upgrade a package:

```bash
byper install requests --upgrade
```

Remove:

```bash
byper remove requests
```

---

## Python version management

You can pin the Python version in `requirements.yaml` :

```yaml
python: "3.12"          # any 3.12.x
python: "3.12.4"        # exact
python: ">=3.12,<3.13"  # range
python: "^3.12"         # compatible release
```

If you don't have the required version, byper can download it automatically
from `python-build-standalone` :

```bash
byper python install 3.12.8
```

List installed runtimes:

```bash
byper python list
```

Set a version for the project:

```bash
byper python use 3.12
```

This writes `python: "3.12"` to `requirements.yaml` .

### Global shims

Every time you install a runtime, byper creates shims in `~/.byper/bin/` :

```
~/.byper/bin/python
~/.byper/bin/python3
~/.byper/bin/python3.12
~/.byper/bin/python3.12.8
~/.byper/bin/pip
~/.byper/bin/pip3
~/.byper/bin/pip3.12
```

Add `~/.byper/bin` to your PATH to use these commands from anywhere.

On Unix:

```bash
export PATH="$HOME/.byper/bin:$PATH"
```

On Windows (CMD):

```cmd
setx PATH "%PATH%;%USERPROFILE%\.byper\bin"
```

---

## Scripts and tasks

Define scripts in `requirements.yaml` :

```yaml
scripts:
  start: python main.py
  test: python -m pytest
  lint: python -m ruff check .
```

Run them:

```bash
byper run start
byper run test
```

Tasks allow more elaborate step sequences:

```yaml
tasks:
  deploy:
    - byper run test
    - { call: src.deploy.run, kwargs: { env: prod } }
    - { file: scripts/finalize.py }
```

Run:

```bash
byper task deploy
```

---

## Environment variables

Declare variables inline or load them from a `.env` file:

```yaml
env:
  from_file: .env
  DEBUG: "true"
  API_URL: https://api.example.com
```

Access them from Python:

```python
from byper.env import DEBUG, API_URL
```

They are also injected automatically into `os.environ` .

Regenerate stubs so your editor recognizes them:

```bash
byper refresh
```

---

## Lockfile

`requirements.yaml` expresses the project's intent. `byper.lock` stores the
exact resolution:

```yaml
lock_version: 1

python:
  required: ">=3.12,<3.13"
  resolved: "3.12.8"
  implementation: "CPython"

packages:
  "requests@2.32.5":
    name: "requests"
    version: "2.32.5"
    source: "pypi"
    resolved: "https://files.pythonhosted.org/..."
    integrity: "sha256:..."
    direct: true
    group: "main"
    dependencies:
      charset-normalizer: ">=2.0.0,<4.0.0"
```

When `byper.lock` is in sync with `requirements.yaml` , `byper install` uses the
lockfile for a faster, reproducible install.

---

## Main commands

| Command | Description |
|---|---|
| `byper install [--offline]` | Install/update dependencies from `requirements.yaml` |
| `byper install [packages] [--upgrade] [--offline] [--no-cache]` | Install dependencies or specific packages |
| `byper remove <pkg>` | Remove a package |
| `byper run <script>` | Run a manifest script |
| `byper task <name>` | Run a manifest task |
| `byper <file.py>` | Run a Python file with the local environment |
| `byper list [--outdated \| --freeze \| --cache]` | List installed packages |
| `byper tree` | Show directory tree (hiding `packages/` ) |
| `byper reset [-y]` | Rebuild `packages/` from scratch |
| `byper doctor [--fix]` | Diagnose and repair the environment |
| `byper build` | Build the package with `python -m build` |
| `byper publish` | Upload the package to PyPI |
| `byper login` / `byper logout` | Manage PyPI credentials |
| `byper cache <list\|clear\|dir>` | Manage pip cache |
| `byper wheel <pkg>` | Build a wheel for a package |
| `byper python install <version>` | Download and install a Python runtime |
| `byper python list` | List installed runtimes |
| `byper python use <version>` | Pin the project's Python version |
| `byper refresh` | Regenerate `.pyi` stubs for tasks and env |

---

## Typical workflow

```bash
# 1. Create project
byper init my-api -y

# 2. Enter directory
cd my-api

# 3. Pick Python
byper python use 3.12

# 4. Add dependencies
byper install fastapi
byper install "uvicorn[standard]"

# 5. Write code in main.py
# ...

# 6. Run
byper run start
# or directly
byper main.py

# 7. Diagnose environment issues
byper doctor

# 8. Publish (optional)
byper build
byper publish
```

---

## Project structure

```
my-project/
├── requirements.yaml    # project manifest
├── byper.lock          # exact dependency resolution
├── packages/           # local environment (venv)
├── main.py             # entry point (optional)
├── src/                # source code
└── tests/              # tests
```

* Do not commit `packages/` to git.
* Commit `requirements.yaml` and `byper.lock` for reproducibility.

---

## Additional documentation

* `docs/manifest.md` — full `requirements.yaml` format
* `docs/commands.md` — complete command reference
* `docs/tasks-and-env.md` — tasks and environment variables
* `docs/publishing.md` — build and publish to PyPI
* `docs/development.md` — internal architecture for contributors
* `docs/ESTADO.md` — current status and roadmap

---

## Contributing

Contributions are welcome. See `docs/development.md` to understand the codebase
and how to run the tests.

```bash
cd apps/python/byper
python -m pytest
```

Performance tests ( `pytest -m performance` ) require network access and are not
run by default.
