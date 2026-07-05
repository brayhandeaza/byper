# Byper Current State

Byper is an **environment/project workflow manager** for Python. It uses `venv` to create a local `packages/` environment, `pip` to install dependencies, and `requirements.yaml` as a manifest.

---

## Implementation Checklist

### Project management

- [x] `byper init [name] [-y]` — initialize project (interactive wizard or non-interactive)
- [x] `byper install [--offline]` — install dependencies from `requirements.yaml` or lockfile
- [x] `byper install [packages] [--upgrade] [--no-cache] [--offline]` — install dependencies or specific packages
- [x] `byper remove <pkg>` — remove package
- [x] `byper list [--outdated | --freeze | --cache]` — list packages
- [x] `byper tree` — directory tree hiding `packages/`
- [x] `byper reset [-y]` — rebuild `packages/` from scratch
- [x] `byper path` — show project paths
- [x] `byper <archivo.py>` — execute Python file with the local environment

### Scripts and tasks

- [x] `byper run <script>` — execute script from the manifest
- [x] `byper task <name>` — execute task (sequence of steps)
- [x] Steps `{ file: ruta.py }` — execute Python file
- [x] Steps `{ call: modulo.func, args: [...], kwargs: {...} }` — call function

### Environment and variables

- [x] `byper env` — environment variables from `requirements.yaml`
- [x] `from byper.env import DEBUG` — dynamic variable import
- [x] Support `from_file: .env` — load from `.env` file
- [x] Automatic injection into `os.environ`
- [x] `byper refresh` — regenerate `.pyi` stubs for tasks/env

### Python version
- [x] `python` field in `requirements.yaml` with simple format: `"3.12"`, `"3.12.4"`
- [x] Comparison operators: `>=3.12,<3.13`, `>=3.12`, `<3.13`, etc.
- [x] Caret (`^3.12`) and tilde (`~3.12.4`)
- [x] Validation of existing environment compatibility
- [x] `byper python` — show project version info
- [x] `byper python install <version>` — download and install Python runtime from python-build-standalone
- [x] `byper python use <version>` — configure `python: "<version>"` in `requirements.yaml`
- [x] `byper python list` — list Python runtimes installed by Byper in `~/.byper/pythons/`
- [x] Automatic Python download when executing `byper install` without compatible interpreter (interactive prompt)
- [x] `byper doctor` — diagnosis including Python requirement and version
- [x] `byper doctor --fix` — automatically fix issues (including rebuild environment)
- [x] Lockfile registers `python.required`, `python.resolved`, `python.implementation`
- [x] MORE EXPANSIVE PYTHON VERSION RANGES

### Lockfile

- [x] `byper.lock` — YAML lockfile with keys `"name@version"` and structured metadata
- [x] Fields `name`, `version`, `source`, `resolved`, `integrity`, `direct`, `group`, `dependencies`
- [x] `direct: true` for dependencies from `requirements.yaml`, `false` for transitive ones
- [x] Graph-based generation: only packages reachable from the roots
- [x] Uses `packages/bin/python` to read metadata, never the global interpreter
- [x] `packaging.utils.canonicalize_name` for name normalization
- [x] `integrity: "sha256:..."` and `resolved` URL from PyPI JSON API
- [x] Legacy lockfile detection (`{name: version_str}`) with auto-regeneration
- [x] Installation from lockfile if synced with `requirements.yaml`
- [x] `python` section with `required`, `resolved`, `implementation`

### Build and publication

- [x] `byper build` — build with `python -m build` using the project's Python
- [x] `byper publish` — upload to PyPI using twine
- [x] `byper login` / `byper logout` — manage PyPI credentials
- [x] Detection of missing `build`/`twine` with clear messages

### Cache and wheels

- [x] `byper cache <list|clear|dir>` — administer pip cache
- [x] `byper wheel <pkg>` — build wheel for a package
- [x] `PIP_DISABLE_PIP_VERSION_CHECK=1` on all internal pip calls
- [x] Explicit `--disable-pip-version-check` flag in `run_project_pip()`

### Network and resilience

