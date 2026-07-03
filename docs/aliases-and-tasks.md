# Tareas y variables de entorno

## Tareas

Son secuencias de pasos:

```yaml
tasks:
  deploy:
    - byper run test
    - { call: src.deploy.run, kwargs: { env: prod } }
    - { file: scripts/finalize.py }
```

Soporta:

- Líneas de Python arbitrarias
- `byper run <script>`
- `{ call: ruta.funcion, args: [...], kwargs: {...} }`
- `{ file: ruta/archivo.py }`

## Variables de entorno

```yaml
env:
  from_file: .env
  DEBUG: "true"
```

Se acceden con:

```python
from byper.env import DEBUG
```

También se inyectan en `os.environ`.
