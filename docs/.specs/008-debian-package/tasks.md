# Tasks: Local Debian package installation

## Source

- Spec: `docs/.specs/008-debian-package/spec.md`
- Plan: `docs/.specs/008-debian-package/plan.md`
- Issue: `https://github.com/robmoraes/pinleaf/issues/8`

## Implementation Tasks

1. Add Debian packaging skeleton.
   - Add required files under `debian/`.
   - Set package name, maintainer, version and section.
   - Use a conventional Debian source format.
   - Validation: packaging files are parseable by Debian tooling.

2. Declare dependencies.
   - Add build dependencies for Python/Debian packaging helpers.
   - Add runtime dependencies for Python, GTK 4, libadwaita and Ayatana
     AppIndicator.
   - Validation: install testing pulls missing runtime dependencies.

3. Install application files.
   - Install the `pinleaf` command.
   - Install Python package files and bundled resources.
   - Install desktop launcher.
   - Install icons in hicolor paths.
   - Validation: installed command launches without source checkout paths.

4. Preserve user data on removal.
   - Avoid maintainer scripts that delete XDG user data.
   - Document that package removal does not remove note data.
   - Validation: removing the package preserves `~/.local/share/pinleaf`.

5. Document local package workflow.
   - Add build dependency installation command.
   - Add local package build command.
   - Add local install command with `sudo apt install ./pinleaf_*.deb`.
   - Add removal command.
   - Validation: documentation matches tested commands.

6. Add focused tests or checks where practical.
   - Check packaging metadata or expected desktop/icon files if useful.
   - Keep tests runnable without root.
   - Validation: unit tests pass.

7. Build and inspect the package.
   - Build the local `.deb`.
   - Inspect package contents.
   - Run `lintian` if available.
   - Validation: build succeeds and warnings are documented or addressed.

8. Manual acceptance pass.
   - Install the generated `.deb` on a clean or isolated Debian/Ubuntu system.
   - Confirm `pinleaf` launches.
   - Confirm launcher and icon integration.
   - Remove the package.
   - Confirm user note data remains.

9. Run automated checks.
   - Run `/usr/bin/python3 -m unittest discover -s tests`.
   - Run `/usr/bin/python3 -m compileall pinleaf tests`.
   - Validation: both commands pass.

## Progress

- Tasks 1-7 and 9: implemented.
- Automated checks passed:
  - `/usr/bin/python3 -m unittest discover -s tests`
  - `/usr/bin/python3 -m compileall pinleaf tests`
  - `dpkg-buildpackage -us -uc -b`
- Package inspection passed with `dpkg-deb -I` and `dpkg-deb -c`.
- Manual install/launch/removal/reinstall check: passed on maintainer machine.
  Existing user note data was preserved and previous sticky notes opened
  correctly after package installation.
- `lintian`: maintainer reported `no-manual-page` for `/usr/bin/pinleaf`; this
  remains accepted for this first local package iteration.
- `apt`: maintainer reported the expected unsandboxed local file note when
  installing the `.deb` from a path inaccessible to the `_apt` user. This is
  documented with the `/tmp` workaround.
- Task 8: completed.
