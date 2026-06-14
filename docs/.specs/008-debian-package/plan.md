# Plan: Local Debian package installation

## Spec Link

- Source spec: `docs/.specs/008-debian-package/spec.md`
- Tracking issue: `https://github.com/robmoraes/pinleaf/issues/8`

## Approach

Add conventional Debian packaging under `debian/` and build a local `.deb`
package for Pinleaf.

Use the Python package metadata from `pyproject.toml` where practical, while
installing desktop integration files through Debian packaging rules. The package
should install a system command, desktop file, icons and Python package data
without relying on the source checkout path used by `scripts/install-local`.

The first iteration targets local package builds and local installation testing.
PPA publication remains a follow-up after the package layout and dependencies
are proven locally.

## Implementation Notes

- Add Debian source metadata:
  - `debian/control`
  - `debian/rules`
  - `debian/changelog`
  - `debian/copyright`
  - source format metadata as needed.
- Declare runtime dependencies for:
  - `python3`
  - `python3-gi`
  - `gir1.2-gtk-4.0`
  - `gir1.2-adw-1`
  - `gir1.2-ayatanaappindicator3-0.1`
  - `libayatana-appindicator3-1`
- Add install metadata for:
  - command wrapper or generated Python entry point;
  - desktop file under `/usr/share/applications`;
  - icons under `/usr/share/icons/hicolor`;
  - bundled package resources.
- Avoid package maintainer scripts unless they are necessary.
- Keep uninstall behavior limited to package-managed files.
- Document build and install commands in the README or a packaging doc.

## Files

Expected new or changed areas:

- `debian/`: Debian packaging metadata.
- `README.md` or `docs/`: local `.deb` build/install documentation.
- `tests/`: focused checks for package metadata or installed file manifests
  where practical.
- `CHANGELOG.md`: release-visible packaging support, if included in a release.

## Validation

Automated:

- run `/usr/bin/python3 -m unittest discover -s tests`;
- run `/usr/bin/python3 -m compileall pinleaf tests`;
- build the package locally;
- run packaging checks such as `lintian` where available.

Manual:

- install the generated `.deb` with `sudo apt install ./pinleaf_*.deb`;
- run `pinleaf` from the terminal;
- confirm the desktop launcher appears with the correct icon;
- remove the package;
- confirm user note data is not removed.

## Risks

- Debian Python packaging may install package data differently than source-tree
  execution.
- Desktop launcher and icon cache behavior may vary by environment.
- Runtime dependencies may differ between Debian and Ubuntu releases.
- Local install scripts and Debian package files may drift if both are not
  documented clearly.

