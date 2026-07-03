# Desarrollo de Byper

## Qué es Byper

Byper es un **environment/project workflow manager** para Python. No es un package manager nuevo ni reemplaza a pip, PyPI ni los virtual environments de Python. Byper se construye encima del ecosistema real de Python:

- Usa `venv` para crear el environment local del proyecto (`packages/`).
- Usa `pip` para instalar dependencias desde PyPI.
- Usa `requirements.yaml` como manifesto práctico, similar a `package.json`.
- El usuario no necesita activar manualmente el environment.
- Todo corre a través del comando `byper`.

## Qué NO es Byper

- No reemplaza `pip`.
- No reemplaza `venv` / `virtualenv`.
- No reemplaza PyPI.
- No es un runtime de Python propio.

## Arquitectura de environments

Hay dos environments distintos:

1. **Environment donde está instalado el CLI de Byper**
   - Normalmente es el Python global o un environment del sistema.
   - Aquí vive el comando `byper` y sus dependencias (`colorama`, `requests`, `packaging`, etc.).

2. **Environment local del proyecto (`packages/`)**
   - Byper lo crea automáticamente en la raíz del proyecto.
   - Aquí se instalan las dependencias del proyecto.
   - Aquí también se instala Byper mismo en modo editable, para que los imports `from byper.aliases import ...` y `from byper.env import ...` funcionen dentro del proyecto.

Regla arquitectónica principal:

> Todo comando relacionado al proyecto debe usar internamente el Python del environment local `packages/`, nunca el Python global del PATH.

## Detección del root del proyecto

Byper busca el archivo `requirements.yaml` subiendo desde el directorio de trabajo actual. Si lo encuentra, esa carpeta es el root del proyecto. Si no, asume el directorio actual como root.

Helpers en `byper/__core__/project_env.py`:

- `find_project_root()`
- `get_packages_dir()`
- `get_project_python()`
- `get_project_bin_dir()`

## Creación del environment local

Cuando se ejecuta `byper init` o cualquier comando que necesite el environment, Byper:

1. Crea un venv con `python -m venv packages/`.
2. Instala Byper en modo editable dentro de ese venv para que los imports de aliases/env funcionen.

## Ejecución de Python dentro del project environment

Todos los subprocess de proyecto corren con:

- `VIRTUAL_ENV` apuntando a `packages/`.
- `packages/bin` (o `packages/Scripts` en Windows) al inicio de `PATH`.
- `PYTHONPATH` incluyendo el root del paquete Byper.

Helpers:

- `run_project_python(args)` → corre `packages/bin/python <args>`.
- `run_project_pip(args)` → corre `packages/bin/python -m pip <args>`.
- `run_in_project(cmd)` → corre un comando shell con el environment activado.

## Formato de `requirements.yaml`

```yaml
name: mi-proyecto
version: 0.0.1
description: Descripción opcional
entry: main.py
author: Tu nombre
license: MIT

scripts:
  start: python main.py

aliases:
  utils: src.utils

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

Campos soportados: `name`, `version`, `description`, `entry`, `author`, `license`, `scripts`, `aliases`, `tasks`, `env`, `dependencies`.

## Formato del lockfile

El lockfile se llama `Lockfile` (sin extensión) y usa YAML:

```yaml
packages:
  requests: 2.32.5
  colorama: 0.4.6
```

La clave principal es `packages`. Si está corrupto o usa otra clave, `byper install` muestra un error claro.

## Flujo de `byper add`

1. Valida que existe el environment local.
2. Instala solo el paquete nuevo con `run_project_pip(["install", ...])`.
3. Lee la versión final instalada.
4. Actualiza `requirements.yaml`.
5. Actualiza `Lockfile`.
6. Respeta `--upgrade` y `--no-cache`.

## Flujo de `byper install`

1. Si existe `Lockfile` válido y sincronizado con `requirements.yaml`, instala desde el lockfile.
2. Si no existe lockfile, instala desde `requirements.yaml` y genera el lockfile.
3. Si el lockfile está corrupto, muestra error claro.
4. No reinstala paquetes que ya están presentes con la versión correcta.

## Flujo de `byper run`

1. Lee el script desde `requirements.yaml`.
2. Ejecuta el comando shell con `run_in_project`, de modo que `python` se resuelva al Python del environment local.

## Flujo de `byper task`

Soporta varios tipos de pasos:

- Líneas de Python arbitrarias (ejecutadas en el proceso actual).
- `byper run <script>`.
- `{ file: "ruta.py" }` → ejecuta con `run_project_python`.
- `{ call: "modulo.funcion", args: [...], kwargs: {...} }` → ejecuta la función dentro del Python del proyecto.

## Aliases

Los aliases permiten importar objetos del proyecto como si fueran parte del módulo `byper`:

```python
from byper.aliases import utils
```

Se configuran en `requirements.yaml` y se refrescan con `byper refresh`.

## Env

Las variables de entorno definidas en `requirements.yaml` pueden importarse:

```python
from byper.env import DEBUG
```

También se inyectan en `os.environ`. Soportan carga desde un archivo `.env` mediante `from_file`.

## Build / Publish

- `byper build` usa `packages/bin/python -m build`.
- `byper publish` usa `packages/bin/python -m twine upload ...`.
- Si `build` o `twine` no están instalados en el environment local, Byper muestra un mensaje claro indicando cómo instalarlos (`byper add build`, `byper add twine`).

## Cómo correr tests

Desde la raíz del repo o desde `apps/python/byper`:

```bash
cd apps/python/byper
python -m pytest tests -v
```

Los tests usan directorios temporales y verifican que los comandos usen el Python del environment local (`packages/bin/python`).
