# Tasks: Pinleaf local desktop install

## Source

- Spec: `docs/.specs/002-local-desktop-install/spec.md`
- Plan: `docs/.specs/002-local-desktop-install/plan.md`

## Progress

- Tasks 1-4: implemented and covered by automated tests.
- Task 5: pending manual desktop verification.

## Implementation Tasks

1. Add `scripts/install-local`.
   - Validate the script is run from the repository root.
   - Create user-local bin, applications and icon directories.
   - Install wrapper, desktop file and icons.
   - Run optional cache updates when available.
   - Validation: shell syntax check and temporary-home install test.

2. Add `scripts/uninstall-local`.
   - Remove installed wrapper, desktop file and icons.
   - Keep user note data untouched.
   - Run optional cache updates when available.
   - Validation: shell syntax check and temporary-home uninstall test.

3. Add script tests.
   - Use `tempfile` or shell temp directories for `HOME`.
   - Assert installed files exist.
   - Assert uninstall removes install files but leaves data directory.
   - Validation: include in the existing `unittest` suite.

4. Update README.
   - Add local install instructions.
   - Add uninstall instructions.
   - Document that moving the checkout requires re-running install.
   - Validation: README reflects actual script names and paths.

5. Manual desktop verification.
   - Install locally.
   - Launch through terminal wrapper.
   - Launch through app menu.
   - Confirm icon behavior.
   - Uninstall locally.
