# Plan: Pinleaf project page and screenshots

## Spec Link

- Source spec: `docs/.specs/004-project-page-and-screenshots/spec.md`

## Approach

Use a static GitHub Pages site under:

```text
docs/site/
  index.html
  styles.css
  assets/
    screenshots/
      .gitkeep
```

GitHub Pages can later be configured to publish from the repository branch and
the `docs/site` folder if using a workflow, or the files can be copied/adapted
to a Pages source supported by GitHub settings. The static files should not
depend on a build step.

## Content

The page should include:

- Pinleaf name and short description.
- Feature list.
- Screenshot section with placeholders until files are available.
- Development setup/run command.
- Link to known limitations.
- Link to GitHub repository.

## Screenshot Convention

Use:

```text
docs/site/assets/screenshots/panel.png
docs/site/assets/screenshots/note.png
docs/site/assets/screenshots/about.png
```

The initial page may show placeholders or hide missing images until screenshots
are added manually.

## README Update

Add a project page link:

```text
https://robmoraes.github.io/pinleaf/
```

Add screenshot references only after images exist.

## Validation

Automated:
- ensure static files exist;
- ensure README contains the project page URL;
- run existing unit tests and compileall.

Manual:
- open `docs/site/index.html` in a browser;
- add screenshots and confirm they render;
- enable GitHub Pages in repository settings or through a later deployment
  workflow.

## Risks

- GitHub Pages source configuration may require a later workflow if the chosen
  folder is not directly selectable.
- Screenshot filenames may change after the maintainer provides final images.
