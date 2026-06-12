# Tasks: Pinleaf project page and screenshots

## Source

- Spec: `docs/.specs/004-project-page-and-screenshots/spec.md`
- Plan: `docs/.specs/004-project-page-and-screenshots/plan.md`

## Implementation Tasks

1. Add static site skeleton.
   - Create `docs/site/index.html`.
   - Create `docs/site/styles.css`.
   - Create `docs/site/assets/screenshots/.gitkeep`.
   - Validation: files exist and open locally without a build step.

2. Add project content.
   - Include name, description, feature list, run/install commands and links.
   - Include screenshot section with clear expected filenames.
   - Validation: page is readable without screenshots.

3. Update README.
   - Add project page URL.
   - Add screenshot section only when assets exist.
   - Validation: README references the correct GitHub Pages URL.

4. Add simple tests.
   - Assert site files exist.
   - Assert README contains the project page URL.
   - Validation: include in `unittest`.

5. Manual screenshot integration.
   - Add screenshots prepared by maintainer.
   - Verify image rendering and alt text.
   - Validation: manual browser check.

## Progress

- Tasks 1-4: implemented and covered by automated tests.
- Task 5: screenshots integrated; pending manual browser/GitHub Pages verification.
