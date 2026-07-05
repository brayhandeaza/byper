# Manifest Format of `requirements.yaml`

The `requirements.yaml` file is the YAML project manifest.

```yaml
name: my-project
version: 0.0.1
description: Optional description
entry: main.py
author: Your name
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

## Supported fields

- `name`, `version`, `description`, `entry`, `author`, `license`
- `scripts`: shell commands executed with `byper run <name>`
- `tasks`: sequences of steps executed with `byper task <name>`
- `env`: environment variables inline or loaded from `from_file`
- `dependencies`: package and version (resolved against PyPI if not installed)
- `python`: Python version required. Formats:
  - `"3.12"` → `>=3.12,<3.13` (any 3.12.x)
  - `"3.12.4"` → `==3.12.4` (exact version)
  - `">=3.12,<3.13"` → range with operators
  - `">=3.12"` → minimum
  - `"<3.13"` → maximum
  - `"^3.12"` → compatible release (`>=3.12,<3.13`)
  - `"~3.12.4"` → tilde range (`>=3.12.4,<3.13`)

## Relationship with `byper.lock`

```
requirements.yaml  = project intention (what the user declares)
byper.lock         = generated exact resolution (package metadata)
packages/          = physical local environment (venv)
```

The lockfile uses a structured format with keys `"name@version"` and includes
`source`, `resolved`, `integrity`, `direct`, `group`, and `dependencies`
for each package. See `docs/ESTADO.md` for details.
