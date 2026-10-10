# Automated desktop qualification — 2026-10-10

The maintainer requested completing all available checks without further manual
participation. This supplements the earlier [execution record](execution-2026-10-10.md)
and its confirmed manual X11 observations. All fixtures are synthetic and private;
the normal note library was never opened. At the end of this QA run, no commit,
push, tag or release had been made. Subsequent feature-branch review is tracked
in [review status](review.md); no release publication is authorized.

## Validated build

- Branch: `feat/profiles-and-groups`, uncommitted at QA time, based on
  `23d4c92b5015b7afe785d5f18036f3e9918d5ec0`.
- Code/test/contract SHA-256:
  `2d8c25d506cdfbf98449b5286b14a640e60a6c420f427ae084a42d2e74777792`.
  The algorithm is defined in the earlier execution record.
- Python 3.12, GTK 4.14.5, libadwaita 1.5.0, current GNOME X11 compositor.
  Desktop automation uses a private session bus. AT-SPI checks additionally use
  a nested Xephyr display and private accessibility service, leaving desktop
  accessibility settings unchanged.
- Machine-readable [results and timing samples](evidence/automation-results.json).
  Raw command output is retained in `/tmp/pinleaf-final-qa-7_4ta2qk/` for this session.

## Corrections found through automation

1. Activating a group removed its Activate button and attempted to focus the
   outer, non-focusable ExpanderRow. Focus now enters its native header. A
   regression test failed before the correction and passes afterwards.
2. GTK selection updates replaced dropdown accessible names with their values.
   Search scope and destination/replacement selectors now have explicit
   labelled-by relationships. A separate AT-SPI client verifies the exported
   names, selected values, expanded state and hidden-note labels.
3. Restoring many notes requested compositor focus once per window. Context
   restoration now maps the batch and presents the final editor, while explicit
   single-note opens still request focus. All restored windows remain visible
   and mapped. Failed presentation still preserves the committed context.
4. Color palettes are built when opened. The GTK regression test opens the
   actual palette and verifies that selecting green persists the color.

## Executed checks

| Check | Result and evidence boundary |
| --- | --- |
| Full unittest discovery | **157 passed**, zero failures/skips, 1.655 s |
| `compileall pinleaf tests` | Passed |
| `git diff --check` | Passed |
| Visible save failure and retry, TC-CTX-005 | A real dialog appears; context/editor and pending draft remain; dismissing and retrying after fault removal saves the draft and switches successfully |
| XTest keyboard, TC-CTX-012 | Actual Ctrl+F/Escape, inactive-group expansion, action-menu opening, Rename cancellation and invoking-control focus restoration passed |
| X11 resize/context cycle | Resized logical size 359×239 persists and restores; exact position remains the documented adapter limitation |
| Profile Delete all, TC-CTX-008 | Actual summary/confirmation deletes notes across General/custom groups, including a hidden note, selects the replacement and preserves an unrelated note exactly |
| Profile transfer, TC-CTX-007 | Actual confirmation transfers open/hidden notes from two groups into Seventh / Agenda; destination becomes active and note values/open state are preserved |
| Separate-process AT-SPI | Three inspections passed: profile/hidden/expanded/80-character name; scope/global result; destination controls/full selected group name. This verifies exported accessibility data, not Orca speech |
| Native lifecycle/restart | Passed again after the final product changes |
| Incompatible startup | Schema 99 produces the visible error, exit 1 and no replacement library |
| Narrow light/dark layouts | Passed, including the new visible scope label and global results at 360 px |

Reproduce the principal checks:

```bash
/usr/bin/python3 tests/gui_session.py /usr/bin/python3 -m unittest discover -s tests
PINLEAF_QA_SCREENSHOTS=/tmp/pinleaf-auto-evidence \
  /usr/bin/python3 tests/gui_session.py --desktop \
  /usr/bin/python3 tests/gui_desktop_qualification.py
/usr/bin/python3 tests/gui_session.py --a11y /usr/bin/python3 tests/gui_accessibility.py
/usr/bin/python3 tests/gui_session.py --desktop /usr/bin/python3 tests/gui_benchmark.py
/usr/bin/python3 tests/gui_session.py --desktop /usr/bin/python3 tests/gui_startup_benchmark.py 75
/usr/bin/python3 tests/gui_session.py --desktop /usr/bin/python3 tests/gui_startup_benchmark.py 100
```

