# Feature: Shared profile notes, panel creation menu and remote backup

Status: draft; scope captured, material questions remain open.
Current phase: Spec / Clarify. No implementation plan or tasks yet.
Target: the next development iteration after Pinleaf 0.8.0; release version
and publication date are not assigned.
Branch: `feat/shared-groups-and-remote-backup`.

## Intent

Problem:
Some notes are useful across several projects within the same profile. Moving
between project groups should keep those common notes available without
duplicating them. The separate New group button also consumes space that
could be used by the panel's note list.

Users or stakeholders:
People who organize project notes into profiles and groups, and want to save
and restore their library through a first remote integration.

Desired outcome:
Show shared profile notes alongside the active project's notes, consolidate
panel creation actions, and specify a first remote save/restore integration
before implementing it.

## Scope

This development package has three workstreams:

1. A built-in Shared group per profile, replacing General as the captive
   group. Existing General data and ordinary-group fallback require a migration
   decision before planning.
2. A New action menu in the panel header containing New Note and New Group,
   replacing the standalone New group button in the body.
3. A first remote backup/restore integration. Provider, remote behavior and
   local backup/restore workflow remain to be decided. S3-compatible storage
   is a candidate, not a selected provider.

No application code, schema migration, network behavior, release preparation
or publication is authorized by this draft itself. The current request is to
prepare the branch and record scope. Subsequent implementation follows the
spec-driven workflow.

Dependencies:
- Profiles, groups and scoped search delivered in spec 011.
- Existing local SQLite data, autosave and deliberate-open behavior.
- Existing GTK 4 / libadwaita environment on Ubuntu 24.04.
- Earlier remote-storage exploration in [Cloud Sync Ideas](../../docs/ideas/cloud-sync.md).

## Confirmed Behavior

### Shared notes

- **SH-01:** Each profile has one built-in Shared group. Its notes accompany
  the active ordinary group in that profile. Shared is scoped to its owning
  profile and does not expose its notes in other profiles.
- **SH-02:** Shared has no Activate action and never becomes the active group.
  Expanding or collapsing its panel section only changes the panel list.
- **SH-03:** Shared has a + action in its section header. It creates and opens
  a note directly in that profile's Shared group without changing the active
  ordinary group.
- **SH-04:** A shared note marked open remains on the desktop when switching
  between ordinary groups in the same profile. Preserve its window and pending
  edits instead of closing and recreating it during that switch.
- **SH-05:** Switching profiles removes the previous profile's shared windows
  and displays the new profile's shared notes that are individually marked
  open. Preserve each note's open/hidden state across profile switches and
  restarts.
- **SH-06:** Hidden shared notes remain struck through in the panel and stay
  off the desktop until deliberately opened. Membership in Shared does not
  override hiding.
- **SH-07:** Shared cannot be renamed or deleted independently of its profile.
  Notes can move between Shared and ordinary groups through the existing move
  workflow. Each note still belongs to exactly one group.
- **SH-08:** Organization remains in the panel. Sticky windows gain no tags,
  group badges or other organizational controls.

### Panel creation actions

- **NEW-01:** The header's New control opens an action menu with New Note and
  New Group. These are commands; selecting one does not establish a persistent
  creation mode.
- **NEW-02:** New Note creates a note in the active ordinary group. The Shared
  + action is the direct path for creating a shared note.
- **NEW-03:** New Group opens the existing group-creation flow for the current
  profile, retaining the agreed Create and activate behavior.
- **NEW-04:** Remove the standalone New group action row from the body so the
  note list receives the available space. Preserve the existing keyboard and
  tray entry points for creating an ordinary note.

### Remote integration boundary

- **REM-01:** Include the first remote save/restore integration in this
  development package after its provider and behavior are agreed. The earlier
  cloud-sync idea does not settle this decision.
- **REM-02:** Provider choice, credentials, data scope, restore behavior and
  failure handling must have an approved specification before a technical
  plan introduces dependencies or application network calls.

## Acceptance Examples

### AC-01: Reuse an AWS tags note across projects

Given one profile contains Kubernetes and Docker Swarm groups
And its Shared group contains an open note with standard AWS resource tags
When the user switches from Kubernetes to Docker Swarm
Then the ordinary project notes change to Docker Swarm
And the same AWS tags window remains open with its edits preserved
And Shared never becomes active.

### AC-02: Create a shared note directly

Given Kubernetes is active
When the user selects + in Shared
Then a new note is created and opened in Shared
And Kubernetes remains active
And selecting New Note from the header still creates a Kubernetes note.

### AC-03: Preserve hidden shared notes

Given a shared note was deliberately hidden
When the user switches ordinary groups or restarts Pinleaf
Then the note stays hidden and struck through
Until the user explicitly opens it.

### AC-04: Keep shared notes within their profile

Given a work profile and a personal profile each have open shared notes
When the user switches from work to personal
Then work shared windows leave the desktop without becoming individually hidden
And the personal profile's open shared notes appear.

### AC-05: Consolidate creation in the header

Given the panel is showing its note list
When the user opens New
Then New Note and New Group are available
And there is no standalone New group row above the list
And New Group retains the existing validation and Create and activate flow.

## Data, Quality and Rollout Constraints

- Shared requires stable identity independent of its eventual localized label.
  Define the data contract and migration after resolving the questions below.
- Preserve existing note content, appearance, membership intent and open/hidden
  state. Do not silently make all existing General notes visible across groups.
- Keep the existing save-before-switch guarantee: failed saves retain the
  previous context and unsaved text rather than partially switching windows.
- Expose a keyboard-operable creation menu and a named Shared + action that
  identifies its creation destination to assistive technology.
- Remote backup and restore must specify how profiles, groups, shared notes,
  hidden notes and existing local data are preserved. Concrete round-trip,
  failure and recovery acceptance examples depend on the selected behavior.
- Define migration snapshots, compatibility and recovery before implementation.
- Release metadata, tag and PPA upload are separate future release work.

## Open Questions

All questions below are owned by the maintainer and must be resolved during
Clarify, before planning the affected workstream.

1. **Existing General and ordinary-group fallback:** the current recommendation
   is to create Shared empty and retain existing General as an ordinary group.
   Confirm this migration, the initial ordinary group for a new profile, and
   behavior when its last ordinary group is deleted. Shared cannot be the
   fallback because it cannot be activated.
2. **Search and cross-context open:** the current recommendation is for Active
   group search to include Shared without duplicate results. Confirm its label
   and how opening a shared search result from another profile selects that
   profile's ordinary context.
3. **Panel labeling:** confirm Shared's pt-BR label, first-position section
   presentation and how the header explains its notes accompany the active group.
4. **First remote provider and product workflow:** choose the integration and
   whether this first iteration provides explicit backup/restore, scheduled
   backup or broader synchronization. Multi-device merge is not assumed.
5. **Remote data and recovery contract:** agree local export/import, backup
   scope, restore replacement/merge behavior, retention, encryption, credential
   storage and offline/failure behavior. Record consequential architecture
   choices in an ADR and the remote data format in a contract.

## Next Spec-Driven Step

Resolve the material questions, complete concrete remote acceptance examples,
then perform Check before creating plan.md and tasks.md. The workstreams can
use separate focused specifications and implementation branches as they become
ready while remaining part of the same intended release package.
