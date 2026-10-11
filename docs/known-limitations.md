# Known Limitations

Pinleaf is currently an MVP.

## Supported Platform

The primary target is Ubuntu 24.04 LTS with GNOME or GNOME-style desktop
sessions.

The supported packaged install path is:

```bash
sudo add-apt-repository ppa:robmoraes/pinleaf
sudo apt update
sudo apt install pinleaf
```

Pinleaf may work on other Debian/Ubuntu-compatible systems where the same
runtime dependencies are available, but those systems are currently
best-effort.

The following targets are not currently validated:

- Fedora, Arch, openSUSE or other non-Debian distributions;
- KDE, Xfce, LXQt or other non-GNOME desktop behavior;
- Flatpak, Snap or AppImage packaging;
- macOS or Windows.

## Window Position

Note window size and open state are persisted. Exact window position capture and
restore are best-effort. GTK 4 on Wayland does not expose a reliable public API
for application-controlled window coordinates; the compositor decides placement.
On the tested X11 build, the current GTK 4 adapter also lacks the generic
`get_position`/`move` methods: saved fallback coordinates remain stored, while
the compositor places the windows. Automated resizing and size restoration pass.

## AppIndicator Behavior

The status indicator is implemented with Ayatana AppIndicator in a separate
GTK 3 helper process so the main app can stay on GTK 4/libadwaita.

Depending on how the app is launched, the indicator may depend on desktop
session environment variables such as `DBUS_SESSION_BUS_ADDRESS` and
`XDG_RUNTIME_DIR`. Launching from the Ubuntu Terminal is the current tested
path.

## Dock and Launcher Icon

Running with `/usr/bin/python3 -m pinleaf` may still show a generic Python or
terminal icon in the Ubuntu dock. Proper dock/launcher identity requires a
desktop file and installed icon metadata, which is out of scope for the MVP.

## Panel Focus

When the main panel is minimized, choosing `Show Pinleaf` from the indicator may
show Ubuntu's `"Pinleaf" is ready` notification before the window is focused.
This behavior is accepted for the MVP.

Closing the panel now hides it for reuse through the indicator or launcher.
It preserves the active context and individually hidden notes.

## Profiles and Groups

Development schema 6 cannot be opened by published 0.8.0 (schema 5). Returning to an older version
requires a deliberate [snapshot restore](organization-and-recovery.md) with
Pinleaf stopped. Later edits remain only in the separately preserved newer
recovery set. Backups are local and are not automatically pruned.

Shared development QA adds automated migration, controller and GTK checks,
plus an isolated nested X11 lifecycle with actual Ctrl+F/Escape/Enter events,
shared-window identity, profile transfer, hidden-note opening, restart and
normal/narrow dark layouts. The app's real tray helper runs on the private bus
and is explicitly reaped after testing. These results supplement the 0.8.0 X11
qualification below; they do not qualify a different desktop environment.
See the [Shared execution record](../specs/013-general-to-shared/execution.md).

Feature QA covers GTK widget tests, an isolated nested X11 session and a manual
real X11 desktop pass with disposable data. Context switching, search, movement,
group transfer, profile deletion, real AppIndicator actions, restart and explicit
hidden-note opening passed on X11. Additional automation passes actual keyboard
events, visible save-error/retry, size restoration and profile deletion/transfer
including hidden notes. A separate client verifies names/states exported over
a private AT-SPI bus. Wayland and human Orca speech/usability remain unqualified;
the shared desktop's accessibility service advertises a missing socket. The
existing positioning limitation above remains.

After batch focus and lazy-menu improvements, the real X11 desktop starts 100
128-character notes with 75 open windows in a median 1.52 seconds (maximum 1.68).
With all 100 open, the median is 1.94 seconds and maximum 2.001 seconds; the
strict stress boundary has little margin. These local first-idle measurements
exclude interpreter startup, fixture generation and shutdown. See the
[final qualification evidence](../specs/011-profiles-and-groups/automation-2026-10-10.md)
for every sample, the earlier nested baseline and nonfatal private-bus tray
diagnostics. They do not guarantee the same timings on every desktop.

## Packaging

The supported packaged install path is Ubuntu 24.04 LTS through the Launchpad
PPA.

The supported development run path is:

```bash
/usr/bin/python3 -m pinleaf
```

GitHub Release `.deb` artifacts and local Debian package builds are maintained
as alternative installation paths. Flatpak, Snap and AppImage packages are not
currently provided.
