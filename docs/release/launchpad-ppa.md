# Manual Launchpad PPA Publication

This document describes the manual Pinleaf publication flow for the Launchpad
PPA.

It assumes the maintainer already has:

- a Launchpad account;
- SSH key configured in Launchpad;
- OpenPGP/GPG key registered and verified in Launchpad;
- the personal PPA created at `ppa:robmoraes/pinleaf`;
- local terminal access on Ubuntu 24.04 or a compatible Ubuntu system.

The current PPA target is Ubuntu 24.04 LTS:

```text
noble
```

## Key Values

PPA:

```text
ppa:robmoraes/pinleaf
```

GPG fingerprint:

```text
C8F3D9976DEDB74C5C31BFC87854367646319599
```

Launchpad PPA page:

```text
https://launchpad.net/~robmoraes/+archive/ubuntu/pinleaf
```

APT repository content:

```text
https://ppa.launchpadcontent.net/robmoraes/pinleaf/ubuntu/
```

## Install Local Maintainer Tools

Install the tools needed to build, sign and upload source packages:

```bash
sudo apt update
sudo apt install \
  build-essential \
  debhelper \
  devscripts \
  dput \
  ubuntu-dev-tools
```

Verify the expected commands exist:

```bash
command -v debuild
command -v debsign
command -v dput
command -v dpkg-buildpackage
command -v lintian
```

Verify the GPG key is available locally:

```bash
gpg --list-secret-keys --keyid-format=long
```

The key list must include the Launchpad-registered fingerprint.

## Release Checklist

Start from a clean and updated `main` branch:

```bash
git switch main
git pull
git status -sb
```

Create a short-lived release or packaging branch:

```bash
git switch -c release/0.6.0
```

Update version references:

- `pyproject.toml`
- `pinleaf/metadata.py`
- `pinleaf/__init__.py`
- `debian/changelog`
- `CHANGELOG.md`
- README or site documentation, when install commands change

For the PPA upload, `debian/changelog` must use the target Ubuntu series:

```text
pinleaf (0.6.0) noble; urgency=medium

  * Publish Pinleaf through the maintainer Ubuntu PPA.

 -- Carlos R Moraes <carlos.moraes.as@gmail.com>  Mon, 15 Jun 2026 10:00:00 -0300
```

Use a new version for every upload. Launchpad will reject uploading the same
source package version to the same PPA again.

## Run Local Checks

Run the project checks before building packages:

```bash
/usr/bin/python3 -m unittest discover -s tests
/usr/bin/python3 -m compileall pinleaf tests
```

Build a local binary package to catch packaging regressions:

```bash
dpkg-buildpackage -us -uc -b
```

Inspect the package if needed:

```bash
dpkg-deb -I ../pinleaf_0.6.0_all.deb
dpkg-deb -c ../pinleaf_0.6.0_all.deb | less
```

Run `lintian` on the binary build:

```bash
lintian ../pinleaf_0.6.0_amd64.changes
```

The current accepted warning is:

```text
no-manual-page [usr/bin/pinleaf]
```

## Build The Signed Source Package

Launchpad PPAs expect source package uploads. Do not upload the local `.deb`
directly.

Build and sign the source package:

```bash
debuild -S -kC8F3D9976DEDB74C5C31BFC87854367646319599
```

This creates source artifacts in the parent directory:

```text
../pinleaf_0.6.0.dsc
../pinleaf_0.6.0.tar.xz
../pinleaf_0.6.0_source.buildinfo
../pinleaf_0.6.0_source.changes
```

Verify the signatures:

```bash
gpg --verify ../pinleaf_0.6.0.dsc
gpg --verify ../pinleaf_0.6.0_source.buildinfo
gpg --verify ../pinleaf_0.6.0_source.changes
```

The signature should be from the Launchpad-registered key.

Run `lintian` on the source upload:

```bash
lintian ../pinleaf_0.6.0_source.changes
```

