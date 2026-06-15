# Tasks: Ubuntu PPA publication

## Source

- Spec: `docs/.specs/009-ubuntu-ppa/spec.md`
- Plan: `docs/.specs/009-ubuntu-ppa/plan.md`
- Issue: `https://github.com/robmoraes/pinleaf/issues/13`

## Implementation Tasks

1. Confirm external Launchpad setup.
   - Use personal PPA `ppa:robmoraes/pinleaf`.
   - Confirm maintainer GPG key is registered in Launchpad.
   - Confirm local tools are installed.
   - Validation: `debuild`, `debsign`, `dput` and GPG key are available.

2. Define PPA release metadata.
   - Decide target Ubuntu series for the first upload.
   - Decide Launchpad-compatible package version.
   - Update `debian/changelog` if needed.
   - Validation: version and distribution are accepted by source-package tools.

3. Validate source-package build.
   - Build a signed source package.
   - Confirm generated `.dsc` and source `.changes` files exist.
   - Confirm the source `.changes` file is signed by the maintainer key.
   - Validation: source-package build exits successfully.

4. Inspect source-package contents.
   - Confirm source package includes required app files and packaging metadata.
   - Confirm it does not rely on ignored local artifacts.
   - Run packaging checks where practical.
   - Validation: no blocking packaging errors remain.

5. Upload to Launchpad PPA.
   - Run `dput ppa:robmoraes/pinleaf <source.changes>`.
   - Confirm Launchpad accepts the upload.
   - Monitor build queue and build logs.
   - Validation: Launchpad publishes a binary package.

6. Test installation from PPA.
   - Add `ppa:robmoraes/pinleaf` on an Ubuntu system.
   - Run `sudo apt update`.
   - Run `sudo apt install pinleaf`.
   - Launch from terminal and desktop launcher.
   - Validation: installed app runs correctly.

7. Test package removal and data preservation.
   - Create or reuse note data.
   - Remove the package.
   - Reinstall from the PPA.
   - Validation: user note data remains available.

8. Update documentation.
   - Add PPA install commands to README.
   - Add PPA install commands to GitHub Pages.
   - Keep GitHub Release download as an alternative.
   - Validation: docs match the tested PPA flow.

9. Update release notes.
   - Update `CHANGELOG.md` for the PPA distribution support.
   - Keep version metadata aligned if a new release is created.
   - Validation: changelog reflects user-visible install changes.

10. Run automated checks.
    - Run `/usr/bin/python3 -m unittest discover -s tests`.
    - Run `/usr/bin/python3 -m compileall pinleaf tests`.
    - Validation: both commands pass.

## Progress

- Task 1: completed.
  - Personal PPA selected: `ppa:robmoraes/pinleaf`.
  - Launchpad team namespace deferred.
  - Local tools verified:
    - `debuild`
    - `debsign`
    - `dput`
    - `ubuntu-dev-tools`
    - `debhelper`
    - `build-essential`
  - Local GPG key verified:
    - `C8F3D9976DEDB74C5C31BFC87854367646319599`
- Task 2: completed.
  - Target Ubuntu series: `noble`.
  - Package version: `0.6.0`.
- Task 3: completed.
  - Signed source package generated with:
    `debuild -S -kC8F3D9976DEDB74C5C31BFC87854367646319599`.
  - Signatures verified for `.dsc`, `.buildinfo` and source `.changes`.
- Task 4: completed.
  - Source package excludes local agent metadata, VCS metadata, `tmp/` and
    local build artifacts through `debian/source/options`.
  - `lintian` completed without warnings on the source `.changes`.
- Task 5: completed through Launchpad build.
  - Upload command passed:
    `dput ppa:robmoraes/pinleaf ../pinleaf_0.6.0_source.changes`.
  - Launchpad accepted the upload.
  - Launchpad build `32971598` completed successfully for `noble`/`amd64`.
  - Maintainer later confirmed publication completed and the package installed
    successfully through APT.
- Task 6: completed.
  - Maintainer installed Pinleaf from `ppa:robmoraes/pinleaf` after Launchpad
    publication completed.
  - The installed version on the maintainer PC is now the APT/PPA package.
- Task 7: completed.
  - Maintainer completed manual removal and reinstall testing after
    publication.
  - No data-loss issue was reported during the PPA validation pass.
- Task 8: completed in branch documentation.
  - README and GitHub Pages document the PPA install flow.
  - GitHub Release package download remains documented as an alternative.
- Task 9: completed.
  - `CHANGELOG.md` includes `0.6.0` PPA distribution support.
- Task 10: completed.
  - `/usr/bin/python3 -m unittest discover -s tests` passed.
  - `/usr/bin/python3 -m compileall pinleaf tests` passed.
  - `dpkg-buildpackage -us -uc -b` passed.
  - `lintian ../pinleaf_0.6.0_source.changes` passed without warnings.
  - `lintian ../pinleaf_0.6.0_amd64.changes` reported the known accepted
    warning: `no-manual-page [usr/bin/pinleaf]`.
