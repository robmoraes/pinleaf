# Bundled Fonts

Place app-bundled `.ttf` or `.otf` files in this directory.

Recommended font for the current note editor style:

- `Playwrite AU VIC Guides`

The application registers fonts in this directory with Fontconfig at startup,
then GTK/Pango can use them through `font-family` in `resources/styles.css`.

Keep the font license file beside the font files when bundling fonts in the
repository or distribution package.
