# Estado actual de Byper

Byper es un **environment/project workflow manager** para Python. Usa `venv` para crear un environment local `packages/`, `pip` para instalar dependencias, y `requirements.yaml` como manifesto.

---

## Checklist de implementación

### Gestión de proyecto

- [x] `byper init [name] [-y]` — inicializar proyecto (wizard interactivo o no)
- [x] `byper install [--offline]` — instalar dependencias desde `requirements.yaml` o lockfile
- [x] `byper add <pkg> [--upgrade] [--no-cache] [--offline]` — añadir paquete
- [x] `byper remove <pkg>` — eliminar paquete
- [x] `byper list [--outdated | --freeze | --cache]` — listar paquetes
- [x] `byper tree` — árbol de directorios (oculta `packages/`)
- [x] `byper reset [-y]` — reconstruir `packages/` desde cero
- [x] `byper path` — mostrar rutas del proyecto
- [x] `byper <archivo.py>` — ejecutar archivo Python con el environment local

### Scripts y tareas

- [x] `byper run <script>` — ejecutar script del manifesto
- [x] `byper task <name>` — ejecutar tarea (secuencia de pasos)
- [x] Pasos `{ file: ruta.py }` — ejecutar archivo Python
- [x] Pasos `{ call: modulo.func, args: [...], kwargs: {...} }` — llamar función

### Environment y variables

- [x] `byper env` — variables de entorno desde `requirements.yaml`
- [x] `from byper.env import DEBUG` — import dinámico de variables
- [x] Soporte `from_file: .env` — carga desde archivo `.env`
- [x] Inyección automática en `os.environ`
- [x] `byper refresh` — regenerar stubs `.pyi` de tasks/env

### Versión de Python

- [x] Campo `python` en `requirements.yaml` con formato simple: `"3.12"`, `"3.12.4"`
- [x] Operadores de comparación: `>=3.12,<3.13`, `>=3.12`, `<3.13`, etc.
- [x] Caret (`^3.12`) y tilde (`~3.12.4`)
- [x] Validación de compatibilidad del environment existente
- [x] `byper python` — mostrar info de versión del proyecto
- [x] `byper doctor` — diagnóstico incluyendo requisito y versión de Python
- [x] `byper doctor --fix` — reparar problemas automáticamente (incl. reconstruir env)
- [x] Lockfile registra `python.required`, `python.resolved`, `python.implementation`
- [x] RANGOS DE VERSIÓN DE PYTHON MÁS EXPRESIVOS

### Lockfile

- [x] `byper.lock` — lockfile oficial en YAML con clave `packages`
- [x] Instalación desde lockfile si está sincronizado con `requirements.yaml`
- [x] Detección de lockfile corrupto con mensaje claro
- [x] Regeneración automática cuando el lockfile está desincronizado

### Build y publicación

- [x] `byper build` — compilar con `python -m build` usando el Python del proyecto
- [x] `byper publish` — subir a PyPI con twine
- [x] `byper login` / `byper logout` — gestionar credenciales PyPI
- [x] Detección de `build`/`twine` faltantes con mensajes claros

### Cache y wheels

- [x] `byper cache <list|clear|dir>` — administrar caché de pip
- [x] `byper wheel <pkg>` — construir wheel para un paquete

### Red y resiliencia

- [x] `--offline` flag en `byper install` y `byper add`
- [x] Reintentos con backoff exponencial al resolver versiones en PyPI
- [x] Mensajes de error claros para fallos de red vs paquete no encontrado
- [x] `NetworkError` y `PackageNotFoundError` como excepciones explícitas
- [ ] SOPORTE OFFLINE CON WHEEL CACHE — ✅ IMPLEMENTADO (parcial)

### Tests

- [x] Tests de ciclo de vida (init, install, add, remove)
- [x] Tests de lockfile (escritura, lectura, corrupción)
- [x] Tests de scripts, tareas y env
- [x] Tests de build y publish
- [x] Tests de doctor, doctor --fix, reset
- [x] Tests de versión de Python (parsing, compatibilidad, constraints)
- [x] Tests de modo offline
- [x] Tests de mensajes de error

### Documentación

- [x] `docs/manifest.md` — formato de `requirements.yaml`
- [x] `docs/commands.md` — todos los comandos del CLI
- [x] `docs/aliases-and-tasks.md` — tareas y env
- [x] `docs/development.md` — arquitectura para contribuidores
- [x] `docs/publishing.md` — build y publish
- [x] `docs/ESTADO.md` — este documento

---

## Pendiente / mejoras futuras

- [ ] Descarga/instalación automática de Python cuando no se encuentre un intérprete compatible
- [ ] Tests de rendimiento para proyectos con muchas dependencias
- [ ] Documentación de usuario final más detallada (tutorial paso a paso)

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

### Flujo de `byper add <pkg>`

1. `main.py` → `Commands.add_package()` → `Installation.install()`
2. Resuelve versión en PyPI con `_fetch_pypi_releases()` (retry con backoff)
3. Instala solo el paquete nuevo (no reinstala todo)
4. Actualiza `requirements.yaml` y `byper.lock`

### Flujo de `byper refresh`

1. `main.py` → `generate_tasks_stub()` → lee tasks del manifesto → escribe `.pyi`
2. `main.py` → `generate_env_stub()` → lee env del manifesto → escribe `.pyi`
3. Los stubs van en `packages/lib/pythonX.Y/site-packages/byper/{tasks,env}/__init__.pyi`

### Resolución de versión (Python)

- `get_required_python()` en `project_env.py:18` → `parse_version_string()` en `python_version.py`
- Soporta: `"3.12"`, `"3.12.4"`, `">=3.12,<3.13"`, `"^3.12"`, `"~3.12.4"`
- `is_compatible()` compara version triplet contra lista de constraints
- `find_compatible_python()` busca intérpretes instalados que cumplan los constraints

### Resolución de paquetes

- `_fetch_pypi_releases()` en `installation.py` — 3 reintentos con backoff exponencial
- `NetworkError` — error de red persistente (timeout, conexión rechazada)
- `PackageNotFoundError` — PyPI devuelve 404
- `--offline` → `--no-index` a pip + skip de resolución PyPI

---

## Cambios recientes

| Fecha | Cambio |
|---|---|
| 2026-07-03 | Removido sistema de aliases (`byper.aliases`) |
| 2026-07-03 | Rangos de versión de Python con operadores (`>=3.12,<3.13`, `^3.12`, etc.) |
| 2026-07-03 | Reintentos con backoff y mensajes de error de red |
| 2026-07-03 | Modo offline (`--offline`) en `install` y `add` |
| Anterior | Centralización de ejecución en `project_env.py` |
| Anterior | Renombrado lockfile a `byper.lock` con clave `packages` |
| Anterior | `byper cache`, `byper wheel`, `byper doctor`, `byper python` |
| Anterior | Soporte de versión de Python en `requirements.yaml` |
| Anterior | `byper build`/`publish` con detección de `build`/`twine` |
