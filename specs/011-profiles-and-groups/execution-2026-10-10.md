# Implementation and verification execution — 2026-10-10

## Build and scope

- Executor: Codex in the maintainer's local workspace; implementation authorized
  in the conversation after Spec -> Plan -> Tasks.
- Branch: `feat/profiles-and-groups`, based on
  `23d4c92b5015b7afe785d5f18036f3e9918d5ec0`; working tree is uncommitted.
- Initial code/test/contract SHA-256: `a8735ab6b959afb7780e14a09cdf9ad300d039c088bdaae72ef7bfc0fc286181` (sorted relative Python file
  paths under `pinleaf/` and `tests/`, plus the migration JSON; hash each path,
  NUL, file bytes, NUL in that order).
- The subsequent [automated desktop qualification](automation-2026-10-10.md)
  identifies the final corrected build, 157-test regression and current timings.
- Preserved the existing local text-search/0.8.0 preparation. No commit, push,
  tag, GitHub Release or PPA publication was made.
- Python 3.12; SQLite from the system Python; GTK 4.14.5, libadwaita 1.5.0.
  Host X11; native QA also uses off-screen Xephyr with a private D-Bus session.
  All libraries and notes used for QA are temporary and synthetic.

## Delivered implementation

Required note membership and schema 5, a shared SQLite transaction owner,
private validated legacy snapshots, organization services, context/window
reconciliation, native profile/group controls, forms, scoped search and recovery
documentation are implemented. General is identified by `is_general`; the initial
profile name is stored once. Removed containers retain tombstones, and retained
deleted notes are neither purged nor revived.

The final transition sequence refines the original plan: flush editors, capture
geometry, apply the proposed organization changes inside the transaction, stage
native editors against that uncommitted state, commit, then reconcile/present.
This supports newly created identities without a second allocation protocol.
Preparation failure still rolls back before any old window is removed; native
construction holds the SQLite write lock and does not iterate the main loop.

The panel closes by hiding for reuse. Each editor uses a local style provider,
and row action menus are created on demand. Stable focus keys and expansion
snapshots preserve browsing/search state. A read-only scrollable inspection
window keeps inactive-note consultation separate from Activate and open.

## Automated regression

Executed after the initial implementation changes; the later automated
qualification above supersedes these build/timing results:

```bash
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 -m unittest discover -s tests
/usr/bin/python3 -m compileall pinleaf tests
git diff --check
```

Result: **154 tests passed**, zero failures, zero skips; 1.481 seconds for the
suite in the final isolated X11 run. Compilation and whitespace checks passed.
The wrapper changes only the display/session environment; the unittest discovery
command is the repository's required command.

Non-failing diagnostics: software-rendering/DRI3 warnings in Xephyr; GTK 4
deprecation warnings for the supported StyleContext/CssProvider APIs. Native QA
deliberately disables accessibility-bus integration on its private bus, so it
does not qualify screen-reader output. The tray helper emits the expected missing
AT-SPI service warning there. An initial default-bus attempt timed out in the
desktop secret portal; the private QA bus avoids that unrelated service dependency.

| Tasks | Evidence |
| --- | --- |
| T01–T05 | `organization_fixtures.py`, `test_migrations.py`, `test_backup.py`: schemas 1–4, exact original note values/settings, required columns/contract, private snapshots, rollback and process interruption |
| T03, T06–T08 | `test_organization_service.py`, `test_context_recovery.py`: one durable composite commit, uniqueness/protection, last-context restore/repair, moves, search, disposal and stale summaries |
| T09–T10 | `test_context_controller.py`, `test_panel_context.py`: save/geometry/preparation/commit faults, pending buffers, real GTK disposal, hidden state, moves, no late deleted-note writes, post-commit presentation failure |
| T11–T14 | `test_main_window.py`, `test_panel_context.py`, `test_organization_dialogs.py`, native lifecycle script: profiles/groups, expansion vs activation, create/rename/move/delete, search reset, focus and defaults |
| T15 | Fault-injection tests plus `migration_recovery.py` using the v0.7.0 migrator |
| T17 | README, organization/recovery guide, known limitations and reconciled spec/plan/ADR/contract |
| T16, T18 | Available X11 and automated checks completed; qualification follow-ups below remain open |

## Maintained-case coverage

These are coverage results, not a claim that every manual step of every case
was executed on GNOME/Wayland. Reusable definitions remain in `verification.md`.

