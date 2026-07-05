# Build and Publish

## Build

Requires the `packages/` environment to exist:

```bash
byper build
```

Uses `packages/bin/python -m build`.

## Publish to PyPI

1. Configure credentials:

```bash
byper login
```

This saves the token in `~/.pypirc`.

2. Publish:

```bash
byper publish
```

`publish` uses the `python` from the PATH to run `twine`, not `packages/bin/python`.
