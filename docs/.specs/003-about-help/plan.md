# Plan: Pinleaf about and help

## Spec Link

- Source spec: `docs/.specs/003-about-help/spec.md`

## Approach

Use libadwaita's native about dialog/window from the existing GTK app.

Add static metadata in a small module:

```text
pinleaf/metadata.py
```

Add a UI helper:

```text
pinleaf/ui/about.py
```

Expose the action from the main window header bar through a menu button.

## Metadata

Initial constants:

- app name: `Pinleaf`
- app id: `dev.pinleaf.Pinleaf`
- version: `0.1.0-dev`
- build date: `TBD`
- maintainer: `robmoraes`
- maintainer website: `https://about.robmoraes.dev.br`
- license: `MIT`
- font license credit: `Bundled Google Fonts are licensed under the SIL Open Font License.`

Dynamic version/build metadata is deferred.

## UI

Use a header-bar menu in the main panel with an `About Pinleaf` item. This keeps
the primary create action visible while avoiding extra clutter.

The about helper should prefer `Adw.AboutDialog` when available and fall back to
`Adw.AboutWindow` if needed by the installed libadwaita version.

## Validation

Automated:
- metadata constants are present and non-empty;
- about helper imports with GTK/libadwaita available.

Manual:
- launch app;
- open main panel;
- activate `About Pinleaf`;
- verify displayed text and links.

## Risks

- libadwaita versions differ in about APIs. Keep a compatibility fallback.
- External link activation is delegated to the desktop environment.
