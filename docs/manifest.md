# Formato del manifesto `requirements.yaml`

El archivo `requirements.yaml` es el manifesto YAML del proyecto.

```yaml
name: mi-proyecto
version: 0.0.1
description: Descripción opcional
entry: main.py
author: Tu nombre
license: MIT

scripts:
  start: python main.py
  test: python -m pytest

tasks:
  deploy:
    - byper run test
    - { call: src.build.run, args: ["prod"] }

env:
  from_file: .env
  API_URL: https://api.example.com

dependencies:
  requests: 2.32.5
  fastapi: 0.116.1
```

## Campos soportados

- `name`, `version`, `description`, `entry`, `author`, `license`
- `scripts`: comandos de shell que se ejecutan con `byper run <nombre>`
- `tasks`: secuencias de pasos que se ejecutan con `byper task <nombre>`
- `env`: variables de entorno inline o cargadas desde `from_file`
- `dependencies`: paquete y versión (se resuelve contra PyPI si no está instalado)
- `python`: versión de Python requerida. Formatos:
  - `"3.12"` → `>=3.12,<3.13` (cualquier 3.12.x)
  - `"3.12.4"` → `==3.12.4` (versión exacta)
  - `">=3.12,<3.13"` → rango con operadores
  - `">=3.12"` → mínimo
  - `"<3.13"` → máximo
  - `"^3.12"` → compatible release (`>=3.12,<3.13`)
  - `"~3.12.4"` → tilde range (`>=3.12.4,<3.13`)