| Case | Executed evidence and boundary |
| --- | --- |
| TC-CTX-001 | All four legacy fixtures migrated; exact original columns/settings, deleted memberships, initial pt-BR context, repeated startup and schema contract passed |
| TC-CTX-002 | Backup permission/integrity/version failures, competing writer, denied DDL/copy/version writes and abrupt process exit passed; the source library remains usable |
| TC-CTX-003 | v0.7.0 reader rejected schema 5 without logical mutation; snapshot restored three exact rows; newer work recovered from separately preserved DB/WAL/SHM |
| TC-CTX-004 | Fake/real GTK and native lifecycle preserve open/hidden flags, timestamps and content; manual real X11 group/profile cycles and explicit hidden-note opening passed |
| TC-CTX-005 | Injected failures preserve context/editors; final real X11 automation verifies the visible save-error dialog, pending draft and successful retry; presentation failure preserves committed state |
| TC-CTX-006 | Service/controller/GTK/dialog moves preserve metadata and context; open notes enter/leave the active desktop, hidden notes stay hidden |
| TC-CTX-007 | Group/profile transfers include retained deleted rows and previously tombstoned source groups; profile transfer flattens membership; summary/cancel/fallback checks passed |
| TC-CTX-008 | Profile Delete all preserves unrelated notes and chooses the explicit replacement; final real X11 automation includes a hidden note and real editor disposal |
| TC-CTX-009 | Changed membership/count or destination name requires another review; autosaved text alone does not; SQL-failure rollback passed |
| TC-CTX-010 | Separate-process restart and panel close/reopen passed; real X11 shell Show Pinleaf/New Note/Quit and manual restart restoration passed without duplicate windows |
| TC-CTX-011 | All scopes, hidden/full-text matches, global breadcrumbs and real menu Activate and open passed; actual context change resets query/scope, same/failed context and rename retain them |
| TC-CTX-012 | Native/widget and real X11 XTest keyboard checks pass; an external private AT-SPI client verifies exported names/states; human Orca speech/usability remains unexecuted |

## Native application checks

Run a new temporary data directory for each `lifecycle`, `layout` or
`startup-error` scenario; `restart` uses the prior lifecycle's synthetic library:

```bash
XDG_DATA_HOME=/tmp/pinleaf-qa-new \
  PINLEAF_QA_SCREENSHOTS=/tmp/pinleaf-qa-new/screenshots \
  /usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_lifecycle.py
XDG_DATA_HOME=/tmp/pinleaf-qa-new \
  /usr/bin/python3 tests/gui_session.py /usr/bin/python3 tests/gui_lifecycle.py restart
```

Executed lifecycle/restart, startup-error (schema 99), layout and layout-dark.
The native flow exercises the application controller, pending editor text,
hidden notes, tray callbacks, panel close/reopen, explicit external-result menu
opening, deletion summary and cancellation. The incompatible database produces
a visible error and exit code 1; no empty replacement library is created.

Inspected screenshots contain only synthetic Pinleaf windows:

- [Groups and active context](evidence/panel-groups.png)
- [Global search breadcrumb](evidence/global-search.png)
- [Profile deletion summary](evidence/delete-profile.png)
- [Long names at 360px in the dark theme](evidence/narrow-dark.png)
- [Move destination with long names](evidence/move-long-names.png)
- [Incompatible-database error](evidence/startup-error.png)

The nested server has no GNOME compositor or indicator shell. It verifies real
GTK windows, not actual shell-menu clicking or compositor positioning.

## Recovery drill

```bash
/usr/bin/python3 tests/migration_recovery.py v0.7.0
```

Passed. The old migrator refuses schema 5 without mutation. After a child writes
new work in WAL mode and terminates abruptly, the stopped database and its real
WAL/SHM are moved into a separate recovery directory. The pre-upgrade snapshot
reopens under the old reader with all three original rows. The preserved newer
set reopens as schema 5 with four rows. This demonstrates the post-snapshot loss
boundary of the restored view and preservation of newer work for later recovery.

## Initial nested scale measurements

Synthetic short notes, three profiles and 30 groups. Five repetitions except
panel rendering (three), migration (one) and fresh-process startup (one each).
These are local Xephyr/software-rendering observations, not a supported-hardware
benchmark. Startup timings begin before `run()` and end at the first idle after
panel/editor restoration; fixture generation and interpreter startup are excluded.

