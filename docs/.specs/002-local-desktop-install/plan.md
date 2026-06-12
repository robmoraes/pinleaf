# Plan: Pinleaf local desktop install

## Spec Link

- Source spec: `docs/.specs/002-local-desktop-install/spec.md`

## Approach

Add two shell scripts:

- `scripts/install-local`
- `scripts/uninstall-local`

The scripts install only into the current user's home directory. They do not
install dependencies and do not require root access.

## Installed Files

Wrapper:

```text
~/.local/bin/pinleaf
```

Desktop launcher:

```text
~/.local/share/applications/dev.pinleaf.Pinleaf.desktop
```

Icons:

```text
~/.local/share/icons/hicolor/16x16/apps/pinleaf.png
~/.local/share/icons/hicolor/32x32/apps/pinleaf.png
~/.local/share/icons/hicolor/64x64/apps/pinleaf.png
~/.local/share/icons/hicolor/256x256/apps/pinleaf.png
```

The 256x256 path can use the current large source icon. The launcher can refer
to `Icon=pinleaf`.

## Wrapper Design

The wrapper should pin the source checkout path at install time:

```sh
#!/usr/bin/env sh
cd "<repo-root>"
exec /usr/bin/python3 -m pinleaf "$@"
```

This keeps the install simple and source-based. Moving the repository after
install requires re-running `scripts/install-local`.

## Desktop File

Use:

```ini
[Desktop Entry]
Type=Application
Name=Pinleaf
Comment=Desktop sticky notes
Exec=<home>/.local/bin/pinleaf
Icon=pinleaf
Terminal=false
Categories=Utility;Office;
StartupWMClass=dev.pinleaf.Pinleaf
```

## Cache Updates

Run cache updates only when tools are available:

- `update-desktop-database ~/.local/share/applications`
- `gtk-update-icon-cache ~/.local/share/icons/hicolor`

Cache update failures should warn but not fail the install.

## Validation

Automated validation:
- scripts pass shell syntax checks with `sh -n`;
- install script creates files when run with temporary `HOME`;
- uninstall script removes files when run with temporary `HOME`;
- uninstall does not remove `~/.local/share/pinleaf`.

Manual validation:
- run `scripts/install-local`;
- launch `pinleaf` from terminal after ensuring `~/.local/bin` is on `PATH`;
- launch Pinleaf from the desktop application menu;
- confirm dock/launcher icon uses Pinleaf icon;
- run `scripts/uninstall-local`.

## Risks

- Some desktop shells may cache old launcher metadata until logout or cache
  refresh.
- If the repository is moved, the wrapper points to the old path.
- AppIndicator behavior still depends on the desktop session environment.
