# Shared execution record — 2026-10-11

Outcome: local Shared implementation complete and verified. The maintainer
accepted CR-02 and pre-approved plan/tasks/full implementation. No release
version or date was assigned; published metadata remains 0.8.0. The header New
menu and remote integration remain separate workstreams in spec 012.

## Environment and checks

Ubuntu 24.04 environment, Linux 6.8.0-146-generic x86_64, Python 3.12.3,
SQLite 3.45.1, GTK 4.14.5. Native lifecycle uses off-screen Xephyr, a private
D-Bus session and disposable synthetic libraries; real-compositor startup uses
the current X11 desktop with private bus and disposable data. No user note
database was opened or changed.

```bash
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 -m unittest discover -s tests
/usr/bin/python3 -m compileall -q pinleaf tests
git diff --check
/usr/bin/python3 tests/migration_recovery.py
/usr/bin/python3 tests/migration_recovery.py v0.7.0
PINLEAF_QA_SCREENSHOTS=/tmp/pinleaf-shared-evidence /usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_shared.py
/usr/bin/python3 tests/gui_session.py --a11y /usr/bin/python3 tests/gui_accessibility.py
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_benchmark.py
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_startup_benchmark.py 75
/usr/bin/python3 tests/gui_session.py --desktop /usr/bin/python3 tests/gui_startup_benchmark.py 75
/usr/bin/python3 tests/gui_session.py --desktop /usr/bin/python3 tests/gui_startup_benchmark.py 100
```

- Full isolated unittest suite: **186 passed**, 2.477 seconds, no skipped GTK cases.
- Python compilation and whitespace checks: passed.
- Schema 1–5 upgrades, exact retained note/settings preservation, in-place IDs,
  deleted containers, collisions, snapshot permissions, nullable contexts,
  repeat startup and persistent notice dismissal: passed.
- Schema-5 snapshot denial, post-conversion/version-write failures and abrupt
  process termination: original logical schema/data/context preserved.
- Existing autosave, prepare, geometry and commit-failure rollback checks pass;
  new Shared tests preserve the retained editor and pending draft on failure.
- Current-context search includes Shared plus the ordinary group uniquely,
  includes hidden notes and excludes deleted notes. Foreign Shared opening
  restores its owner's ordinary/null context; deliberate opening focuses the
  requested editor when several notes are restored.
- Native app lifecycle: Shared + and tray-action fallback, retained editor
  identity, real Ctrl+F/Escape/Enter events, hidden-note explicit opening,
  foreign-profile isolation, profile transfer to Shared, narrow dark layout
  and fresh-process restart passed. See [native result](artifacts/native-lifecycle.json).
- Private AT-SPI client: Shared label/+ action, profile selector, hidden note,
  long expanded group, scope and destination labels exported correctly in
  three phases. See [accessible result](artifacts/accessibility.json).
- Recovery drills: actual v0.8.0 schema-5 and v0.7.0 schema-4 migrators reject
  schema 6 without mutation; restoring the validated snapshot restores every
  original value. A separately preserved DB/WAL/SHM set retains one newer note.

## Performance

Uncontended nested run: 1,000 notes of 128 code points, three profiles,
three Shared and 27 ordinary groups, 250 hidden notes. Contexts contain 34 or
51 open editors; **17 Shared editor objects are reused on every switch**.
See [benchmark samples](artifacts/benchmark.json).

| Operation | Median | Maximum |
| --- | --- | --- |
| Global service search, 1,000 matches | 21.92 ms | 25.25 ms |
| Global panel construction, 1,000 matches | 616.14 ms | 635.38 ms |
| Shared + project context switch (five samples) | 349.72 ms | 573.22 ms |
| Schema-4 upgrade with private snapshot (one sample) | 9.83 ms | 9.83 ms |

Fresh-process first-idle startup with 100 short notes on the actual X11
compositor: **1,318.58 ms with 75 open** and **1,618.66 ms with all 100 open**.
These individual samples meet the inherited two-second target; they are not a
multi-run timing guarantee. See [75-open](artifacts/desktop-startup-75.json)
and [100-open](artifacts/desktop-startup-100.json) measurements. The nested
software-rendered display takes 4,120.47 ms with 75 open and 4,790.02 ms with
100 open; these results are recorded separately and are not substituted for
real desktop qualification. Timings exclude interpreter startup, fixture
creation and shutdown.

## Visual evidence and limits

Captured synthetic windows were visually inspected: Shared is first, has +,
no activation/management control, ordinary project sections retain their
controls, hidden notes are struck through, and summaries describe the resulting
ordinary context after Shared transfer. Narrow layout truncates long titles
and retains scrolling and reachable actions.

- [Normal panel](artifacts/shared-panel.png)
- [Narrow dark panel](artifacts/shared-panel-narrow-dark.png)
- [Current-context search](artifacts/shared-search.png)
- [Unchanged sticky-note surface](artifacts/shared-note.png)
- [Profile transfer confirmation](artifacts/shared-delete-profile.png)

Wayland placement and human Orca speech/usability remain unqualified, as before;
Shared adds no positioning guarantees. Nested X11 emits nonfatal DRI3 warnings.
Without an AT-SPI service, the private-bus GTK3 tray helper reports a missing
accessibility service; one desktop stress run also reported an existing GTK3
thaw-updates assertion. All asserted mapping and cleanup checks passed. The
native harness explicitly stops/reaps helpers and verifies IPC socket removal;
no Pinleaf test process/helper or nested server remains afterward.

A first harness attempted restart inside the same Python process and stalled;
the harness now validates restart in a fresh process. Its disposable app/helper
were terminated and its stale socket removed. This was a QA harness issue,
not a data migration or product failure.

Implementation commit: `9d1bf0c` on `feat/shared-groups-and-remote-backup`,
published in [draft PR #28](https://github.com/robmoraes/pinleaf/pull/28).
The PR remains draft for the larger package's remaining decisions; the Shared
slice and its local validation are complete. All [tasks](tasks.md) are checked.
The larger package remains unreleased; no merge, release or tag was performed.