The source upload should be clean before publishing.

## Check And Simulate The Upload

Before uploading for real, run `dput` checks:

```bash
dput -o ppa:robmoraes/pinleaf ../pinleaf_0.6.0_source.changes
dput -s ppa:robmoraes/pinleaf ../pinleaf_0.6.0_source.changes
```

The simulation should show uploads to:

```text
ppa.launchpad.net:~robmoraes/pinleaf
```

## Upload To Launchpad

Upload the signed source package:

```bash
dput ppa:robmoraes/pinleaf ../pinleaf_0.6.0_source.changes
```

Expected result:

```text
Successfully uploaded packages.
```

Launchpad then processes the upload asynchronously. The package may take a few
minutes to appear in the PPA page.

## Monitor Launchpad

Open the PPA package page:

```text
https://launchpad.net/~robmoraes/+archive/ubuntu/pinleaf/+packages
```

Useful states:

- `Pending`: upload accepted, build not finished or not published yet.
- `Currently building`: Launchpad is building the package.
- `Successfully built`: the build completed.
- `FULLYBUILT_PENDING`: build succeeded, but the APT index is not published
  yet.
- `Failed to build`: inspect the build log, fix packaging, bump the version and
  upload again.

The build page provides the build log and generated files. For the first
`0.6.0` upload, the successful build was:

```text
https://launchpad.net/~robmoraes/+archive/ubuntu/pinleaf/+build/32971598
```

## Validate The Published PPA

After Launchpad publishes the package, the APT package index should be
available:

```text
https://ppa.launchpadcontent.net/robmoraes/pinleaf/ubuntu/dists/noble/main/binary-amd64/Packages.gz
```

The uncompressed `Packages` URL may return `404`; Launchpad publishes the
compressed index files. Inspect the index from the terminal with:

```bash
curl -sSL \
  https://ppa.launchpadcontent.net/robmoraes/pinleaf/ubuntu/dists/noble/main/binary-amd64/Packages.gz \
  | gzip -dc
```

On the test machine, add the PPA and install:

```bash
sudo add-apt-repository ppa:robmoraes/pinleaf
sudo apt update
sudo apt install pinleaf
```

Confirm the installed package:

```bash
apt policy pinleaf
dpkg -L pinleaf | less
```

Launch the app:

```bash
pinleaf
```

Also confirm Pinleaf appears in the desktop application launcher.

## Removal And Reinstall Test

Package removal must not remove user note data:

```bash
sudo apt remove pinleaf
```

Check that user data remains:

```bash
ls ~/.local/share/pinleaf
```

Reinstall:

```bash
sudo apt install pinleaf
pinleaf
```

Existing notes should still be available.

## If Upload Fails

If `dput` rejects the upload because the version already exists, bump the
version in `debian/changelog` and project metadata. Launchpad does not allow
reusing the same version for a new upload to the same PPA.

If the build fails in Launchpad:

1. Open the build log from the Launchpad build page.
2. Fix the packaging or dependency issue locally.
3. Bump the package version.
4. Rebuild and sign the source package.
5. Upload the new source package.

If GPG signing fails locally, verify the secret key is present:

```bash
gpg --list-secret-keys --keyid-format=long
```

Then build with the explicit fingerprint:

```bash
debuild -S -kC8F3D9976DEDB74C5C31BFC87854367646319599
```

## Finish The Release

After the PPA install test passes:

1. Update `CHANGELOG.md` with the released version.
2. Update README and GitHub Pages if install instructions changed.
3. Commit and open the PR.
4. Merge to `main`.
5. Create and push the GitHub version tag.
6. Confirm the GitHub Release workflow publishes release artifacts.
7. Confirm the PPA install path still works.

GitHub Release artifacts and Launchpad PPA publication are separate channels.
The GitHub tag drives the GitHub Release workflow. The Launchpad PPA upload is
manual until a future automation issue changes that.
