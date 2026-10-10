# Review: Profiles and note groups

## Workflow

Current phase: Verify. Product decisions are recorded, including container deletion
with transfer/delete choices. The [technical plan](plan.md),
[migration contract](contracts/migration-v5.json) and
[adopted ADR](adr-001-context-storage-and-recovery.md) describe the local implementation.
The [ordered tasks](tasks.md) and [maintained verification cases](verification.md)
are maintained. Automated and native X11 checks are recorded in
[execution evidence](execution-2026-10-10.md) and the final
[automated desktop qualification](automation-2026-10-10.md). X11 keyboard,
fault/retry, external AT-SPI names/states and normal startup qualification pass.
Wayland, human Orca speech/usability and the documented stress/diagnostic
follow-ups remain. The implementation was merged through
[PR #24](https://github.com/robmoraes/pinleaf/pull/24), with successful CI and Pages
workflows. Release publication remains outside scope.

Source standard:
`~/wspace/engineering-playbook/engineering-playbook/architecture/spec-driven-development.md`.
Related standard:
`~/wspace/engineering-playbook/engineering-playbook/testing/test-case-standards.md`.

## Confirmed Product Rules

- Profiles contain groups; groups contain notes.
- A profile has a captive General/Geral group.
- New notes go to the active group; notes can move between groups.
- Activation changes which context's open notes appear on the desktop.
- Individually hidden notes stay hidden and struck through until explicitly
  opened. Context switching preserves their existing stored state.
- Profile/group identification belongs in the panel.
- Existing notes migrate to Personal/Pessoal -> General/Geral.
- Profile/group creation uses Create and activate.
- Search defaults to the active group, offers profile/global scopes and clears
  on an actual context change.
- Profile/user-created-group deletion offers transfer to another group or
  existing note-deletion semantics. General remains protected independently,
  and at least one live profile must remain.
- Implementation and feature-branch review were subsequently authorized;
  release publication remains outside scope.

## Accepted UX Direction

- Profile title button with an anchored selection menu.
- Expandable groups with an explicit Activate action and independent expansion.
- Multiple group sections can remain expanded for comparison.
- Explicit Activate and open for notes outside the active context.

## Clarification Outcome

No material product questions remain for planning. The maintainer confirmed
migration, creation and search defaults and added container deletion to scope.
DEL-01..07 and AC-13..18 record the resulting lifecycle, confirmation and failure
behavior. The UX document includes the deletion flow.

The implementation uses schema 5 with required membership, one transaction owner,
dedicated context disposal and local pre-upgrade recovery snapshots. The execution
record connects these choices to independent migration, fault and GTK checks.

## Quality Checklist

- [x] Intent, scope, assumptions and non-goals are stated.
- [x] Requirements have stable behavior identifiers.
- [x] Concrete acceptance examples cover visibility, context, hidden state,
      migration, movement, naming and failed saves.
- [x] Product decisions and proposed technical design are distinguishable.
- [x] Persistence invariants and migration preservation are specified.
- [x] Native component availability checked with GTK 4.14/libadwaita 1.5.
- [x] Primary GNOME references distinguish source guidance from Pinleaf choices.
- [x] UX direction accepted in conversation.
- [x] Resolve material product questions with the maintainer.
- [x] Produce technical plan, migration contract and proposed architecture decision.
- [x] Check plan consistency and derive ordered implementation tasks.
- [x] Derive maintained verification cases using the Test Case Standards.
- [x] Implement and run automated/isolated-X11 verification against the spec.
- [x] Automate real X11 keyboard, fault/retry, resize and AT-SPI exports.
- [x] Measure normal and stress startup on the real X11 desktop and retain all samples.
- [ ] Complete Wayland and human Orca speech/usability qualification; retain the
      strict stress-boundary and private-bus tray diagnostic follow-ups.

## Evidence Boundary

The interactive preview illustrates navigation UX with synthetic data. It is
not proof of desktop lifecycle behavior. The separate execution record contains
GTK tests, native X11 observations and migration/rollback evidence. Container
deletion remains absent from the earlier HTML prototype but is implemented in
GTK. Passing automated checks does not substitute for unexecuted desktop checks.

## Planning Validation

Historical checks at the Plan phase, before implementation authorization:

- Parsed the migration JSON and matched its source versions and preserved note
  columns to the inspected schema-4 implementation using a temporary in-memory store.
- Checked local Markdown targets/anchors and trailing whitespace, including new
  untracked documents, and ran `git diff --check`.
- Confirmed 18 acceptance scenarios and traceability identifiers in the contract.
- No feature implementation, migration on user data or desktop verification was run.

## Task Definition Validation

Historical checks at the Tasks phase, before implementation authorization:

- Defined 18 pending tasks with prerequisites, behavior traceability and completion
  criteria; every prerequisite precedes its dependent task.
- Mapped all 18 acceptance examples to implementation and validation tasks.
- Defined 12 maintained risk cases with traceability, risk, classification,
  automation state, objective, reproducible data, scenario and cleanup.
- Checked task/case references, local links/anchors and document whitespace.
- No implementation task or feature test is marked completed/executed by these checks.
