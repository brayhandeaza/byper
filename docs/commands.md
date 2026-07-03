# Comandos del CLI

| Comando | Descripción |
|---|---|
| `byper` | Instala las dependencias del `requirements.yaml` actual |
| `byper install` | Igual que arriba; usa `Lockfile` si está sincronizado |
| `byper init [nombre] [-y]` | Crea un proyecto nuevo |
| `byper add <pkg> [--upgrade] [--no-cache]` | Añade/instala un paquete |
| `byper remove <pkg>` | Elimina un paquete |
| `byper run <script>` | Ejecuta un script del manifesto |
| `byper task <nombre>` | Ejecuta una tarea del manifesto |
| `byper <archivo.py>` | Ejecuta un archivo Python con el entorno `packages/` |
| `byper refresh` | Regenera stubs `.pyi` de tareas/env |
| `byper build` | Compila el paquete con `python -m build` (usa `packages/bin/python`) |
| `byper publish` | Sube a PyPI usando twine y `~/.pypirc` |
| `byper login` | Guarda token de PyPI en `~/.pypirc` |
| `byper logout` | Borra `~/.pypirc` |
| `byper list [--outdated \| --freeze \| --cache]` | Lista paquetes instalados en `packages/` |
| `byper cache <list\|clear\|dir>` | Administra la caché de pip |
| `byper wheel <pkg>` | Construye una wheel para un paquete |
| `byper doctor` | Diagnóstico del entorno |
| `byper tree` | Muestra árbol de directorios ocultando `packages/` |
| `byper --u-all` | Actualiza todos los paquetes obsoletos |
| `byper -v`, `byper -h` | Versión y ayuda |

Todas las operaciones de proyecto usan el venv local `packages/` y su Python (`packages/bin/python`), nunca el Python global del PATH.
