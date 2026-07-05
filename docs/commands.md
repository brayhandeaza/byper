# CLI Commands

| Comando | Descripción |
|---|---|
| `byper` | Install the current `requirements.yaml` dependencies |
| `byper install [--offline]` | Same as above; uses `Lockfile` if synced. `--offline` installs only from local cache |
| `byper init [nombre] [-y]` | Creates a new project |
| `byper install [packages] [--offline] [--upgrade] [--no-cache]` | Installs dependencies from `requirements.yaml` or specified packages |
| `byper remove <pkg>` | Removes a package |
| `byper run <script>` | Executes a script from the manifesto |
| `byper task <nombre>` | Executes a task from the manifesto |
| `byper <archivo.py>` | Executes a Python file with the `packages/` environment |
| `byper refresh` | Regenerate `.pyi` stubs for tasks/env |
| `byper build` | Builds the package with `python -m build` (uses `packages/bin/python`) |
| `byper publish` | Uploads to PyPI using twine and `~/.pypirc` |
| `byper login` | Saves PyPI token to `~/.pypirc` |
| `byper logout` | Deletes `~/.pypirc` |
| `byper list [--outdated \| --freeze \| --cache]` | Lists packages installed in `packages/` |
| `byper cache <list\|clear\|dir>` | Administers the pip cache |
| `byper wheel <pkg>` | Builds a wheel for a package |
| `byper doctor` | Diagnoses the environment |
| `byper tree` | Shows directory tree while hiding `packages/` |
| `byper --u-all` | Updates all outdated packages |
| `byper -v`, `byper -h` | Version and help |

All project operations use the local `packages/` venv and its Python (`packages/bin/python`), never the global Python from PATH.