| Operation | Median | Maximum |
| --- | ---: | ---: |
| Global service search, 1,000 notes | 15.04 ms | 18.19 ms |
| Global search panel construction, 1,000 matches | 569.21 ms | 596.79 ms |
| Context changes with 33–34 native editors | 516.05 ms | 604.16 ms |
| Schema-4 migration, three notes, including backup | 9.86 ms | 9.86 ms |
| Fresh startup, 100 notes / 10 open | 1,078.05 ms | single run |
| Fresh startup, 100 notes / 100 open | 5,520.01 ms | single run |

Before lazy row menus and local editor styles, global panel construction was
1,267.74 ms and context changes 744.79 ms (medians). The optimizations preserve
separate per-note styles, covered by a real GTK regression test.

Reproduce with `tests/gui_benchmark.py` and `tests/gui_startup_benchmark.py 10`
or `100`, each through `tests/gui_session.py`. The two-second startup target
passes with ten open windows here; the 100-open stress case exceeds it and
requires profiling/qualification on the supported desktop before full acceptance.
The later automated qualification profiles and corrects batch focus requests,
then measures the maintained 128-code-point fixture on the real X11 compositor;
use that record for the current performance boundary.

## Real X11 manual session

Started the current application on the user's X11 desktop (`DISPLAY=:1`) after
confirming the normal Pinleaf instance was stopped. The child process uses a
private, disposable `XDG_DATA_HOME`; the normal note library is not opened.
The synthetic fixture contains three profiles (Pessoal, Freelancer and Seventh),
eight groups and eight notes. Initial context is Pessoal / Financeiro, with two
open notes and one hidden note. Native X11 discovery confirms the panel and two
note windows. The maintainer confirmed the following manual observations:

- Expanding inactive Exercícios leaves the Financeiro desktop unchanged.
- Activating Exercícios hides both Financeiro windows and shows its own note.
- Returning to Financeiro restores both open notes; the hidden note stays struck
  through in the panel and does not open.
- Switching to Freelancer restores Empresa X - DevOps and its note. After
  selecting LGPD in Seventh, returning to Pessoal restores Financeiro with its
  two open notes and hidden note; returning to Seventh restores LGPD.
- From Seventh / LGPD, Ctrl+F and `TESTE X11` return one note in Active group,
  two notes across LGPD/Agenda in Current profile, and eight notes with paths in
  All profiles, including the struck-through hidden Financeiro note.
- Selecting Financeiro 2 from the global results opens a read-only inspection
  without changing context. Activate and open switches to Pessoal / Financeiro,
  clears the query and leaves the hidden note closed.
- Moving Financeiro 2 to Freelancer / Empresa X - DevOps removes its window from
  the Financeiro desktop without activating the destination. Switching to
  Freelancer shows its original note and the moved note with preserved text and
  color. Returning to Financeiro shows Financeiro 1; the hidden note remains
  struck through.
- Creating Temporário in Pessoal activates the new group. Two notes created
  there belong to it; explicitly closing TESTE GRUPO OCULTA leaves it hidden.
- The group deletion summary counts both notes. Cancelling the transfer to
  Pessoal / Financeiro preserves Temporário and its active context. Repeating
  and confirming removes the group and activates Pessoal / General. Activating
  Financeiro then shows Financeiro 1 and TESTE GRUPO ABERTA; both hidden notes
  remain struck through and closed.
- Creating a disposable profile (entered as Temporario) supplies General.
  The maintainer creates a second group and a note in each group, then confirms
  that cancelling Delete all notes leaves the profile available. Repeating and
  confirming removes it from navigation and activates Pessoal / Financeiro with
  two open and two hidden notes. A global search for TESTE PERFIL returns no
  results.
- Closing the panel leaves its two note windows visible. The real X11 shell
  indicator's Show Pinleaf action returns to Pessoal / Financeiro without
  duplicate windows. Its New Note action creates TESTE BANDEJA in that group.
  Quit closes the panel, note windows and indicator; the application process
  terminates.
- Restarting restores Pessoal / Financeiro with Financeiro 1, TESTE GRUPO ABERTA
  and TESTE BANDEJA open, while both hidden notes remain struck through and
  closed. Explicitly opening TESTE GRUPO OCULTA opens only that note. Closing it,
  activating Exercícios and returning to Financeiro restores the three open
  notes while both hidden notes remain closed.

