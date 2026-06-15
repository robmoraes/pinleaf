# Feature: Ubuntu PPA publication

## Intent

Problem:
Pinleaf can already be installed from a locally built `.deb` and from GitHub
Release artifacts, but users still need to manually download package files for
each release.

Users or stakeholders:
Maintainer and early Ubuntu users who want Pinleaf to install and update through
the normal APT repository workflow.

Desired outcome:
Pinleaf is published to the maintainer's Launchpad PPA so a clean Ubuntu system
can install it with `add-apt-repository`, `apt update` and `apt install`.

Non-goals:
- Inclusion in Debian or Ubuntu official archives.
- Creating a Launchpad project team for the first PPA iteration.
- Publishing a custom self-hosted APT repository.
- Flatpak, Snap or AppImage packaging.
- Automating PPA upload from GitHub Actions in the first iteration.
- Replacing GitHub Release `.deb` artifacts.

## Scope

In scope:
- Use the personal Launchpad PPA `ppa:robmoraes/pinleaf`.
- Prepare Debian packaging metadata for Launchpad source-package builds.
- Define the first PPA versioning and Ubuntu target-series strategy.
- Build a signed source package locally.
- Upload the source package with `dput`.
- Validate the Launchpad build result.
- Validate installation from the PPA on Ubuntu.
- Document the PPA installation path in README and GitHub Pages after the PPA
  package is proven.
- Keep GitHub Release `.deb` downloads available as an alternative install path.

Out of scope:
- Team-owned PPA namespace such as `ppa:pinleaf/stable`.
- Fully automated source-package signing and upload.
- Private package repository hosting.
- Cross-distribution packaging beyond Ubuntu-compatible APT packages.

Assumptions:
- The first PPA upload uses the maintainer's personal Launchpad account.
- The maintainer's GPG key is registered in Launchpad and available locally.
- Local packaging tools are installed on the maintainer machine.
- Pinleaf remains an architecture-independent Python package.
- Runtime dependencies are available from Ubuntu repositories for the target
  Ubuntu series.

Dependencies:
- Launchpad account `robmoraes`.
- Launchpad PPA `ppa:robmoraes/pinleaf`.
- GPG key:
  `C8F3D9976DEDB74C5C31BFC87854367646319599`.
- Local tools:
  `devscripts`, `debhelper`, `dput`, `ubuntu-dev-tools`, `build-essential`.
- Existing Debian package metadata from
  `docs/.specs/008-debian-package/spec.md`.

## Behavior

1. The maintainer can build a signed source package from a clean checkout.
2. The source package can be uploaded with:
   `dput ppa:robmoraes/pinleaf <source.changes>`.
3. Launchpad accepts the upload and builds the binary package.
4. A clean Ubuntu system can add the PPA and install Pinleaf.
5. A PPA-installed Pinleaf launches from the terminal and desktop launcher.
6. Removing or upgrading the PPA package does not remove user note data.
7. Documentation presents the PPA install path as the preferred Ubuntu install
   path after validation.

## Acceptance Examples

Scenario: source package build
Given the maintainer has packaging tools and the registered GPG key available
When the maintainer builds the source package
Then a signed source `.changes` file is produced for upload to Launchpad.

Scenario: Launchpad upload
Given the signed source package exists
When the maintainer runs `dput ppa:robmoraes/pinleaf <source.changes>`
Then Launchpad accepts the upload and starts or schedules the package build.

Scenario: install from PPA
Given Launchpad has published the package
When a clean Ubuntu system runs:

```bash
sudo add-apt-repository ppa:robmoraes/pinleaf
sudo apt update
sudo apt install pinleaf
```

Then the `pinleaf` command is available
And the app launches.

Scenario: package removal
Given Pinleaf has user note data under `~/.local/share/pinleaf`
When the PPA-installed package is removed
Then package-managed files are removed
And the user note data remains.

## Data and Contracts

Inputs:
- Source checkout.
- Debian packaging metadata.
- Maintainer GPG key.
- Launchpad PPA.

Outputs:
- Signed source package.
- Launchpad-built binary package.
- APT-installable Pinleaf package from `ppa:robmoraes/pinleaf`.

API/schema/event changes:
- None.

Persistence changes:
- None. User note data location must remain unchanged.

## Quality Attributes

Security:
- Source uploads must be signed with the maintainer's registered GPG key.
- Do not add telemetry or network behavior to the app itself.
- Package install/removal must not remove user note data.

Reliability:
- Launchpad builds must not depend on local generated files.
- Runtime dependencies must be declared so APT can resolve them.

Maintainability:
- Keep PPA-specific decisions documented near the packaging spec.
- Avoid CI upload automation until the manual PPA process is proven.

Usability:
- Ubuntu users should have a short, copyable install flow.
- Documentation should clearly separate PPA install from GitHub Release
  download fallback.

## Rollout and Operations

Migration:
- None for user note data.

Feature flag or configuration:
- None.

Rollback:
- Remove the package with `sudo apt remove pinleaf`.
- Remove the PPA with `sudo add-apt-repository --remove ppa:robmoraes/pinleaf`.

Monitoring:
- Launchpad upload status.
- Launchpad build logs.
- Manual installation and launch validation.
