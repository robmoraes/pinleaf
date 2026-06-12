# Repository Guidelines

## Project Structure & Module Organization

Pinleaf is a Python GTK/libadwaita desktop app.

- `pinleaf/`: application source.
- `pinleaf/app.py`: GTK application lifecycle and dependency wiring.
- `pinleaf/ui/`: windows, dialogs, About UI, and tray controller.
- `pinleaf/storage/`: SQLite schema and repository.
- `pinleaf/services/`: note service and autosave behavior.
- `pinleaf/resources/`: CSS, bundled fonts, and icons.
- `tests/`: `unittest` suite.
- `docs/.specs/`: spec-driven development artifacts.
- `scripts/`: local install/uninstall helpers.

## Build, Test, and Development Commands

Run the app from the repository root:

```bash
/usr/bin/python3 -m pinleaf
```

Run with isolated development data:

```bash
XDG_DATA_HOME=/tmp/pinleaf-dev /usr/bin/python3 -m pinleaf
```

Run tests:

```bash
/usr/bin/python3 -m unittest discover -s tests
```

Check Python syntax/import compilation:

```bash
/usr/bin/python3 -m compileall pinleaf tests
```

Install or remove a user-local desktop launcher:

```bash
scripts/install-local
scripts/uninstall-local
```

## Coding Style & Naming Conventions

Use Python 3.11+ syntax unless system GTK bindings require `/usr/bin/python3`.
Use 4-space indentation, type hints for public helpers, and small modules with
single responsibilities. Keep GTK imports lazy or isolated where practical so
non-GUI tests remain usable. Use snake_case for functions, modules, and
variables; use PascalCase for classes.

## Testing Guidelines

Tests use the standard library `unittest` framework. Name test files
`tests/test_*.py` and test classes `*Tests`. Add focused tests for storage,
services, metadata, resources, and script behavior. GUI behavior that cannot be
reliably automated should be recorded in the relevant spec `tasks.md`.

## Commit & Pull Request Guidelines

This repository uses trunk-based development. Keep `main` releasable and use
short-lived branches such as `feat/about-help` or `fix/tray-icon`.

The current commit style is concise imperative summaries, for example:

```text
Initial Pinleaf MVP
```

Pull requests should include:

- summary of user-visible changes;
- spec path when implementing spec-driven work;
- test output, especially `unittest` and `compileall`;
- screenshots or notes for GTK UI changes;
- known limitations or follow-up work.

## Security & Configuration Tips

Do not add network calls or telemetry without a spec. Notes are local SQLite
data under XDG user data paths. Install scripts must not require `sudo` and
must not remove user note data.
