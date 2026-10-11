# Feature: Convert General into Shared profile notes

Status: implemented and locally verified on 2026-10-11.
Current phase: Verify / delivery, following the pre-approved plan and tasks.
Package: [next development iteration](../012-shared-notes-and-remote-backup/spec.md).
Target: after Pinleaf 0.8.0; release version and date are not assigned.

## Intent

Problem:
A note may be useful in several project groups within the same profile. Today,
switching groups removes that note from the desktop unless it is duplicated or
moved each time. General currently behaves like any other active context.

Users or stakeholders:
People using project groups inside work, freelance or personal profiles.

Desired outcome:
Replace the captive General group with Shared. Its open notes accompany the
active ordinary group in the same profile. For example, one AWS resource-tags
post-it remains available while switching between Kubernetes and Docker Swarm.

## Scope

In scope:
- Convert each live profile's existing General into Shared, including its notes.
- Shared visibility, direct creation through +, moving notes and container deletion.
- Profiles with no active ordinary group, persistence, startup and scoped search.
- Naming, localization, migration preservation, snapshots and compatibility.

Out of scope:
- The header New Note / New Group menu, tracked separately in the package brief.
- Remote backup, synchronization, accounts, telemetry or network calls.
- Multiple memberships, nested groups, tags or new controls on sticky windows.
- A restore/trash interface, hard purge or new platform positioning guarantees.

Dependencies:
The existing [profile/group behavior](../011-profiles-and-groups/spec.md),
local SQLite storage, autosave, note actions and literal text search remain the
baseline except where this specification explicitly changes them. Historical
spec 011 and its schema-5 contract continue to describe the shipped release.

## Accepted Decisions

Confirmed direction:
- General is replaced by a captive Shared in each profile.
- Shared accompanies the active group and has no Activate action.
- Shared's + creates a note directly in it.
- Individually hidden notes retain their deliberate-open behavior.

This specification defines conversion literally: the original General becomes Shared
with its notes and identity. It supersedes the earlier recommendation to keep
General as an ordinary group and create Shared empty.

Accepted product defaults:
- Use Shared in English and Compartilhado in pt-BR.
- A profile can have no active ordinary group; only its shared notes then appear.
- Preserve that state when migrating an active General, instead of selecting
  an unrelated project group automatically.
- Rename conflicting ordinary groups with a numeric suffix during migration.
- Search the visible context under the label Current context / Contexto atual.

On 2026-10-11 the maintainer accepted the recommendation: ordinary New Note
commands create in Shared when no ordinary group is active. Plan, tasks and
implementation through completion were authorized together.

## Behavior

### Identity and organization

- **SH-01:** Every live profile has exactly one captive Shared. Its identity
  does not depend on the displayed language. Shared cannot be renamed or
  deleted independently; deleting its profile includes Shared and its notes.
- **SH-02:** Each note belongs to exactly one group. Shared notes are common
  to the groups of their owning profile, not to other profiles. Moving a note
  changes its membership; it does not create copies.
- **SH-03:** Shared cannot be activated or stored as an active ordinary group.
  Reject an explicit attempt to activate it without changing context. Expanding
  Shared in the panel does not activate anything.
- **SH-04:** Reserve Shared and Compartilhado for the captive group using the
  existing trimmed, NFC/case-folded uniqueness rule. General and Geral become
  available names for ordinary groups; they have no special behavior.

### Active context and desktop

- **CTX-01:** One profile is active application-wide. It has zero or one active
  ordinary group. A profile with ordinary groups may also have none active,
  for example immediately after conversion of its active General.
- **CTX-02:** A new library starts with Personal/Pessoal containing only Shared
  and no active ordinary group. Creating a profile follows the same rule.
  Creating an ordinary group retains Create and activate.
- **CTX-03:** Remember each profile's last ordinary group, including the valid
  absence of one. Returning to a profile or restarting restores that context.
  A reference to a removed ordinary group becomes absent; Shared is never
  substituted as an active group. If the active profile cannot be recovered,
  use the first remaining live profile by stable ID and its saved valid context.
