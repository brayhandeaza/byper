# Compilar y publicar

## Compilar

Requiere que exista el entorno `packages/`:

```bash
byper build
```

Usa `packages/bin/python -m build`.

## Publicar en PyPI

1. Configura credenciales:

```bash
byper login
```

Esto guarda el token en `~/.pypirc`.

2. Publica:

```bash
byper publish
```

`publish` usa el `python` del PATH para correr `twine`, no `packages/bin/python`.
