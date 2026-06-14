# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-06-14

### Added

- Added note window geometry persistence for supported fields, including
  restored note size and safe handling for compositor-limited positions.
- Added per-note font selection with bundled and generic system font choices.
- Added note header auto-hide behavior for unfocused note windows while keeping
  the header area stable.
- Added compact note toolbar controls for font and color selection.
- Added specs for local note geometry, per-note appearance, header auto-hide,
  and future AI/cloud sync ideas.

### Changed

- Improved note shutdown handling so open note window sizes are saved when the
  app exits.
- Refined note chrome to reduce visual weight when notes are not focused.
- Reworked sticky note windows to use an empty draggable header area with
  compact controls.
- Changed note editing to use horizontal scrolling instead of automatic line
  wrapping.
- Reduced bundled custom fonts to Dancing Script while keeping generic font
  choices available.
- Aligned the main panel `New` action to the left side of the header.

### Fixed

- Fixed open note window size not being persisted when Pinleaf exited through
  the application shutdown path.
- Fixed unreadable tooltip text on dark system themes.
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

[Unreleased]: https://github.com/robmoraes/pinleaf/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/robmoraes/pinleaf/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/robmoraes/pinleaf/releases/tag/v0.1.0
