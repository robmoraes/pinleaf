# Manual Launchpad PPA Publication

This document describes the manual Pinleaf publication flow for the Launchpad
PPA.

It assumes the maintainer already has:

- a Launchpad account;
- OpenPGP/GPG key registered and verified in Launchpad;
- the personal PPA created at `ppa:robmoraes/pinleaf`;
- local terminal access on Ubuntu 24.04 or a compatible Ubuntu system.

The standard `dput ppa:robmoraes/pinleaf` route uses FTP. Launchpad identifies
the uploader through the source package's GPG signature. SSH setup is needed
when choosing SFTP instead; see the
[official upload guide](https://ubuntu.com/docs/launchpad/user/how-to/packaging/ppa-package-upload/).

Release **0.9.0 is published on
[GitHub](https://github.com/robmoraes/pinleaf/releases/tag/v0.9.0)**. Launchpad
accepted its signed `noble` source upload and is building it; PPA publication
is pending. See the [release record](0.9.0.md) for evidence and current status.
The examples below document that upload. Versions 0.8.0 and 0.9.0 have already
been uploaded and must not be reused for another source upload.

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
sudo apt install --no-install-recommends \
  build-essential \
  debhelper \
  dpkg-dev \
  devscripts \
  dput \
  lintian \
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

## Recover GPG On A Replacement Computer

Keep backups outside the repository. Import the public and private exports
from their actual backup location; enter the private key's existing passphrase
when GPG requests it:

```bash
gpg --import /path/to/backup/launchpad-public.asc
gpg --import /path/to/backup/launchpad-private.asc
gpg --list-secret-keys --fingerprint C8F3D9976DEDB74C5C31BFC87854367646319599
```

Compare the full fingerprint above with the key registered in the maintainer's
[Launchpad account](https://launchpad.net/~robmoraes/+editpgpkeys). Restoring the
same key preserves that registration. The current backup expires on 2028-06-14.

Keep the `.rev` certificate for emergency revocation; do not import it during
recovery. Retain a private copy under GPG's revocation directory:

```bash
install -d -m 0700 ~/.gnupg/openpgp-revocs.d
install -m 0600 \
  /path/to/backup/C8F3D9976DEDB74C5C31BFC87854367646319599.rev \
  ~/.gnupg/openpgp-revocs.d/C8F3D9976DEDB74C5C31BFC87854367646319599.rev
```

For the maintainer's own recovered key, owner trust can be restored locally:

```bash
printf '%s:6:\n' C8F3D9976DEDB74C5C31BFC87854367646319599 | gpg --import-ownertrust
```

Test a local signature before discarding a temporary transfer copy:

```bash
launchpad_check_dir=$(mktemp -d)
printf '%s\n' 'Local Launchpad signing recovery check' > "$launchpad_check_dir/check.txt"
gpg --armor --local-user C8F3D9976DEDB74C5C31BFC87854367646319599 \
  --output "$launchpad_check_dir/check.txt.asc" --detach-sign "$launchpad_check_dir/check.txt"
gpg --verify "$launchpad_check_dir/check.txt.asc" "$launchpad_check_dir/check.txt"
rm "$launchpad_check_dir/check.txt.asc" "$launchpad_check_dir/check.txt"
rmdir "$launchpad_check_dir"
```

Keep the original offline backup. After recovery and validation, a temporary
transfer directory can be removed. The operational key remains under
`~/.gnupg`; future signing may request the same passphrase.

## Configure User Signing And Uploads

Merge this setting into `~/.gnupg/gpg.conf` to choose the default GPG signing key:

```text
default-key C8F3D9976DEDB74C5C31BFC87854367646319599
```

Merge this setting into `~/.devscripts` for `debsign`:

```bash
DEBSIGN_KEYID=C8F3D9976DEDB74C5C31BFC87854367646319599
```

The standard `ppa:robmoraes/pinleaf` target works with dput's supplied PPA
configuration. To also provide the explicit alias used in the local setup,
add this section to `~/.dput.cf`:

```ini
[pinleaf-ppa]
fqdn = ppa.launchpad.net
method = ftp
incoming = ~robmoraes/ubuntu/pinleaf/
login = anonymous
allow_unsigned_uploads = 0
```

Protect the user configuration and verify that the signing key and upload alias
are recognized:

```bash
chmod 0700 ~/.gnupg
chmod 0600 ~/.gnupg/gpg.conf ~/.devscripts ~/.dput.cf
debsign --help
dput -H
```

On 2026-10-10 the replacement computer passed default-key signing, independent
`gpgv` verification, encryption/decryption, and `debsign` verification of the
`.dsc`, `.buildinfo` and `.changes` files. Both PPA targets passed `dput -s`.
This was local setup validation; no source package was uploaded.

## Replacement computer qualification — 2026-10-16

The Ubuntu 26.04 development computer was prepared from the maintainer's
private transfer backup. The public key fingerprint was checked before import
and independently matched the key listed on the public Launchpad account API.
The private key was restored into the user's GPG keyring; the revocation
certificate was retained with private permissions, never imported. Default GPG
signing, `DEBSIGN_KEYID` and the `pinleaf-ppa` dput alias were configured.
No private key, passphrase or revocation contents were added to this repository.

Installed `devscripts` and `dput` with their required dependencies. On this
Ubuntu version, optional `ubuntu-dev-tools` requires `dput-ng`, which conflicts
with classic `dput`; installing those two together failed dependency resolution
without changing installed packages. The optional bundle was omitted. Existing
build tools and Lintian were retained; Pinleaf itself was not installed.

Completed checks:

- Local detached signing and independent `gpgv` verification passed.
- A disposable source-only build targeting `noble` passed.
- `debsign` used the configured default key and signed `.dsc`, `.buildinfo`
  and `.changes`; all three signatures matched the expected fingerprint.
- Strict source Lintian passed with no warnings or errors.
- Both `dput -s ppa:robmoraes/pinleaf` and `dput -s pinleaf-ppa` checked
  signatures/hashes and ended with `Simulated upload.` No files were uploaded.

The disposable build retained **0.8.0 only for local tooling qualification**.
That version has already been published and must never be uploaded again.
The actual release must use a new version and freshly rebuilt artifacts from
its tagged commit. At that checkpoint, publication remained deferred pending
Google branding approval, production OAuth status and the normal release checks.
The current 0.9.0 preparation is tracked in [its release checklist](0.9.0.md).
Server acceptance and remote build success can only be confirmed during the
eventual real upload.

The private transfer ZIP remains ignored, with mode 0600. It contains both the
private key and its passphrase; retain an offline backup and move the temporary
transfer archive out of the working copy when convenient. Its passphrase was
used through an inherited file descriptor, never a command-line argument or
printed output. Future signing may request that passphrase again.

## Release Checklist

Start from a clean and updated `main` branch:

```bash
git switch main
git pull
git status -sb
```

Create a short-lived release or packaging branch:

```bash
git switch -c release/0.9.0
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
pinleaf (0.9.0) noble; urgency=medium

  * Keep Shared notes visible alongside the active project in each profile.
  * Add the header New Note and New Group menu.
  * Add local backup and replacement restore with optional password protection.
  * Add manual Google Drive backup and restore with browser OAuth and keyring.
  * Preserve libraries with validated previews, recovery copies and schema-6
    migration snapshots; include the new runtime dependencies and manual.

 -- Carlos R Moraes <carlos.moraes.as@gmail.com>  Mon, 26 Oct 2026 18:55:09 -0300
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
dpkg-deb -I ../pinleaf_0.9.0_all.deb
dpkg-deb -c ../pinleaf_0.9.0_all.deb | less
```

Run `lintian` on the binary build:

```bash
lintian ../pinleaf_0.9.0_amd64.changes
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
../pinleaf_0.9.0.dsc
../pinleaf_0.9.0.tar.xz
../pinleaf_0.9.0_source.buildinfo
../pinleaf_0.9.0_source.changes
```

Verify the signatures:

```bash
gpg --verify ../pinleaf_0.9.0.dsc
gpg --verify ../pinleaf_0.9.0_source.buildinfo
gpg --verify ../pinleaf_0.9.0_source.changes
```

The signature should be from the Launchpad-registered key.

Run `lintian` on the source upload:

```bash
lintian ../pinleaf_0.9.0_source.changes
```

The source upload should be clean before publishing.

Run Lintian explicitly even if `debuild` exits successfully: `debuild` can report
Lintian errors without failing the source-build command. Resolve those errors
before continuing to a real upload.

## Check And Simulate The Upload

Before uploading for real, run `dput` checks:

```bash
dput -s ppa:robmoraes/pinleaf ../pinleaf_0.9.0_source.changes
```

The simulation should show uploads to:

```text
ppa.launchpad.net:~robmoraes/pinleaf
```

With the optional local alias, the equivalent simulation is:

```bash
dput -s pinleaf-ppa ../pinleaf_0.9.0_source.changes
```

It resolves to `ppa.launchpad.net:~robmoraes/ubuntu/pinleaf/`. A successful
simulation ends with `Simulated upload.` and sends no files. Simulation checks
local signatures, hashes and destination selection; server acceptance and builds
are checked only after an actual release upload.

## Upload To Launchpad

Upload the signed source package:

```bash
dput ppa:robmoraes/pinleaf ../pinleaf_0.9.0_source.changes
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

The build page provides the build log and generated files. As a historical
reference, the successful Ubuntu 24.04 (`noble`) build for release `0.8.0` was:

```text
https://launchpad.net/~robmoraes/+archive/ubuntu/pinleaf/+build/33831012
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

Publish the two channels in this order:

1. Prepare `release/0.9.0`, promote `CHANGELOG.md`, and update package metadata,
   README and GitHub Pages. Keep the actual PPA version explicit until it changes.
2. Run local checks and open the release PR.
3. Merge to `main`, then create and push `v0.9.0`.
4. Confirm the GitHub Release workflow publishes the Debian artifacts.
5. Build and sign the source package from the tagged commit, verify its
   signatures, run Lintian and simulate the PPA upload with `dput -s`.
6. Upload to Launchpad when publication is authorized, then confirm its build,
   APT index and install test.
7. Update README, this guide and GitHub Pages with the published PPA version.

GitHub Release artifacts and Launchpad PPA publication are separate channels.
The GitHub tag drives the GitHub Release workflow. The Launchpad PPA upload is
manual until a future automation issue changes that.