`--desktop` needs X11; `--a11y` intentionally uses only the nested display so the
private accessibility service cannot replace the desktop's accessibility bus.
Xephyr/XTest/AT-SPI are QA dependencies, not new application dependencies.

Inspected window-only screenshots:

- [Save failure and retry message](evidence/save-error-retry.png)
- [Delete all summary including hidden notes](evidence/delete-profile-hidden.png)
- [Scope and global results at narrow dark width](evidence/search-narrow-dark.png)

Non-failing diagnostics: existing GTK deprecation warnings, Xephyr DRI3 warnings,
and the GTK 3 tray helper's missing AT-SPI warning on deliberately restricted
functional-test buses. Two short startup runs also emitted a nonfatal GTK 3
tray-helper freeze/thaw assertion, and one emitted an IBus connection warning.
These runs exited successfully; real-shell tray behavior was checked separately
on the normal desktop bus. The tray-helper assertion remains a diagnostic
follow-up rather than an established main-application regression.

## Performance on the current X11 desktop

Startup samples use 100 notes, each exactly 128 code points, fixed IDs/timestamps,
and a fresh process. The 75-open baseline hides every fourth note; 10-open and
100-open samples are additional variants. Three samples per variant. Timing
starts before `run()` and ends at the first idle after all expected editors are
visible and mapped; interpreter startup, fixture generation and shutdown are
excluded. These measurements do not establish first-paint latency on all hardware.

| Notes / open windows | Samples (ms) | Median | Maximum |
| --- | --- | ---: | ---: |
| 100 / 10 | 1076.84, 1017.25, 1122.63 | 1076.84 | 1122.63 |
| 100 / 75 | 1459.60, 1515.36, 1682.05 | 1515.36 | 1682.05 |
| 100 / 100 | 1831.59, 2001.47, 1941.68 | 1941.68 | 2001.47 |

The maintained 75-open normal baseline meets two seconds in every local sample.
The 100-open stress median is below two seconds, but its maximum exceeds the
boundary by 1.47 ms; do not claim every stress run meets the target. Before the
focus correction, shorter-content real-desktop samples took approximately
2.3 s with 75 open and 2.8 s with 100 open. Those earlier inputs differ, so this
comparison is directional rather than a controlled speedup estimate.

Scale data now follows the maintained case: 1,000 notes, 128 code points each,
three profiles, 30 groups and 250 hidden notes. Search/context: five repetitions;
panel construction: three; migration: one.

| Operation | Median | Maximum |
| --- | ---: | ---: |
| Global service search, 1,000 matches | 23.16 ms | 45.66 ms |
| Global panel construction, 1,000 matches | 993.52 ms | 1280.46 ms |
| Context changes, 17–34 visible editors | 213.85 ms | 242.22 ms |
| Schema-4 migration, three notes plus backup | 8.03 ms | 8.03 ms |

## Remaining acceptance boundaries and cleanup

- **Wayland: not run.** No Wayland session/compositor is available here.
- **Orca speech/human usability: not run.** Exported AT-SPI data and XTest
  keyboard behavior pass; spoken announcements still require human assessment.
  The current shared desktop's accessibility service advertises a missing socket;
  the private test service works without changing that session.
- Exact note coordinates remain best effort: the current GTK 4 adapter has no
  `get_position`/`move` methods on this X11 build. It preserves stored fallback
  coordinates while the compositor places the windows. Size restoration passes.
- Preserve the stress timing boundary and private-bus tray diagnostic above.
  T16/T18 remain qualified by these explicit follow-ups; no manual input is
  awaited to complete the automations available in this session.

The long-running disposable manual app was stopped gracefully through its own
tray socket before automation. Automated app/tray/Xephyr sessions close at the
end of each run. Synthetic evidence is retained; normal note data and desktop
settings remain unchanged.
