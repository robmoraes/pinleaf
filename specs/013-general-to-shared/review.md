# Review: General to Shared

Current phase: Verify / delivery. Maintainer accepted the defaults and pre-approved the
plan and tasks on 2026-10-11, authorizing the complete Shared implementation.

Source standards:
- `~/wspace/engineering-playbook/engineering-playbook/architecture/spec-driven-development.md`
- `~/wspace/engineering-playbook/engineering-playbook/testing/test-case-standards.md`

## Product Agreement

The maintainer requested a captive Shared per profile instead of General,
shown alongside the active ordinary group, without an Activate action, and
with + for direct creation. Existing hidden-note behavior remains.

The [spec](spec.md) interprets conversion as retaining the original General's
identity and notes. It explicitly replaces the earlier draft recommendation
to create Shared empty and retain General as an ordinary group.

The empty ordinary context, localized label, name-collision suffix, Current
context search label and New Note fallback to Shared are accepted.

## Quality Checklist

- [x] Scope focuses on the local Shared feature; remote integration and the New
      menu are outside this slice.
- [x] Confirmed direction and proposed defaults are distinguishable.
- [x] Behavior covers nullable ordinary context, creation, visibility, hiding,
      movement, deletion, search and restart.
- [x] Migration preserves IDs, note values, deleted-note state and memberships.
- [x] Conversion handles pre-existing Shared names, locale changes, snapshots,
      rollback and repeat startup.
- [x] Concrete acceptance examples and a migration outcome contract are present.
- [x] Maintainer confirms the no-active-group creation fallback and reviews defaults.
- [x] Check completed; technical plan and target schema contract prepared.
- [x] Ordered tasks and maintained verification cases derived from the plan.
- [x] Implementation and verification evidence produced.

## Verification Boundary

Implementation evidence is recorded in [execution.md](execution.md): 186 tests,
native X11 keyboard/lifecycle/restart checks, private AT-SPI export, schema-5
recovery and real-compositor startup passed. No user database was modified.
Wayland and human Orca qualification remain outside the demonstrated results.

Initial documentation-only checks (before implementation):

Documentation checks on 2026-10-10:
- Local links between the package brief, focused spec, review and JSON contract
  resolve to existing files.
- The JSON contract parses and its traceability IDs exist in the specification.
- Its preserved-column list covers every field in the current Note model.
- Requirement and acceptance IDs are unique; 13 concrete scenarios are present.
- Trailing whitespace and the staged diff are clean.
