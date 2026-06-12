# Known Limitations

Pinleaf is currently an MVP.

## Window Position

Note window size and open state are persisted, but exact window position restore
is best-effort. On Wayland, applications generally cannot force window
coordinates; the compositor decides placement.

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

The supported development run path is currently:

```bash
/usr/bin/python3 -m pinleaf
```

Flatpak, distro packages, desktop files and local install scripts are future
packaging work.
