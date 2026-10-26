# Feature: Local Debian package installation

## Intent

Problem:
Pinleaf currently runs from a source checkout or from the user-local install
script. This is useful for development, but it does not provide a normal
Debian/Ubuntu installation experience.

Users or stakeholders:
Maintainer and early Linux users who want to install Pinleaf as a system
package.

Desired outcome:
A clean Debian/Ubuntu-compatible system can install Pinleaf from a locally built
`.deb` package using `apt`, with the command, desktop launcher, icons, Python
package data and runtime dependencies installed correctly.

Non-goals:
- Publishing a Launchpad PPA.
- Publishing a custom signed APT repository.
- Inclusion in Debian or Ubuntu official archives.
- Flatpak, Snap or AppImage packaging.
- Removing the existing user-local install script.

## Scope

In scope:
- Add Debian packaging metadata under `debian/`.
- Build a local `.deb` package from the repository.
- Declare build-time and runtime package dependencies.
- Install the `pinleaf` executable into the system path.
- Install the desktop launcher under `/usr/share/applications`.
- Install icons under `/usr/share/icons/hicolor`.
- Include bundled CSS, fonts, icons and Python package data.
- Preserve user note data when the package is removed.
- Document local build and install commands.

Out of scope:
- PPA account setup, upload or release automation.
- Signed APT repository metadata.
- Automatic updates beyond normal package-manager behavior.
- Cross-distribution packaging outside Debian-compatible systems.

Assumptions:
- Pinleaf remains a Python 3 GTK/libadwaita app.
- Runtime dependencies are provided by Debian/Ubuntu packages.
- User note data remains under XDG user data paths, not under package-managed
  system paths.
- The first package can target Ubuntu 24.04-style dependencies.

Dependencies:
- Python 3 packaging helpers.
- Debian packaging toolchain.
- GTK 4, libadwaita and Ayatana AppIndicator runtime packages.

## Behavior

1. A developer can build a local `.deb` package from a clean checkout.
2. Installing the package with `apt` pulls required system dependencies.
3. The installed `pinleaf` command launches the app.
4. Pinleaf appears in the desktop application launcher.
5. The launcher uses the Pinleaf icon.
6. Bundled CSS, fonts and icons are available at runtime.
7. Removing the package removes package-managed files.
8. Removing the package does not remove user note data.

## Acceptance Examples

Scenario: install local package
Given a clean checkout with packaging dependencies installed
When the maintainer builds the `.deb`
And installs it with `sudo apt install ./pinleaf_*.deb`
Then the `pinleaf` command is available
And the app launches.

Scenario: launcher integration
Given the package is installed
When the desktop application launcher is refreshed
Then Pinleaf appears with the correct icon.

Scenario: package removal
Given Pinleaf has user note data under `~/.local/share/pinleaf`
When the package is removed
Then package-managed files are removed
And the user note data remains.

## Data and Contracts

Inputs:
- Source checkout.
- Debian packaging metadata.
- System package manager.

Outputs:
- Local `.deb` package.
- Installed system command, launcher, icons and Python package files.

API/schema/event changes:
- None.

Persistence changes:
- None. User note data location must remain unchanged.

## Quality Attributes

Security:
- Do not require `sudo` during normal Pinleaf runtime.
- Package scripts must not remove user data.
- Runtime dependencies should come from distribution packages.

Reliability:
- Installed resources must resolve without depending on the source checkout.
- Package build should be reproducible enough for local release work.

Maintainability:
- Debian packaging files should be small and conventional.
- Version metadata must stay aligned with project releases.

Usability:
- Installation should use standard `apt` workflows.
- Installed app should be discoverable from the desktop launcher.

## Rollout and Operations

Migration:
- None for user note data.

Feature flag or configuration:
- None.

Rollback:
- Remove the package with `apt remove pinleaf`.

Monitoring:
- None.