- [x] `--offline` flag on `byper install`
- [x] Retries with exponential backoff when resolving versions on PyPI
- [x] Clear error messages for network failures vs package not found
- [x] `NetworkError` and `PackageNotFoundError` as explicit exceptions
- [x] OFFLINE SUPPORT WITH WHEEL CACHE — ✅ IMPLEMENTED

### Tests

- [x] Lifecycle tests (init, install, add, remove)
- [x] Lockfile tests (writing, reading, corruption)
- [x] Tests for scripts, tasks and env
- [x] Tests for build and publish
- [x] Tests for doctor, doctor --fix, reset
- [x] Tests for Python version (parsing, compatibility, constraints)
- [x] Tests for offline mode
- [x] Tests for error messages

### Documentation

- [x] `docs/manifest.md` — `requirements.yaml` format
- [x] `docs/commands.md` — all CLI commands
- [x] `docs/tasks-and-env.md` — tasks and env
- [x] `docs/development.md` — architecture for contributors
- [x] `docs/publishing.md` — build and publish
- [x] `docs/ESTADO.md` — this document

---

## Pendiente / mejoras futuras

- [x] Shims globales en `~/.byper/bin/` (python3.12, pip3.12, etc.)
- [x] Soporte Windows para descarga de runtimes
- [x] Tests de rendimiento para proyectos con muchas dependencias
- [x] Documentación de usuario final más detallada (tutorial paso a paso)

---

## Arquitectura de código

```
apps/python/byper/
├── byper/
│   ├── main.py                    # CLI entry point: dispatch de comandos
│   ├── __main__.py                # python -m byper
│   ├── __init__.py
│   ├── env/                       # Módulo dinámico byper.env
│   │   ├── __init__.py            # EnvModule singleton
│   │   ├── __init__.pyi           # Auto-generated stubs (byper refresh)
│   │   └── __module__.py          # Lógica de resolución de env vars
│   ├── tasks/                     # Módulo dinámico byper.tasks
│   │   ├── __init__.py            # TasksModule singleton
│   │   ├── __init__.pyi           # Auto-generated stubs
│   │   └── __module__.py          # Lógica de ejecución de tareas
│   ├── States/                    # Gestión de estado (IPC, backend)
│   └── __core__/                  # Núcleo del sistema
│       ├── commands.py            # Clase Commands: todos los comandos CLI
│       ├── constants/             # Nombres de archivos, versión, etc.
│       ├── environment.py         # Diagnóstico de environments
│       ├── helpers/               # Generación de stubs, carga de archivos
│       ├── installation.py        # Instalación/uninstall, resolución PyPI
│       ├── lockfile.py            # Gestión del lockfile byper.lock
│       ├── manifest.py            # Lectura/escritura de requirements.yaml
│       ├── project_env.py         # Venv local, subprocess, get_required_python
│       ├── python_runtime.py      # Descarga/instalación de Python desde python-build-standalone
│       ├── python_version.py      # Parsing de versión, compatibilidad, constraints
│       ├── tasks.py               # Ejecución de tareas
│       └── utils/
│           └── logger.py          # Logger con niveles y colores
└── tests/
    ├── helpers.py                 # run_byper() helper
    ├── conftest.py                # Fixtures (empty_project, initialized_project)
    ├── test_cli.py                # Tests de integración principales
    ├── test_python_cli.py         # Tests de versión de Python (CLI)
    ├── test_python_version.py     # Tests unitarios de version parsing
    ├── test_python_runtime.py     # Tests unitarios de download/install de Python
    └── test_project_env.py        # Tests unitarios de project_env
```

### Flujo de `byper install`

1. `main.py` → `Commands.install()`
2. Verifica `requirements.yaml` existe
3. Crea/valida `packages/` con `ensure_project_environment()`
4. Si existe `byper.lock` y está sincronizado → instala desde lockfile
5. Si no → `Installation.install_from_requirements()`
6. Cada paquete: `resolve_installable_version()` → PyPI → `run_project_pip(["install", ...])`
7. Sync lockfile con `LockfileManager.sync_lockfile()`

### Flujo de `byper install <pkg>`

1. `main.py` → `Commands.install()` con paquetes → `Installation.install()`
2. Resuelve versión en PyPI con `_fetch_pypi_releases()` (retry con backoff)
3. Instala solo el paquete nuevo (no reinstala todo)
4. Actualiza `requirements.yaml` y `byper.lock`

