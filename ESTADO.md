# Estado actual de Byper

Resumen de lo que soporta, lo que está roto/parcial y lo que falta.

## Soportado

- Manifesto `requirements.yaml` YAML con `scripts`, `aliases`, `tasks`, `env`, `dependencies` y campo opcional `python`.
- Creación y uso de venv local `packages/`.
- Instalación de dependencias desde `requirements.yaml` y desde `byper.lock`.
- Añadir/eliminar/listar paquetes con resolución de versión desde PyPI.
- Ejecutar scripts, tareas y archivos `.py` dentro del entorno local.
- Sistema de aliases dinámicos (`from byper.aliases import ...`).
- Sistema de env dinámico (`from byper.env import ...`) con soporte `.env`.
- Inicialización de proyectos (`byper init`) con `-y` para modo no interactivo.
- Árbol de directorios (`byper tree`).
- Build (`byper build`) y publicación PyPI (`byper publish`, `login`, `logout`) usando el Python del proyecto.
- Diagnóstico básico (`byper doctor`) inspeccionando el environment local, incluyendo requisito y versión de Python.
- Comando `byper cache <list|clear|dir>`.
- Comando `byper wheel`.
- Soporte básico de versión de Python (`python: "3.12"` / `python: "3.12.4"`) con detección de intérpretes instalados y validación del environment existente.
- Lockfile oficial `byper.lock` en el root del proyecto, con sección `python` (`required`, `resolved`, `implementation`).
- Suite de tests automatizados en `apps/python/byper/tests/`.

## Cambios recientes (estabilización)

- Se centralizó la ejecución del environment local en `byper/__core__/project_env.py`.
- Todos los comandos de proyecto usan `packages/bin/python` en lugar del Python global.
- `byper add` ya no reinstala todo desde `requirements.yaml`; instala solo el paquete nuevo.
- Se corrigió el lockfile para usar siempre la clave `packages`.
- Se renombró el lockfile oficial a `byper.lock` y se centralizó su ruta con `LOCKFILE_NAME` / `get_lockfile_path()`.
- Se implementó `byper cache` con acciones `list`, `clear` y `dir`.
- Se corrigió `byper wheel` para pasar argumentos válidos a subprocess.
- Se corrigió el dispatch de tareas (`byper task`) y pasos `{ file: ... }` / `{ call: ... }`.
- `byper build` y `byper publish` detectan si faltan `build`/`twine` y muestran mensajes claros.
- Se agregó soporte de versión de Python en `requirements.yaml` (`python: "3.12"` / `python: "3.12.4"`).
- Se detectan intérpretes compatibles instalados y se valida que `packages/` use la versión requerida antes de ejecutar comandos.
- `byper.lock` ahora registra `python.required`, `python.resolved` y `python.implementation`.
- `byper doctor` reporta requisito, versión, implementación y estado de Python.

## Pendiente / mejoras futuras

- Descarga/instalación automática de Python cuando no se encuentre un intérprete compatible.
- Rangos de versión de Python más expresivos (`>=3.12,<3.13`).
- Mejor manejo de errores de red y resolución de versiones.
- Soporte offline con wheel cache.
- Tests de rendimiento para proyectos con muchas dependencias.
- Documentación de usuario final más detallada.
