# AGENTS.md — Byper monorepo

High-signal notes for OpenCode sessions. Trust manifests and scripts over prose; the root `README.md` is a stale pandas placeholder.

## Layout

Turborepo + Yarn 1 workspaces. `packageManager: yarn@1.22.22`. Workspaces: `apps/python/*`, `apps/docs/*`.

- `apps/python/byper` — Python CLI `byper` (entry `byper.main:cli`). A custom package manager / task runner.
- `apps/docs/web` — Docusaurus docs site.
- `apps/docs/server` — Express + Mongoose backend for package stats.
- `test/` and `apps/python/test/` — manual test/fixture projects using the `requirements.yaml` manifest format.

## Toolchain

- Node `>=18`, Yarn `1.22.22`. Both `yarn.lock` and `package-lock.json` exist; use **Yarn**.
- Root TypeScript `5.8.3`; `web` pins TypeScript `~5.6.2`.
- `web` uses Tailwind CSS v4 via `@tailwindcss/postcss` (no separate Tailwind config).
- `byper` requires Python `>=3.12`.

## Common commands

- `yarn install` — install Node deps for the workspaces.
- `yarn make` — `turbo run make --filter=byper` → `make build` in `apps/python/byper` → `pip install . --no-cache-dir` **globally**.
- `yarn start` — `turbo run start --filter=web` → Docusaurus dev server.
- `make start` — `turbo run start` (no filter; starts every package with a `start` script).

Note: `yarn dev` (`turbo run dev --filter=byper-test`) references a missing package; there is no `apps/python/test/package.json`.

## `byper` CLI specifics

- Install locally: `cd apps/python/byper && pip install . --no-cache-dir` (or `yarn make` from root).
  - `yarn make` installs the **CLI itself** into the active Python environment (often global/system pip), so the `byper` command is available everywhere.
  - Dependency installs are **not** global: byper creates a local `packages/` venv and uses `packages/bin/python -m pip ...` for `install`, `add`, `remove`, `list`, `doctor`, etc.
  - Byper installs itself into `packages/` so that `from byper.aliases import ...` and `from byper.env import ...` work inside project subprocesses.
- Core files in a byper project:
  - `requirements.yaml` — YAML manifest: name, version, entry, scripts, aliases, tasks, env, dependencies, and optional `python`.
  - `packages/` — local venv created by byper.
  - `byper.lock` — byper lock data (`lock_version`, `packages: {name: version}`, and optional `python: {required, resolved, implementation}`).
- Project root detection walks upward looking for `requirements.yaml`.
- Central environment helpers live in `byper/__core__/project_env.py` (`run_project_python`, `run_project_pip`, `run_in_project`, `build_project_env`).
- Bare `byper` (no args) or `byper install` installs dependencies from `requirements.yaml` and writes/uses `byper.lock`. Avoid running it casually in unrelated directories.
- `byper add` installs only the requested package, updates `requirements.yaml`, and updates `byper.lock`.
- `byper refresh` regenerates `.pyi` alias/task/env stubs after editing `requirements.yaml`.
- `byper build` uses `packages/bin/python -m build`; `byper publish` uses `packages/bin/python -m twine`.
  - If `build` or `twine` are missing, byper prints a clear message (`byper add build` / `byper add twine`).
- Optional `python` field in `requirements.yaml` (e.g. `python: "3.12"`) tells byper which Python version to use. It searches installed interpreters (`python3.12`, `python3`, `py -3.12`, etc.) and fails cleanly if none match. Existing `packages/` environments are validated against the requirement before running commands.
- `byper doctor` inspects the local `packages/` environment and reports the project's Python requirement status.
- `byper cache <list|clear|dir>` manages pip cache.
- `byper wheel <pkg>` builds a wheel using the project environment.
- Package resolution hits the PyPI JSON API, so most commands need internet unless you are using cached wheels.

### Tests

- Test suite: `apps/python/byper/tests/`.
- Run: `cd apps/python/byper && python -m pytest tests -v`.
- Tests create temporary Byper projects and verify that project commands use `packages/bin/python`.

### Test fixture projects

- `apps/python/test/requirements.yaml` — aliases `say_hello` to `start.say_hello`; dependencies include `torch`, `pandas`, `fastapi`, `uvicorn`. Running byper here will create a `packages/` venv and download large packages.
- `test/requirements.yaml` — smaller sample with `requests`; `test/*.whl` are cached wheels for offline-style use.

## Docs stack (`web` + `server`)

- `web`:
  - `yarn --filter=web start` — Docusaurus dev (default port 3000).
  - `yarn --filter=web build` — static build.
  - `yarn --filter=web typecheck` — `tsc`.
- `server`:
  - `yarn --filter=server start` — `nodemon index.ts`.
  - Requires `MONGODB_URL` in `.env` (loaded by `dotenv`).
  - Listens on `PORT` or `3001`; CORS is hard-coded to `http://localhost:3000`.
  - Uses `config/projects.json` as the data source and writes to MongoDB.
  - `p-limit` is imported but **not listed in `package.json`**; `nodemon`/`ts-node` are also expected to be available.

## Sensitive files

- `.pypirc` — contains a live PyPI API token. Do not edit, expose, or commit changes.
- `apps/docs/server/config/service_account.json` — Google Cloud service account key. Do not edit or expose.

## Gotchas

- Root `README.md` is unrelated pandas boilerplate; ignore it.
- `apps/python/test/` is not a Yarn/Turbo workspace (no `package.json`).
- `.gitignore` ignores `packages/`, `.env*`, build outputs, and `.turbo`.
