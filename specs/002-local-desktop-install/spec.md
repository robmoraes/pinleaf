# Feature: Pinleaf local desktop install

## Intent

Problem:
Running Pinleaf from the repository root is acceptable for development, but it
does not provide a normal desktop application experience. The app does not
appear reliably in launchers, docks or application menus with its own identity.

Users or stakeholders:
Developers and early local testers running Pinleaf on Linux desktop.

Desired outcome:
Pinleaf can be installed into the current user's desktop environment without
root access, then launched from the application menu, terminal or status
indicator with the correct app icon.

Non-goals:
- Flatpak packaging.
- Debian/Ubuntu package creation.
- System-wide installation under `/usr`.
- Automatic dependency installation.
- Publishing to an app store or package registry.

## Scope

In scope:
- A local install script.
- A local uninstall script.
- A user-local executable wrapper.
- A user-local `.desktop` launcher.
- User-local hicolor icon installation.
- README instructions for local install and uninstall.

Out of scope:
- Sandboxing.
- Versioned upgrades.
- Binary builds.
- System package manager integration.
- Desktop environment support beyond common XDG paths.

Assumptions:
- The user runs scripts from the repository root.
- The app continues to run from the source checkout during local install.
- The target desktop follows XDG user paths.
- The system already has Pinleaf runtime dependencies installed.

Dependencies:
- `/usr/bin/python3`.
- Shell utilities available on common Linux desktops: `mkdir`, `cp`, `chmod`, `cat`.
- Optional cache update commands when available: `update-desktop-database`, `gtk-update-icon-cache`.

## Behavior

1. The user can run `scripts/install-local` from the repository root.
2. The install script creates `~/.local/bin/pinleaf`.
3. The wrapper launches the current source checkout with `/usr/bin/python3 -m pinleaf`.
4. The install script creates `~/.local/share/applications/dev.pinleaf.Pinleaf.desktop`.
5. The desktop file uses the Pinleaf app id, name and icon.
6. The install script copies Pinleaf icons into `~/.local/share/icons/hicolor`.
7. The install script makes the wrapper executable.
8. Re-running the install script updates existing local install files.
9. The user can run `scripts/uninstall-local` to remove the wrapper, desktop file and installed icons.
10. The uninstall script does not remove user note data.
11. The scripts fail with a clear message when run outside the repository root.
12. The scripts do not require root access.

## Acceptance Examples

Scenario: install local launcher
Given the user is in the Pinleaf repository root
When the user runs `scripts/install-local`
Then `~/.local/bin/pinleaf` exists and is executable
And `~/.local/share/applications/dev.pinleaf.Pinleaf.desktop` exists
And Pinleaf icons exist under `~/.local/share/icons/hicolor`

Scenario: launch from wrapper
Given Pinleaf is locally installed
When the user runs `~/.local/bin/pinleaf`
Then Pinleaf starts from the source checkout

Scenario: uninstall local launcher
Given Pinleaf is locally installed
When the user runs `scripts/uninstall-local`
Then the wrapper, desktop file and installed icons are removed
And `~/.local/share/pinleaf/pinleaf.sqlite3` is not removed

Scenario: wrong directory
Given the user is outside the Pinleaf repository root
When the user runs `scripts/install-local`
Then the script exits with a clear error
And no install files are written

## Data and Contracts

Inputs:
- Current repository path.
- Existing Pinleaf icon files.

Outputs:
- User-local executable wrapper.
- User-local desktop file.
- User-local icon files.

API/schema/event changes:
- None.

Persistence changes:
- None. User note data is not changed by install or uninstall scripts.

## Quality Attributes

Security:
- Scripts must not use `sudo`.
- Scripts must write only to user-local XDG locations.
- The desktop file must not execute arbitrary shell input.

Privacy:
- Install and uninstall scripts must not inspect or alter note content.

Accessibility:
- The desktop launcher should use a clear app name: `Pinleaf`.

Reliability:
- Scripts should be idempotent.
- Missing optional cache update tools should not fail the install.

Observability:
- Scripts should print the installed or removed paths.

## Rollout and Operations

Migration:
- No data migration.

Feature flag or configuration:
- None.

Rollback:
- Run `scripts/uninstall-local`.

Monitoring:
- None.
