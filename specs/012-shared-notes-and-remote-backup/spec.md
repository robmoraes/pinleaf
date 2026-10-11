# Development package: Shared notes, creation menu and remote backup

Status: draft package brief; each workstream follows its own spec-driven steps.
Target: the next development iteration after Pinleaf 0.8.0; release version
and publication date are not assigned.
Branch: `feat/shared-groups-and-remote-backup`.

## Intent

Keep common notes available across projects within a profile, free more panel
space for the note list, and introduce a first remote save/restore integration.

This brief records the intended release package. Focused specifications own
their behavior and can proceed independently when their material questions
are resolved.

## Workstream 1: General to Shared

Status: implemented and verified in spec 013; published in draft PR #28.

The canonical behavior, migration, accepted defaults and acceptance examples
are in [spec 013: General to Shared](../013-general-to-shared/spec.md).

Confirmed direction:
- Convert the captive General into Shared in each profile.
- Display open Shared notes alongside the active ordinary group's open notes.
- Shared has no Activate action and has + to create a note directly in it.
- Preserve the deliberate-open behavior of hidden notes.

Spec 013 supersedes this brief's earlier migration recommendation to retain
General as an ordinary group and create Shared empty. Its conversion preserves
the original General's ID and note membership. Review and clarification are
tracked in [its review record](../013-general-to-shared/review.md).

## Workstream 2: Panel Creation Menu

Status: implemented and locally verified on 2026-10-11 in
[spec 014](../014-panel-creation-menu/spec.md). Publication waits for the larger
package, as requested by the maintainer.

Confirmed behavior:
- **NEW-01:** The header's New control opens an action menu containing New Note
  and New Group. Choosing an action does not establish a persistent creation mode.
- **NEW-02:** New Note uses the creation-destination rules from spec 013.
- **NEW-03:** New Group opens the current profile's existing group-creation
  flow, retaining Create and activate and its validation/cancellation behavior.
- **NEW-04:** Remove the standalone New group action row from the body so the
  note list receives that space. Preserve keyboard and tray creation entry points.

Acceptance outline:
Opening New exposes both actions; New Note creates at the agreed destination;
New Group creates and activates an ordinary group; the body has no separate
New group row. Cancellation retains the previous context.

## Workstream 3: First Remote Integration

Include a first remote save/restore integration after agreeing its provider and
behavior. S3-compatible storage remains a candidate. The earlier
[Cloud Sync Ideas](../../docs/ideas/cloud-sync.md) are exploration, not an
implementation contract.

Decisions owned by the maintainer before planning this workstream:
1. Provider and explicit backup/restore versus scheduled backup or synchronization.
2. Local export/import workflow and the library data included in a backup.
3. Restore replacement/merge behavior, conflicts, retention and recovery.
4. Encryption, credential storage, offline behavior and actionable failures.

The focused remote specification must include concrete round-trip and failure
acceptance examples before a technical plan adds dependencies or application
network calls. Record consequential architecture choices in an ADR and the
remote data format in a machine-readable contract.

## Delivery Boundary

Follow Intent -> Spec -> Clarify -> Check -> Plan -> Tasks -> Implement -> Verify
for each workstream. Remote-provider selection does not block specification of
the local Shared feature. Split implementation into reviewable slices while
keeping the intended release package together.

This package brief and its focused specs are planning artifacts. Application
implementation, version metadata, release PR, tag and package publication are
separate subsequent work.
