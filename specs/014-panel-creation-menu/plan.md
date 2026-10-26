# Plan: Panel creation menu

The maintainer authorized this slice on 2026-10-11. All product decisions are
already recorded in [spec.md](spec.md); no separate approval gate is needed.

1. Replace the header Gtk.Button with a named Gtk.MenuButton. Use the existing
   action-popover builder so both items dismiss the menu before invoking their
   action. Keep the label New, with New Note and New Group… inside; retain the
   existing English panel naming convention.
2. Route New Note to on_create_note; route New Group… to the existing NameDialog
   through _present_dialog and execute. No domain/storage/controller changes.
   The native menu-button behavior handles keyboard navigation and dismissal;
   existing dialog handling owns validation, focus and retry.
3. Remove the body New group button; the expanding stack/scroller takes the
   space. Keep search, profile selector and Shared + unchanged.
4. Verify real creation destinations, cancellation and validation through the
   menu with focused GTK integration checks. Run native keyboard selection,
   Escape and narrow/dark layout checks on private X11 with disposable data;
   inspect screenshots and clean up the test app/helper/session.
5. Update README, Unreleased and package status. Run the complete unittest
   suite, compileall and diff checks and record results against maintained
   [verification cases](verification.md). Commit locally on the existing feature
   branch; no push, PR edit, version bump, tag, release or hosted pipeline.

The action menu was chosen over a persistent dropdown mode because the agreed
workflow calls for choosing an action each time. No architecture boundary,
data migration, dependency, credentials or observability change is involved.
Rollback is reverting the panel change; no data conversion is required.
