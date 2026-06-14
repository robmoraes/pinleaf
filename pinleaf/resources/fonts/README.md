# Bundled Fonts

Place app-bundled `.ttf` or `.otf` files in this directory.

Curated bundled fonts available in the note font selector:

- `Dancing Script`
- `Kavoon`
- `Londrina Shadow`
- `Nabla`
- `Press Start 2P`
- `Style Script`

The application registers fonts in this directory with Fontconfig at startup,
then GTK/Pango can use them through `font-family` in `resources/styles.css`.

Keep the font license file beside the font files when bundling fonts in the
repository or distribution package.

The currently bundled curated fonts use the SIL Open Font License, Version 1.1.
Keep each family's `OFL.txt` beside its font files.
