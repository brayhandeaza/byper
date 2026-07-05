# Tasks and Environment Variables

## Tasks

They are sequences of steps:

```yaml
tasks:
  deploy:
    - byper run test
    - { call: src.deploy.run, kwargs: { env: prod } }
    - { file: scripts/finalize.py }
```

Supports:

- Lines of arbitrary Python
- `byper run <script>`
- `{ call: module.function, args: [...], kwargs: {...} }`
- `{ file: path/to/file.py }`

## Environment Variables

```yaml
env:
  from_file: .env
  DEBUG: "true"
```

They are accessed with:

```python
from byper.env import DEBUG
```

They are also injected into `os.environ`.
