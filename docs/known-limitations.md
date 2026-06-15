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

When the panel has been closed and is shown again through the indicator, GTK may
warn that a destroyed window is being shown. The user-visible behavior is still
acceptable for the MVP and should be revisited in a lifecycle polish pass.

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
