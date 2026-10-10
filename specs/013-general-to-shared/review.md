# Review: General to Shared

Current phase: Spec / Clarify. No plan, tasks or application changes.

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

The specified empty ordinary context, localized label, name-collision suffix
and Current context search label are product defaults submitted for review.
CR-02's no-active-group creation fallback has been asked as a clarification;
the draft proposes creating directly in Shared.

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
- [ ] Maintainer confirms the no-active-group creation fallback and reviews defaults.
- [ ] Check completed; technical plan and target schema contract prepared.
- [ ] Ordered tasks and maintained verification cases derived from the plan.
- [ ] Implementation and verification evidence produced.

## Verification Boundary

The acceptance examples define future expected behavior. Documentation and
contract checks do not demonstrate implementation, migration execution or
desktop behavior. Application tests were not rerun for this documentation-only
specification change.

Documentation checks on 2026-10-10:
- Local links between the package brief, focused spec, review and JSON contract
  resolve to existing files.
- The JSON contract parses and its traceability IDs exist in the specification.
- Its preserved-column list covers every field in the current Note model.
- Requirement and acceptance IDs are unique; 13 concrete scenarios are present.
- Trailing whitespace and the staged diff are clean.
