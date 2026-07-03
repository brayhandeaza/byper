# Primeros pasos

## Instalar el CLI

Desde la raíz del repo:

```bash
yarn make
```

O manualmente:

```bash
cd apps/python/byper
pip install . --no-cache-dir
```

Esto instala el comando `byper` en el entorno Python activo (puede ser global).

## Crear un proyecto

```bash
mkdir mi-proyecto
cd mi-proyecto
byper init
```

Esto crea:

- `requirements.yaml`
- `main.py`
- `packages/` (cuando instales dependencias)

## Instalar dependencias

```bash
byper
```

o explícitamente:

```bash
byper install
```

## Ejecutar un script

Define en `requirements.yaml`:

```yaml
scripts:
  start: python main.py
```

Y corre:

```bash
byper run start
```