- **CTX-04:** Display a note exactly when it is live, individually marked open,
  belongs to the active profile, and belongs to either Shared or the active
  ordinary group. With no ordinary group active, display only open Shared notes.
- **CTX-05:** Switching ordinary groups preserves shared editor windows that
  remain eligible, including pending edits, size and existing restorable
  position. Do not close/recreate, duplicate or refocus them merely because
  the ordinary group changed. Reuse any note window common to both contexts.
- **CTX-06:** Switching profiles removes the previous profile's windows and
  restores the new profile's eligible windows. Context removal does not mark
  notes hidden. Closing/reopening the panel does not change desktop visibility.
- **CTX-07:** Hiding a shared note keeps it hidden across group/profile switches
  and restarts. It remains struck through in the panel until deliberately
  opened. Deleted notes remain absent from the panel, search and desktop.
- **CTX-08:** Save pending edits and restorable state before a context, membership
  or container change. A required save, preparation or transaction failure
  preserves the previous context, memberships and available unsaved text.
  Report an actionable error and allow retry without a partially switched desktop.

### Panel and creation

- **UX-01:** Shared is the first expandable section in the active profile's
  group list, with its localized name, live-note count and + action. It has no
  Activate button, Active marker, rename or independent delete action. Ordinary
  groups retain independent expansion, activation and management actions.
- **UX-02:** The title identifies the profile and active ordinary group. With
  none active, show Shared notes only / Somente notas compartilhadas. Shared's
  section explains that its notes accompany this profile's groups. Sticky
  windows retain their existing post-it appearance.
- **UX-03:** In the current profile's Shared section, clicking a note row or
  pressing Enter explicitly opens that note without changing ordinary context.
  Retain Open, Hide when applicable, Move and Delete actions. A hidden note's
  deliberate Open action changes its individual flag; browsing its row does not.
- **CR-01:** Shared's + creates and opens a note in the active profile's Shared,
  using the existing note appearance defaults. Preserve the active ordinary
  group or its absence. The accessible name and tooltip identify the destination
  as New shared note / Nova nota compartilhada.
- **CR-02:** Ordinary note creation from the header, keyboard shortcut or tray
  targets the active ordinary group. With none active, create
  in Shared. Browsing or expanding a group does not change the destination.

### Movement and deletion

- **FLOW-01:** Shared is an available Move destination in each live profile.
  Preserve note ID, content, appearance, timestamps and open/hidden state.
  Moving does not activate a destination group or profile. Recompute visibility
  from CTX-04; hidden notes stay hidden at every destination.
- **FLOW-02:** Moving an open note into Shared of the active profile displays
  it immediately. Moving it from Shared to an inactive ordinary group removes
  its window until that group is activated. If both memberships are eligible
  in the current context, retain the same window.
- **DEL-01:** Existing Move notes / Delete all notes choices, confirmation,
  preview revalidation and soft-deletion semantics remain. A profile deletion
  includes Shared, all ordinary groups and their retained notes. At least one
  live profile with Shared must remain.
- **DEL-02:** Deleting an active ordinary group keeps the same profile with no
  active ordinary group; its open Shared notes remain. Deleting an inactive
  group leaves the current context unchanged. Clear any last-used references
  to a deleted ordinary group without choosing a different project implicitly.
- **DEL-03:** When deleting an active profile and transferring to an ordinary
  group, activate that destination. When transferring to Shared, activate its
  owning profile and restore that profile's last ordinary group or its absence.
  With Delete all notes or an empty profile, require the existing explicit
  replacement-profile choice. The confirmation describes the resulting context.

### Search and explicit opening

- **SEARCH-01:** The default search scope is Current context / Contexto atual:
  Shared plus the active ordinary group, or just Shared when none is active.
  Include hidden notes, exclude deleted notes and return each note once. Keep
  existing full-content, case/accent-insensitive literal matching.
- **SEARCH-02:** Current profile and All profiles retain their scope and group
  breadcrumbs. Identify Shared with its localized label. Searching and
  expanding results do not change active context or open notes automatically.
