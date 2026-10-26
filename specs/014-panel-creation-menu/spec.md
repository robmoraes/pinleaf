# Feature: Panel creation menu

Status: implemented and locally verified on 2026-10-11.
Source: [package workstream 2](../012-shared-notes-and-remote-backup/spec.md).

## Intent and scope

Give the note list more room by bringing note and group creation into the
header's New menu. Users choose an action each time; New does not remember a
creation mode. This slice changes the panel only. Shared's +, existing creation
destinations, organization validation, tray actions and search remain available.
Remote integration and release preparation belong to later package work.

## Behavior

- **NEW-01:** New opens a menu with New Note and New Group…; opening or dismissing
  the menu creates nothing and changes no context or persistent setting.
- **NEW-02:** New Note closes the menu and uses the existing note-creation path:
  active ordinary group when present, otherwise the current profile's Shared.
- **NEW-03:** New Group… closes the menu and opens the existing group-name dialog
  for the current profile. Create and activate, reserved/duplicate-name checks,
  cancellation and save-error retry retain their current behavior.
- **NEW-04:** Remove the separate New group button from the panel body so the
  scrolling note list receives the space. Existing keyboard handling, tray
  creation and Shared's + continue through their current paths.
- **NEW-05:** New and both actions are keyboard reachable and named for assistive
  technology. Escape dismisses the menu without a write. Long profile/group
  titles and narrow/light/dark layouts retain reachable menu actions.

## Acceptance examples

| ID | Given | When | Then |
| --- | --- | --- | --- |
| AC-01 | The panel is open | Open New and dismiss it | Both actions are offered; no note/group/context/settings change occurs |
| AC-02 | Shared-only context, then an ordinary group | Choose New Note in each context | A note opens in Shared, then the ordinary group; context is preserved |
| AC-03 | An ordinary group is active | Choose New Group…, cancel, then reopen and create Project B | Cancellation preserves context; creation activates Project B in the same profile; New still offers both actions |
| AC-04 | A group name conflicts with Shared or another group | Confirm New Group… | The dialog reports validation and remains available for retry |
| AC-05 | A narrow panel with a long context title | Open New with the keyboard and use Escape or Enter | Actions remain reachable; dismissal has no effect; deliberate selection runs the chosen flow; body contains no separate New group button |

## Contracts, quality and delivery

This introduces no storage, schema, API, configuration, dependency or network
boundary; no new machine-readable contract or ADR is needed. Only deliberate
actions use existing creation/persistence and error paths. Accessible labels,
keyboard dismissal/selection and layout are validated on isolated X11 with
synthetic data. Existing platform limitations remain.

No material questions remain: the package already defines these actions and
destinations, and the maintainer requested implementation. Follow the
[plan](plan.md) and [tasks](tasks.md). Keep version 0.8.0 and the existing schema;
delivery stays local until the maintainer requests publication of the larger
package. Do not push, update the remote PR or trigger pipelines for this slice.

Results and screenshots: [execution record](execution.md).