These observations pass the group/profile-cycle and remembered-context portions
of TC-CTX-004, the expand-without-activation interaction, and the scoped/global
search, inspection and explicit-opening desktop checks for TC-CTX-011. Ctrl+F
also passes that interaction's desktop check in TC-CTX-012. The open-note,
cross-profile movement desktop check in TC-CTX-006, the group-transfer desktop
variant of TC-CTX-007 and the tested cancellation interaction in TC-CTX-012 pass.
The two-group profile Delete all/cancellation desktop variant of TC-CTX-008 also
passes. A read-only inspection of the synthetic database confirms both original
Financeiro notes still have `is_open=1` and the hidden note retains `is_open=0`;
no new application log errors occurred during this portion. The manual
explicit-open/re-hide variant in TC-CTX-004 passes. Other desktop qualification
checks remain pending. This supplementary desktop fixture uses Exercícios in
place of Dieta; its IDs are retained in the session manifest. The before/after
Financeiro 2 snapshots (`before-move-finance-2.json` and
`after-move-finance-2.json` beside the manifest) show only `group_id` changed;
ID, content, open flag, color, size, font appearance and creation/update
timestamps are unchanged. Its hidden sibling remains in Pessoal / Financeiro
with `is_open=0`.

After the group-transfer check, read-only inspection confirms Temporário is
tombstoned and its two live notes belong to Financeiro with `is_open=1` and `0`
respectively. Financeiro now contains two open and two hidden live notes;
`PRAGMA quick_check` returns `ok` and `foreign_key_check` returns no violations.
The session also emitted an IBus key-event warning; no application traceback or
storage error was logged in this portion.

For the profile-deletion check, `before-profile-delete-unaffected.json` and
`after-profile-delete.json` confirm all three pre-existing profile rows, nine
group rows and ten note rows are exactly unchanged. The new Temporario profile,
its General/custom groups and its two notes are tombstoned; no live global match
for TESTE PERFIL remains. Integrity and foreign-key checks pass. Both deleted
test notes retain `is_open=1`, so this manual variant establishes deletion of
open notes across groups, not deletion of an individually hidden note. The
hidden-note deletion variant was subsequently qualified by the automated real
X11 desktop scenario in the follow-up record.

The real-shell panel/tray/new-note/quit portion of TC-CTX-010 passes on X11.
After Quit, the saved active context is Pessoal / Financeiro with three open
notes (Financeiro 1, TESTE GRUPO ABERTA and TESTE BANDEJA) and two hidden notes.
Before restarting, the application bus name has no owner. The same disposable
library is reopened in a fresh process, and D-Bus confirms that process owns
the application name. X11 discovery finds exactly one panel and three note
windows. `before-restart-financeiro.json` and `after-restart-financeiro.json`
confirm content, open flags, membership, geometry and timestamps are unchanged
by restoration. The maintainer confirms the restored desktop, the isolated
opening of one hidden note, and its re-hiding across a subsequent group cycle.
Final read-only inspection finds Pessoal / Financeiro active with three open
and two hidden notes, `quick_check=ok` and no foreign-key violations. The
restart log contains only the previously observed AT-SPI connection failures.

Session manifest and application log are in
`/tmp/pinleaf-manual-x11-xotbsp4e/`. The desktop's accessibility service returns an
AT-SPI address whose socket is missing; application and tray startup report that
connection failure. This requires resolution before the screen-reader pass and
does not establish an application accessibility regression. Orca was not
started and desktop accessibility settings were not changed.

## Remaining qualification

- **T16 / T18 remain partial.** Real X11 AppIndicator-shell interactions pass.
  Run GNOME Wayland, including compositor geometry and AppIndicator-shell
  interactions; no Wayland session was available here. X11 size restoration
  passes; exact positioning retains the documented adapter limitation.
- Real X11 keyboard and exported AT-SPI state pass. Human Orca speech/usability
  has not been verified; private AT-SPI automation does not establish it.
- Real-desktop startup and scale have been re-measured after correction. The
  75-open normal baseline meets two seconds; the 100-open stress median is
  1941.68 ms and maximum 2001.47 ms. Preserve this strict-boundary follow-up.
- Visible save-error/retry and profile disposal with hidden notes now pass real
  X11 automation. No manual input is awaited for available local checks.
- See the follow-up record for nonfatal private-bus tray-helper diagnostics.

Publication is outside this implementation. The existing 0.8.0 metadata remains
development preparation; new feature notes are under Unreleased.