- **SEARCH-03:** Opening a Shared result in the current profile preserves its
  ordinary context. For another profile, offer Switch profile and open; resume
  that profile's saved ordinary context or its absence, then open the note.
  Never activate Shared. Ordinary-group results retain Activate and open.
- **SEARCH-04:** A successful profile or ordinary-group change clears the query
  and resets scope to Current context. Failed changes retain query and context.
  Clearing search restores normal sections and their prior expansion state.

## Data and Migration Contract

The [migration outcome contract](contracts/general-to-shared.json) records the
domain invariants. The technical plan must supply the target schema version,
schema definition, transaction boundaries and compatibility checks before code.

- **MIG-01:** For every live schema-5 profile, convert its General in place:
  retain profile ID, group ID and every note's group membership. Change the
  captive group's name/role to Shared; do not retain a second built-in General
  or create an extra ordinary group automatically.
- **MIG-02:** Preserve every existing note field exactly, including note ID,
  content, appearance, geometry, timestamps, individual open/hidden flag and
  deletion state. Include retained soft-deleted notes. Preserve app settings,
  user profile names and non-conflicting ordinary groups. Do not alter deleted
  profiles or their tombstoned groups.
- **MIG-03:** Preserve the active profile and valid ordinary-group context.
  Replace active/last-used references to the converted General with no active
  ordinary group. Do not auto-open a different project's notes to repair that
  context. General notes previously marked open become visible as Shared even
  when an ordinary group remains active; manually hidden ones stay hidden.
- **MIG-04:** A live ordinary group named Shared or Compartilhado retains its
  ID and notes. Rename it to its original name plus the first available suffix
  ` (N)`, starting at 2 and checking normalized uniqueness. For example, Shared
  becomes Shared (3) if Shared (2) is already in use. Do not merge those notes
  with the converted General or silently overwrite either group.
- **MIG-05:** Upgrades from earlier supported schemas preserve the existing
  legacy-field defaults and create initial Personal/Pessoal -> Shared membership
  for all retained notes. Their resulting context has no active ordinary group.
  Reopening a migrated library validates it without duplicate groups, repeated
  renaming, note retimestamping or additional migration snapshots.
- **MIG-06:** Before an existing-library upgrade, create and validate the private
  recovery snapshot. Snapshot, validation or migration failure leaves the old
  library usable without a partial conversion. Publish the new schema version
  only after all preservation, membership and context checks succeed together.
- **MIG-07:** After successful conversion, show a dismissible informational
  notice in the panel explaining that General is now Shared and its open notes
  accompany the profile's groups. Report any renamed groups without note content.
  Do not require a confirmation to open the converted library.

## Acceptance Examples

### AC-01: Convert existing General without losing notes

Given Pessoal's General contains open, hidden and soft-deleted notes
When the schema-5 library is upgraded
Then that same group ID represents Shared
And every note retains its ID, membership and all existing field values
And the hidden/deleted notes keep those states.

### AC-02: Preserve context when General was active

Given General was active and Kubernetes is another group with open notes
When General is converted
Then Pessoal stays active with no active ordinary group
And only its open Shared notes appear
And Kubernetes notes appear only after Kubernetes is explicitly activated.

### AC-03: Keep a shared AWS tags window across projects

Given Kubernetes is active and Shared has an open AWS tags note
When the user edits that note and activates Docker Swarm
Then the ordinary project notes change to Docker Swarm
And the same AWS tags window remains open with its edits preserved
And Shared is never activated.

### AC-04: Preserve hidden notes and profile boundaries

Given work and personal profiles each have open and hidden shared notes
When the user switches profiles, returns and restarts Pinleaf
Then only the restored profile's eligible windows appear
And hidden shared notes remain hidden and struck through until explicitly opened.

### AC-05: Create directly in Shared without changing groups

Given Kubernetes is active
When the user selects Shared's +
Then a new note opens in Shared with the existing appearance defaults
And Kubernetes remains active
And ordinary New Note still creates a Kubernetes note.

