# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.6.0] - 2026-06-15

### Added

- Added Ubuntu PPA publication support for installing Pinleaf with
  `add-apt-repository` and `apt install`.
- Added source package upload documentation for the maintainer Launchpad PPA.

### Changed

- Updated package version metadata to `0.6.0`.
- Updated Debian source-package metadata for Ubuntu 24.04 LTS (`noble`) PPA
  uploads.

## [0.5.0] - 2026-06-14

### Added

- Added a GitHub Actions release workflow that builds the Debian package and
  uploads `.deb`, `.buildinfo` and `.changes` artifacts to GitHub Releases when
  version tags are pushed.

### Changed

- Documented the maintainer release flow for publishing downloadable Debian
  package artifacts.

## [0.4.0] - 2026-06-14

### Added

- Added local Debian package metadata for building and installing Pinleaf with
  `apt install ./pinleaf_*.deb`.

### Changed

- Updated the project page and README with local Debian package installation
  instructions.

## [0.3.0] - 2026-06-14

### Added

- Added curated bundled note fonts: Kavoon, Londrina Shadow, Nabla, Press Start
  2P and Style Script.
- Added a Monospace note font option.

### Changed

- Reordered the note font menu to show default/system fonts first, separated
  from bundled custom fonts.
- Changed font menu options to render each font label using its corresponding
  font.

## [0.2.1] - 2026-06-14

### Added

- Added compact note toolbar controls for font and color selection.

### Changed

- Reworked sticky note windows to use an empty draggable header area with
  compact controls.
- Changed note editing to use horizontal scrolling instead of automatic line
  wrapping.
- Reduced bundled custom fonts to Dancing Script while keeping generic font
  choices available.

### Fixed

- Fixed unreadable tooltip text on dark system themes.

## [0.2.0] - 2026-06-13

### Added

- Added note window geometry persistence for supported fields, including
  restored note size and safe handling for compositor-limited positions.
- Added per-note font selection with bundled and generic system font choices.
- Added note header auto-hide behavior for unfocused note windows while keeping
  the header area stable.
- Added specs for local note geometry, per-note appearance, header auto-hide,
  and future AI/cloud sync ideas.

### Changed

- Improved note shutdown handling so open note window sizes are saved when the
  app exits.
- Refined note chrome to reduce visual weight when notes are not focused.
- Aligned the main panel `New` action to the left side of the header.

### Fixed

- Fixed open note window size not being persisted when Pinleaf exited through
  the application shutdown path.
- Documented GNOME/Wayland limitations for exact note window positioning.

## [0.1.0] - 2026-06-12

### Added

- Initial Pinleaf MVP as a local-first Linux sticky notes app built with Python,
  GTK 4 and libadwaita.
- Added independent note windows with local SQLite persistence, autosave, note
  colors and a main panel with note previews.
- Added AppIndicator status menu, bundled app icons, bundled handwriting-style
  fonts and an About dialog.
- Added user-local desktop install and uninstall scripts.
- Added unit tests, Python compile checks and GitHub Actions CI.
- Added GitHub Pages project page with screenshots.
- Added repository contributor guidelines.

[Unreleased]: https://github.com/robmoraes/pinleaf/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/robmoraes/pinleaf/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/robmoraes/pinleaf/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/robmoraes/pinleaf/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/robmoraes/pinleaf/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/robmoraes/pinleaf/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/robmoraes/pinleaf/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/robmoraes/pinleaf/releases/tag/v0.1.0