### Flujo de `byper refresh`

1. `main.py` → `generate_tasks_stub()` → lee tasks del manifesto → escribe `.pyi`
2. `main.py` → `generate_env_stub()` → lee env del manifesto → escribe `.pyi`
3. Los stubs van en `packages/lib/pythonX.Y/site-packages/byper/{tasks,env}/__init__.pyi`

### Resolución de versión (Python)

- `get_required_python()` en `project_env.py:21` → `parse_version_string()` en `python_version.py`
- Soporta: `"3.12"`, `"3.12.4"`, `">=3.12,<3.13"`, `"^3.12"`, `"~3.12.4"`
- `is_compatible()` compara version triplet contra lista de constraints
- `find_compatible_python()` busca intérpretes instalados + byper-managed que cumplan los constraints
- `_byper_managed_candidates()` en `python_version.py` escanea `~/.byper/pythons/`
- Si no hay intérprete compatible, `ensure_project_environment()` ofrece descarga automática

### Resolución de Python runtimes

- `byper python install <version>` → `python_runtime.install_runtime()`
- Descarga desde GitHub Releases de `astral-sh/python-build-standalone` (portable, sin dependencias)
- Detección de plataforma: `aarch64-apple-darwin`, `x86_64-unknown-linux-gnu`, etc.
- Extrae a `~/.byper/pythons/<version>/`
- `_parse_version_from_filename()` extrae la versión del nombre del asset
- `resolve_runtime()` busca el mejor runtime byper-manejado que satisfaga un requirement

### Resolución de paquetes

- `_fetch_pypi_releases()` en `installation.py` — 3 reintentos con backoff exponencial

### Formato del lockfile (`byper.lock`)

```yaml
lock_version: 1

python:
  required: ">=3.12,<3.13"
  resolved: "3.12.8"
  implementation: "CPython"

packages:
  "fastapi@0.136.1":
    name: "fastapi"
    version: "0.136.1"
    source: "pypi"
    resolved: "https://files.pythonhosted.org/.../fastapi-0.136.1-py3-none-any.whl"
    integrity: "sha256:..."
    direct: true
    group: "main"
    dependencies:
      pydantic: ">=2.0.0,<3.0.0"
```

- Keys: `"name@version"` — identifica de forma única cada paquete
- `direct: true` si viene de `requirements.yaml`, `false` si es transitiva
- `resolved` e `integrity` se obtienen de PyPI JSON API
- `dependencies` se obtienen de `importlib.metadata` (los `Requires-Dist`)
- Legacy detection: si los valores de `packages` son strings planos, se regenera automáticamente
- `NetworkError` — error de red persistente (timeout, conexión rechazada)
- `PackageNotFoundError` — PyPI devuelve 404
- `--offline` → `--no-index` a pip + skip de resolución PyPI

---

## Cambios recientes

| Fecha | Cambio |
|---|---|
| 2026-07-03 | `byper python install <v>`, `byper python use <v>`, `byper python list` |
| 2026-07-03 | Descarga automática de Python al ejecutar `byper install` sin intérprete compatible |
| 2026-07-03 | Suprimido mensaje `[notice] A new release of pip is available` (env var + flag) |
| 2026-07-03 | Removido `byper.aliases` y `byper.awaiter` |
| 2026-07-03 | Nuevo formato de lockfile: keys `name@version`, metadata por paquete |
| 2026-07-03 | Lockfile: detección legacy, `direct`/`transitive`, `integrity` sha256 |
| 2026-07-03 | Rangos de versión de Python con operadores (`>=3.12,<3.13`, `^3.12`, etc.) |
| 2026-07-03 | Reintentos con backoff y mensajes de error de red |
| 2026-07-03 | Modo offline (`--offline`) en `install` y `add` |
| Anterior | Centralización de ejecución en `project_env.py` |
| Anterior | Renombrado lockfile a `byper.lock` con clave `packages` |
| Anterior | `byper cache`, `byper wheel`, `byper doctor`, `byper python` |
| Anterior | Soporte de versión de Python en `requirements.yaml` |
| Anterior | `byper build`/`publish` con detección de `build`/`twine` |