### AC-06: Use a profile containing only Shared

Given a new profile has only Shared and no active ordinary group
When the user creates a note through + or New Note
Then the note belongs to Shared and opens without activating Shared
And creating a Kubernetes group later activates it alongside the shared note.

### AC-07: Move notes according to resulting visibility

Given Kubernetes is active and Docker Swarm is inactive
When an open note moves from Docker Swarm to Shared
Then its window appears immediately and Kubernetes remains active
When the note moves from Shared to Docker Swarm
Then its window leaves the desktop
And its individual open flag remains unchanged
And a hidden note stays hidden through both moves.

### AC-08: Delete a group while retaining Shared

Given Kubernetes is active with an open shared AWS tags note
When Kubernetes is deleted using either existing note-disposal choice
Then the same profile remains with no active ordinary group
And the shared AWS tags note retains its membership and window
And Shared has no independent delete action.

### AC-09: Transfer an active profile into another profile's Shared

Given Pessoal is active and Freelancer's last ordinary group is Empresa X
When Pessoal is deleted with Move notes to Freelancer / Shared
Then all retained notes move without being revived or retimestamped
And Freelancer becomes active with Empresa X and its eligible shared notes
And no context reference treats Shared as an active group.

### AC-10: Search and open Shared in another profile

Given Kubernetes is active and Shared contains Café AWS
When the user searches CAFE in Current context
Then the shared note matches once with the existing accent-insensitive rules
When the user explicitly opens an All profiles result in Freelancer / Shared
Then Freelancer's saved ordinary context is restored and the result opens
And merely searching never changed the desktop.

### AC-11: Handle names and language without merging groups

Given General, Shared and Shared (2) exist in a schema-5 profile
When the library is converted
Then the original General becomes captive Shared
And the ordinary Shared becomes Shared (3), retaining its own ID and notes
When the application language changes to pt-BR
Then the captive label becomes Compartilhado without another group being created.

### AC-12: Preserve the library on failure and on repeat startup

Given a disposable legacy library and injected snapshot or migration failure
When conversion is attempted
Then its original schema, data and context remain intact
When the failure is removed, conversion is retried successfully and Pinleaf restarts
Then no duplicate Shared, repeated collision suffix or note timestamp change occurs.

### AC-13: Keep the previous context on failed saves

Given a shared editor has an unsaved change and saving is forced to fail
When a profile switch, group switch or note move is attempted
Then context and membership remain unchanged
And the editor retains its unsaved text and an actionable retry error is shown.

## Quality Attributes and Rollout

Security and privacy:
This feature remains local. Diagnostics and migration notices must not contain
note text. Keep the existing private data and snapshot permissions.

Accessibility:
Keyboard users can expand Shared, create via its named + and invoke note actions.
Announce profile, ordinary context or its absence, hidden state and expansion.
Retain existing shortcuts, focus-return behavior, theme and reduced-motion support.

Reliability and performance:
Use the same visibility rule for startup, switching, movement and deletion.
Maintain at most one editor window per eligible note and preserve existing
platform limitations. The plan must benchmark shared/ordinary context switches
with the existing representative library; this spec claims no execution results.

Compatibility and recovery:
Use a newer schema version so older Pinleaf binaries refuse the upgraded
library rather than modifying it using General's old semantics. The plan must
define a validated snapshot-restore drill with the app stopped and preservation
of newer DB/WAL/SHM recovery files. A downgrade cannot recover later edits from
an older snapshot automatically. Keep fresh, legacy, failed and repeated-start
cases in the migration verification scope.

Release:
Update current product documentation during implementation. Prepare version
metadata, tag and package publication later in the release workflow.

## Clarification Outcome and Delivery

No material product questions remain. CR-02 is accepted: create directly in
Shared when no ordinary group is active. The [plan](plan.md), [tasks](tasks.md)
and [review](review.md) govern implementation and verification. Remote-provider
selection does not block this local slice.

Implementation and verification results: [execution record](execution.md).
