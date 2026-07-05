# Getting Started

## Install the CLI

From the repo root:

```bash
yarn make
```

Or manually:

```bash
cd apps/python/byper
pip install . --no-cache-dir
```

This installs the `byper` command into the active Python environment (it can be global).

## Create a project

```bash
mkdir my-project
cd my-project
byper init
```

This creates:

- `requirements.yaml`
- `main.py`
- `packages/` (when you install dependencies)

## Install dependencies

```bash
byper
```

or explicitly:

```bash
byper install
```

## Execute a script

Define in `requirements.yaml`:

```yaml
scripts:
  start: python main.py
```

And run:

```bash
byper run start
```
