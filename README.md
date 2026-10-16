# Pinleaf

Pinleaf is a local-first desktop sticky notes app for Ubuntu-first,
GNOME-style Linux desktops, built with Python, GTK 4 and libadwaita.

Project page: [https://robmoraes.github.io/pinleaf/](https://robmoraes.github.io/pinleaf/)

The latest release is [0.8.0](https://github.com/robmoraes/pinleaf/releases/tag/v0.8.0),
with profiles, groups and scoped text search. Install it through the Ubuntu PPA,
download its Debian package from GitHub Releases or
[run from source](#development-setup).

![Pinleaf desktop overview](docs/site/assets/screenshots/overview.png)

## Supported Platform

Primary target:

- Ubuntu 24.04 LTS with GNOME or GNOME-style desktop sessions.

Supported install path:

- Ubuntu 24.04 through the Launchpad PPA `ppa:robmoraes/pinleaf`.

Expected runtime requirements:

- Python 3;
- GTK 4;
- libadwaita;
- PyGObject;
- Ayatana AppIndicator support.

Best-effort:

- other Debian/Ubuntu-compatible systems where the same dependencies are
  available.

Not currently validated:

- Fedora, Arch, openSUSE or other non-Debian distributions;
- KDE, Xfce, LXQt or other non-GNOME desktop behavior;
- Flatpak, Snap or AppImage packaging;
- macOS or Windows.

See [Known Limitations](docs/known-limitations.md) for desktop-environment and
packaging notes.

Pinleaf includes:

- independent post-it-style note windows;
- local SQLite persistence;
- autosave while typing;
- note colors;
- a main panel with note previews;
- profiles and expandable groups, with one desktop context active at a time;
- live text search across open and hidden notes, ignoring case and accents;
- an AppIndicator status menu for quick actions;
- an About dialog with maintainer, license and font credits;
- bundled handwriting-style fonts;
- bundled app/tray icon assets;
- Ubuntu PPA and local Debian package installation.

## Profiles and Groups

The following describes the development branch. Published 0.8.0 uses General
and an active-group-only desktop; Shared is scheduled for the next release.

Choose a profile in the panel's title bar. Its last ordinary group is restored,
including the valid state with no ordinary group active. Every profile has a
permanent **Shared** section (**Compartilhado** in pt-BR). Open Shared notes
appear alongside the active project's notes. Use its **+** to create a shared
note without changing projects. Shared has no Activate, Rename or Delete action.

Expand groups to browse; **Activate** switches the project's desktop notes while
keeping shared windows in place. **New profile…** starts with Shared only.
The header's **New** menu offers **New Note** and **New Group…**. New Group
creates and activates an ordinary group. New Note and tray creation target the
active ordinary group, falling back to Shared when absent. Each menu selection
is an action; it does not establish a persistent creation mode. Group creation
is kept in the header, leaving more space for notes in the panel body.

Note menus offer **Move to…** with profile/group destinations, including Shared.
Moving preserves content, appearance, timestamps and open/hidden state without
activating the destination. Context changes save pending edits. Hidden notes
remain crossed through and stay closed until explicitly opened.

Deleting a group or profile offers **Move notes** or **Delete all notes**,
including hidden notes. Deleting the active ordinary group leaves Shared only.
Transferring an active profile to an ordinary group activates that destination;
transferring to Shared resumes the destination profile's remembered project or
Shared-only context. Delete all or deleting an empty active profile requires a
replacement profile. Shared cannot be deleted independently; one profile remains.

Upgrading from 0.8.0 converts each General to Shared in place, keeping IDs and
notes. A previously active General becomes Shared-only; no unrelated project
is selected. Conflicting ordinary Shared/Compartilhado names receive a numeric
suffix and are reported in a dismissible notice. Older libraries migrate to
**Personal / Shared** (**Pessoal / Compartilhado** in pt-BR). A validated private
snapshot precedes the upgrade. See [organization and database recovery](docs/organization-and-recovery.md)
before returning to an older version.

## Search Notes

Type in **Search notes** to filter full note content. Search ignores case and
accents, so `cafe` finds `Café`. Results retain creation order and include hidden
notes. **Current context** (default) searches Shared plus the active ordinary
group, or Shared alone. **Current profile** and **All profiles** broaden scope.
Global results show the profile/group path. Opening current-profile Shared keeps
the project active; **Switch profile and open** resumes a foreign Shared's
profile. Ordinary external notes use **Activate and open**. Inspection and
expansion leave the desktop unchanged; an actual context switch resets search.

Press **Ctrl+F** to focus search. Clear it or press **Escape** to restore normal
sections and previous expansion. With no matches, use **Clear Search**.

## Backup and Restore (development branch)

Open **Main menu → Backup & Restore…** to create a local `.pinleaf-backup`
file or restore one. This unreleased feature works offline and includes the
whole library: profiles, groups, hidden notes, retained deleted records, current
context and text defaults. Pending edits are saved before capture; later edits
remain local and are not included in the captured copy.

Each creation starts with **Protect with password** off. Enable it to encrypt
that copy, then enter and confirm a password. Unprotected files are readable by
anyone with access to them; protected files require their password to restore.
Pinleaf cannot recover a forgotten backup password.

Restore validates the selected file and shows a preview. Final **Restore**
replaces the entire library. Before replacement, Pinleaf preserves the latest
current data in a private, independently restorable file under `backups/` beside
the database. Hidden/deleted notes retain their state. Cancelling the chooser or
preview leaves the current library in place. The startup-error screen also offers
local restore and preserves unreadable original database/journal files first.

The first format accepts library schema 6. Raw SQLite migration snapshots and
other portable versions are not inputs for this reader. Google Drive is the
partially delivered: the development window supports account connection, saving
backups and listing completed copies. Download/restore from Drive is next.

### Google Drive development setup

The maintainer registers a desktop OAuth client with the Google Drive API
enabled and only `https://www.googleapis.com/auth/drive.file` declared. Keep the
downloaded client JSON outside tracked files. Point development at it explicitly:

```bash
PINLEAF_GOOGLE_CLIENT_FILE=/absolute/path/to/client.json \
  XDG_DATA_HOME=/tmp/pinleaf-dev /usr/bin/python3 -m pinleaf
```

In **Backup & Restore**, choose **Connect Google Drive…**. Authorization opens
the system browser and waits up to three minutes. Cancel stops waiting. Saved
access uses the system Secret Service, separated by client/account/installation.
If the keyring is unavailable or locked, unlock it or explicitly select
**Connect for this session only**; there is no plaintext token-file fallback.
**Disconnect / Forget Saved Access** removes this installation's saved access;
it does not revoke other installations or remove Drive files. Saved credentials
are loaded when you explicitly Connect and refreshed only during deliberate
account/Drive operations, never at app startup.
In session-only mode, **Disconnect This Session** clears memory; any previously
saved access can then be removed separately with **Forget Saved Access**.
During a Drive transfer, Disconnect cancels the operation before forgetting
local access; a remotely completed copy may remain discoverable on reconnection.

**Save Backup to Drive…** captures the whole library, with password protection
initially off for each new copy. Each save creates a distinct dated file under
app-marked **Pinleaf / Backups** folders; it does not overwrite another device's
copy. Editing can continue during upload; the status identifies the capture time.
Uploads are resumable, verified by size/checksum and marked complete only after
verification. **Refresh Drive Copies** discovers complete compatible files across
marked backup folders, including from another installation using the same Google
account and OAuth client. Listing checks metadata; file contents will be validated
by the upcoming download/restore flow.

After an interrupted save, **Retry Drive Save** checks the same UUID/file ID and
continues that captured copy, including the original encrypted bytes. It does not
capture newer edits. Retry data stays in memory until success, a new save,
Disconnect or app exit; after restart, refresh discovers completed copies and a
new save creates a new attempt. Incomplete files stay excluded from the list;
there is no automatic retry, cleanup or pruning. A cancelled/lost response can
leave a remotely completed copy, which Refresh or Retry can discover. Local
backup status and the last recorded successful Drive upload are kept separately.

For Google's testing mode, add the designated account under OAuth test users.
Testing grants may expire and require Disconnect followed by Connect. The
development client override is not included in backups or packages. A registered
client resource/distribution configuration is still required before release.

## Install

### Ubuntu PPA

On Ubuntu 24.04, add the Pinleaf PPA and install with `apt`:

```bash
sudo add-apt-repository ppa:robmoraes/pinleaf
sudo apt update
sudo apt install pinleaf
```

After installation, updates are handled by the normal system update flow:

```bash
sudo apt update
sudo apt upgrade
```

Remove the package:

```bash
sudo apt remove pinleaf
```

Removing the package does not remove note data under `~/.local/share/pinleaf`.

### Debian/Ubuntu Release Package

Download the `pinleaf_*.deb` package from the release artifacts, then install it
with `apt`:

```bash
sudo apt install ./pinleaf_*.deb
```

This installs:

- `/usr/bin/pinleaf`
- `/usr/share/applications/dev.pinleaf.Pinleaf.desktop`
- Pinleaf icons under `/usr/share/icons/hicolor`
- Pinleaf Python package files and bundled resources

Remove the package:

```bash
sudo apt remove pinleaf
```

Removing the package does not remove note data under `~/.local/share/pinleaf`.

If `apt` reports that the local package download is performed unsandboxed
because the `_apt` user cannot access the `.deb`, move or copy the package to a
world-readable directory such as `/tmp` and install it from there:

```bash
cp pinleaf_*.deb /tmp/
sudo apt install /tmp/pinleaf_*.deb
```

## Development Setup

Install the system dependencies for Python, GTK 4, libadwaita and the
AppIndicator helper.

On Ubuntu 24.04:

```bash
sudo apt install \
  python3-gi \
  python3-jsonschema \
  python3-cryptography \
  python3-google-auth-oauthlib \
  python3-requests \
  python3-secretstorage \
  gir1.2-gtk-4.0 \
  gir1.2-adw-1 \
  gir1.2-ayatanaappindicator3-0.1 \
  libayatana-appindicator3-1
```

Clone the repository and run the app from the project root:

```bash
git clone https://github.com/<owner>/pinleaf.git
cd pinleaf
/usr/bin/python3 -m pinleaf
```

For isolated development data, set `XDG_DATA_HOME`:

```bash
XDG_DATA_HOME=/tmp/pinleaf-dev /usr/bin/python3 -m pinleaf
```

Pinleaf stores notes under:

```text
~/.local/share/pinleaf/pinleaf.sqlite3
```

or under:

```text
$XDG_DATA_HOME/pinleaf/pinleaf.sqlite3
```

## Local Desktop Install

For a user-local desktop launcher, run from the repository root:

```bash
scripts/install-local
```

This installs:

- `~/.local/bin/pinleaf`
- `~/.local/share/applications/dev.pinleaf.Pinleaf.desktop`
- Pinleaf icons under `~/.local/share/icons/hicolor`

The local install points to the current source checkout. If you move the
repository, run `scripts/install-local` again.

To remove the local launcher and icons:

```bash
scripts/uninstall-local
```

Uninstalling does not remove note data.

## Local Debian Package

Maintainers can build the local Debian package from the repository root.

Install packaging tools:

```bash
sudo apt install build-essential debhelper dpkg-dev
```

Build the package from the repository root:

```bash
dpkg-buildpackage -us -uc
```

Install the generated package from the parent directory:

```bash
sudo apt install ../pinleaf_*.deb
```

## Release

Maintainers publish downloadable Debian package artifacts through GitHub
Releases and publish Ubuntu packages through the Launchpad PPA.

After merging the release changes into `main`, create and push a version tag:

```bash
git switch main
git pull
git tag -a v0.8.0 -m "Release Pinleaf 0.8.0"
git push origin v0.8.0
```

The release workflow runs on `v*` tags. It runs tests, builds the local Debian
package, creates or updates the matching GitHub Release, and uploads:

- `pinleaf_*.deb`
- `pinleaf_*.buildinfo`
- `pinleaf_*.changes`

### Ubuntu PPA Upload

Maintainers publish the PPA package by uploading a signed source package to
Launchpad:

```bash
debuild -S -kC8F3D9976DEDB74C5C31BFC87854367646319599
lintian ../pinleaf_0.8.0_source.changes
dput -s ppa:robmoraes/pinleaf ../pinleaf_0.8.0_source.changes
```

After the release is approved, signatures are verified and Lintian passes,
publish the source package:

```bash
dput ppa:robmoraes/pinleaf ../pinleaf_0.8.0_source.changes
```

The PPA target is Ubuntu 24.04 LTS (`noble`).

See [Manual Launchpad PPA Publication](docs/release/launchpad-ppa.md) for tools,
GPG recovery on a replacement computer, user signing/upload configuration,
signature verification and the full publication workflow. The standard
`dput ppa:robmoraes/pinleaf` route uses FTP with a GPG-signed source package;
an SSH key is needed only when choosing SFTP.

## Test

```bash
/usr/bin/python3 -m unittest discover -s tests
/usr/bin/python3 -m compileall pinleaf tests
```

## Project Structure

Feature work follows the engineering-playbook's spec-driven workflow:
Intent -> Spec -> Clarify -> Check -> Plan -> Tasks -> Implement -> Verify.
Specifications, plans, tasks, contracts and verification evidence live in
`specs/`, with one numbered directory per feature.

```text
pinleaf/
  app.py                  GTK/libadwaita application lifecycle
  config.py               paths and resources
  fonts.py                bundled font registration
  models.py               note domain model
  storage/                SQLite schema and repository
  services/               note service and autosave
  ui/                     GTK windows, dialogs and tray controller
  resources/              CSS, fonts and icons
specs/001-desktop-sticky-notes/
  spec.md
  plan.md
  tasks.md
```

## Known Limitations

See [Known Limitations](docs/known-limitations.md).

## Fonts

Bundled fonts live in `pinleaf/resources/fonts/`.

The included Google Fonts families are distributed under the SIL Open Font
License. Their `OFL.txt` files are kept beside each font family.

## License

Pinleaf source code is licensed under the MIT License. See [LICENSE](LICENSE).
