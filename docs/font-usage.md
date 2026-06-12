# Font Usage

Pinleaf loads bundled `.ttf` and `.otf` fonts from:

```text
pinleaf/resources/fonts/
```

The app CSS currently applies note editor fonts in:

```text
pinleaf/resources/styles.css
```

Update both selectors when changing the active note font:

```css
.note-editor {
  font-family: "Dancing Script", cursive;
}

.note-editor text {
  font-family: "Dancing Script", cursive;
}
```

The current selected note font is `Dancing Script`.

## Bundled Font Examples

These examples mirror the Google Fonts snippets for the bundled families.
They are documentation examples, not app CSS classes.

```css
.tangerine-regular {
  font-family: "Tangerine", cursive;
  font-weight: 400;
  font-style: normal;
}

.tangerine-bold {
  font-family: "Tangerine", cursive;
  font-weight: 700;
  font-style: normal;
}

.league-script-regular {
  font-family: "League Script", cursive;
  font-weight: 400;
  font-style: normal;
}

.dancing-script-400 {
  font-family: "Dancing Script", cursive;
  font-weight: 400;
  font-style: normal;
}

.updock-regular {
  font-family: "Updock", cursive;
  font-weight: 400;
  font-style: normal;
}

.cedarville-cursive-regular {
  font-family: "Cedarville Cursive", cursive;
  font-weight: 400;
  font-style: normal;
}
```

## Checking Family Names

The CSS family name must match the font's internal family name, not
necessarily the file name. To inspect a font:

```bash
fc-scan pinleaf/resources/fonts/Font_Family/File.ttf | rg family
```
