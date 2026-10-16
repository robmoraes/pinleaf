# Panel creation menu — execution 2026-10-11

Outcome: NEW-01..05 and AC-01..05 implemented and verified locally. Baseline
commit: `961bccd`; production change is confined to MainWindow's creation
controls. The existing action popover dismisses before invoking New Note or
the existing New Group dialog. No persistent creation mode was introduced.

## Verification

Environment: Python 3.12.3, SQLite 3.45.1, GTK 4.14.5. GTK and native checks use
an off-screen nested X11 display and private D-Bus session with synthetic data.

```bash
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 -m unittest discover -s tests -p test_panel_creation_menu.py
PINLEAF_QA_SCREENSHOTS=/tmp/pinleaf-new-menu-evidence /usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_creation_menu.py
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 -m unittest discover -s tests
/usr/bin/python3 -m compileall -q pinleaf tests
git diff --check
```

- Focused menu integration: two tests passed. Opening/dismissing writes nothing;
  note creation targets Shared or the current project; group cancellation,
  reserved/duplicate-name errors, retry and Create and activate retain behavior.
- Complete suite: **188 tests passed**, 6.070 seconds, with GTK checks enabled.
- Compilation and whitespace checks: passed.
- Native app: Enter opens New; Escape closes it, restores focus and writes
  nothing. Enter selects New Note; Tab/Enter reaches New Group. Group-name
  entry receives focus; Escape cancels without creating a group or switching
  context. Successful group creation activates it, retains Shared's editor,
  and subsequent New Note opens in that group. The menu always retains both
  actions. The body no longer contains the separate group-creation button.
- Narrow dark layout: long context/group titles remain readable or truncated,
  both menu actions remain reachable, and the body gains note-list space.
- All native test helpers were stopped and reaped, IPC sockets removed and
  temporary libraries removed. See [native result](artifacts/native-result.json).

## Visual review

Both panel and popup surfaces were captured and inspected. A popup is a separate
native surface, so menu screenshots are intentionally separate from the panel.

- [Light panel](artifacts/panel-light.png)
- [Light New menu](artifacts/menu-light.png)
- [Narrow dark panel](artifacts/panel-narrow-dark.png)
- [Dark New menu](artifacts/menu-dark.png)

Nested X11 emits existing nonfatal DRI3 warnings. The private-bus GTK3 tray
helper reports the absent accessibility service when GTK accessibility is
intentionally disabled in this harness. Assertions and cleanup passed.
Wayland and human screen-reader usability were not requalified for this UI slice.

## Delivery boundary

Spec, plan, maintained cases, tasks, README and Unreleased are updated. The
package now has Shared and the New menu complete; remote save/restore remains
to be specified. Version **0.8.0** and schema **6** remain unchanged. Delivery
is a local commit on `feat/shared-groups-and-remote-backup`. No push, remote PR
edit, hosted pipeline, tag, merge or release was performed for this slice,
following the maintainer's instruction to assemble the larger package first.
