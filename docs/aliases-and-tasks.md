# Aliases, tareas y variables de entorno

## Aliases

Permiten importar objetos del proyecto como si fueran un módulo `byper`:

```yaml
aliases:
  utils: src.utils
  greet: src.greetings.say_hello
```

```python
from byper.aliases import utils, greet
```

Después de editar aliases, corre:

```bash
byper refresh
```

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
