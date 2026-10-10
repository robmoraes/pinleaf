# Feature: Profiles and note groups

Status: implemented locally; automated, real X11 and isolated AT-SPI checks run.
Current phase: Verify. Desktop qualification and the startup stress target have
remaining boundaries recorded in [execution evidence](execution-2026-10-10.md)
and the final [automated desktop qualification](automation-2026-10-10.md).
Target: the next development iteration of Pinleaf 0.8.0.

## Intent

Problem:
As the note library grows, notes from employment, freelance work, personal life
and individual projects compete for space and attention on the desktop.

Users or stakeholders:
People who use Pinleaf across several areas of life and want to resume the
relevant notes when changing projects.

Desired outcome:
Organize notes as **profile -> group -> note**. One group is active at a time;
its notes marked open appear on the desktop. Organization happens in the main
panel, keeping sticky notes visually simple.

Non-goals:
- Tags, arbitrary nesting, multiple memberships, accounts or access control.
- Cloud synchronization, sharing, project-specific typography or permissions.
- Changing the existing deliberate-open behavior of hidden notes.
- Publishing a release during specification work.

## Scope

In scope:
- Create and rename profiles and groups from the panel.
- A permanent General group in each profile, displayed as Geral in pt-BR.
- Activate groups; restore the last active group when returning to a profile.
- Browse groups and their notes in expandable sections of the current list area.
- Move an individual note to another group, including in another profile.
- Delete profiles and user-created groups, choosing to move their notes to an
  existing destination or remove all their notes.
- Integrate existing text search with context and preserve note row actions.
- Remember context across application restarts and migrate existing notes.

Out of scope for this proposal:
- Moving whole groups between profiles, bulk moves outside container deletion
  and drag-and-drop.
- Nested groups, pinning, reminders and full application translation.
- A trash/recovery UI or a new permanent data-purge policy.

Agreed defaults:
- The initial, renameable profile is Personal (Pessoal in pt-BR), with existing
  notes assigned to its General group. No example business profiles are seeded.
- User-supplied names remain as entered when the application language changes.

Dependencies:
- Existing local SQLite storage, note service and autosave.
- Existing GTK 4 / libadwaita environment for Ubuntu 24.04.
- Existing text search in spec 010.

## Behavior

### Organization and identity

- **CTX-01:** Every group belongs to exactly one profile. Every note belongs to
  exactly one group. The hierarchy has exactly two organizational levels.
- **CTX-02:** Every profile has exactly one built-in General group. Its stable
  identity is independent of its translated label. It cannot be renamed or
  removed independently; deleting its parent profile also removes it from the
  panel. General is the initial active group of a new profile.
- **CTX-03:** Profile names are unique across profiles; group names are unique
  within a profile. Trim outer whitespace, reject blank names and names over
  80 Unicode code points, and compare uniqueness using Unicode canonical
  normalization and case folding. Reserve General/Geral as group names for the
  built-in group.
- **CTX-04:** One group is active application-wide. Its owner is the active
  profile. Returning to a profile activates its last-used valid group, falling
  back to General if no valid last-used group exists.

### Desktop visibility and persistence

- **CTX-05:** A note is displayed on the desktop exactly when it is not deleted,
  belongs to the active group and is individually marked open.
- **CTX-06:** Deactivating a group removes its windows from the desktop while
  preserving each note's open/hidden state, content and appearance. This is a
  context operation, not the existing Hide Note action.
- **CTX-07:** Deliberately hiding a note keeps it hidden on group switches and
  restarts. It stays struck through in the panel until an explicit open action.
- **CTX-08:** Activating a group displays its notes already marked open. An
  empty group or one containing only hidden notes displays no sticky windows.
- **CTX-09:** Before switching context, save pending note edits and existing
  restorable window state. If any required save fails, retain the previous
  active context and its windows; keep unsaved text available, report the
  failure and allow retry. Do not present a partially switched desktop.
- **CTX-10:** Persist the active group and each profile's last-used group. On
  restart, show only the saved active group's individually open notes.

### Panel and navigation

- **UX-01:** The header identifies the active profile and active group. Profile
  selection is directly available there; creating/renaming profiles is a
  secondary management flow.
- **UX-02:** The panel's note list area shows expandable group sections for the
  active profile. Each header identifies the group, note count and activation
  state. General comes first, then other groups alphabetically; notes retain
  their existing newest-created-first order.
- **UX-03:** Expanding/collapsing a section only changes the panel.
  A distinct Activate action changes desktop context. Multiple groups may be
  expanded for comparison. Collapsing the active group does not hide its notes.
- **UX-04:** A note in an inactive group remains available for inspection in
  the list. Its context-changing action is explicitly labeled Activate and
  open. Merely expanding a group, searching or moving a note does not activate
  it. An active-group note retains the normal explicit open action.
- **UX-05:** Opening a hidden note explicitly marks it open, removes its
  strikethrough and shows it in the active group's desktop context.
- **UX-06:** Empty group and empty search states offer appropriate creation or
  clear-search actions. Persistent active-context feedback remains visible
  even when its group section is collapsed or absent from search results.
- **UX-07:** Long names and narrow windows preserve access to selection,
  activation and row actions. Context and hidden/open states are communicated
  with text or accessible names, not only colors or strikethrough.

### Creating, moving and searching

- **FLOW-01:** A new note created from any entry point, including the tray,
  belongs to the active group and follows existing new-note open behavior.
  Browsing an inactive group does not change this destination.
- **FLOW-02:** Profile/group creation forms use an explicit Create
  and activate action. A new profile includes General. Saving a rename keeps
  identities, memberships, context and note states intact.
- **FLOW-03:** Move Note chooses a destination profile and group, shows the
  complete destination and requires an explicit Move action. Moving a note
  preserves its content, open/hidden state, appearance and creation order.
- **FLOW-04:** Moving an open note out of the active group removes its window
  from this desktop; moving an open note into it displays that note. Moving a
  hidden note keeps it hidden at either destination. The active context stays
  unchanged. Save pending edits before a move; a failure leaves membership and
  context unchanged and keeps the editor available.
- **FLOW-05:** Search defaults to the active group and offers Current
  profile and All profiles scopes. Search retains spec 010's full-content,
  case/accent-insensitive literal matching, including hidden notes and excluding
  deleted notes. Search never activates a context by itself.
- **FLOW-06:** Current-profile results identify their group. All-profile results
  include a profile/group breadcrumb. Opening a result from another context
  uses the explicit Activate and open action. Clearing search restores normal
  sections and the pre-search expansion state.
- **FLOW-07:** Switching context clears the current query and returns the scope
  to Active group, so a previous context's query does not conceal new notes.
  Search itself and accordion expansion are independent of note visibility.

### Deleting profiles and groups

- **DEL-01:** A user-created group or a profile can be deleted. The flow names
  the container and offers Move notes to another group or Delete all notes.
  Profile deletion covers every group in that profile, including General.
  A container without non-deleted notes can be deleted without selecting a note
  destination; any retained deleted notes stay deleted with the removed container.
- **DEL-02:** Move notes requires one existing destination group outside the
  container being removed, including in another profile. All notes receive
  that membership, including retained soft-deleted notes, without reviving
  them. Preserve content, appearance, timestamps and individual open/hidden
  state. Profile deletion merges notes into the selected group; it does not
  recreate the source groups at the destination.
- **DEL-03:** Delete all notes uses the existing note-deletion semantics. Notes
  disappear from the panel, search and desktop; this does not introduce a new
  hard-purge or restore feature. Already-deleted notes stay deleted. Deleted
  containers are no longer offered for navigation, creation or movement.
- **DEL-04:** General cannot be deleted independently. At least one live
  profile with its General group must remain. Deleting the last profile is
  unavailable with an explanation to create another profile first.
- **DEL-05:** Deleting the active user-created group activates General in the
  same profile. Deleting the active profile with Move notes activates the
  selected destination group. With Delete all notes, explicitly select a
  remaining profile in the dialog; resume its last valid group, or General.
  Deleting an inactive container preserves the active context. Any last-used
  group removed by deletion falls back to its profile's General. An empty active
  profile also requires the explicit remaining-profile selection.
- **DEL-06:** Before confirmation, show the affected profile/group, count of
  non-deleted notes (including hidden notes), destination and resulting active
  context where applicable. Move notes is the initial choice; Delete all notes
  is never preselected. Cancellation is the default final response; removal
  of notes uses an explicitly destructive final action. Invalid destinations
  or changed affected membership require review before retrying.
- **DEL-07:** Save pending edits and restorable state of affected visible notes
  before deleting or moving their container. Changes to membership, note
  deletion, containers and saved context succeed together. Any required save
  or transaction failure leaves the organization and active context unchanged,
  keeps editors and pending text available, and offers an actionable retry.

## Acceptance Examples

### AC-01: Switch groups without changing manually hidden notes

Given Seventh / LGPD is active with two open notes and one hidden note
When the user activates Seventh / Agenda and then returns to LGPD
Then the same two LGPD notes appear on the desktop
And the hidden note remains hidden and struck through in the panel.

### AC-02: Switch profiles and resume the last group

Given Seventh last used LGPD and Pessoal last used Financeiro
When the user selects Pessoal and then Seventh from the profile selector
Then Financeiro becomes active first and LGPD becomes active on return
And only the selected group's individually open notes are displayed.

### AC-03: Browse without changing desktop context

Given LGPD is active with two displayed notes
When the user expands Agenda, then collapses LGPD in the panel
Then the same LGPD notes stay on the desktop
And new notes created from the panel or tray still belong to LGPD.

### AC-04: Explicitly open a hidden note in another group

Given LGPD is active and Agenda contains a hidden note
When the user chooses Activate and open on that Agenda note
Then Agenda becomes active and that note becomes individually open
And other Agenda notes that were hidden remain hidden.

### AC-05: Keep edits available after a failed switch

Given a displayed LGPD note contains pending text not yet saved
And saving that text fails during context change
When the user tries to activate Agenda
Then LGPD remains active and its editor retains the pending text
And a visible error offers retry without presenting Agenda as active.

### AC-06: Move across profiles without activating the destination

Given an open note belongs to active Seventh / LGPD
When the user moves it to Freelancer / Empresa X - DevOps
Then LGPD remains active and that note leaves the current desktop
And it is shown when Empresa X - DevOps is later activated.

### AC-07: Preserve hidden state through a move

Given a hidden note belongs to Seventh / LGPD
When the user moves it to active Pessoal / Financeiro
Then the note is listed struck through in Financeiro
And it does not appear on the desktop until explicitly opened.

### AC-08: Search outside the active context

Given LGPD is active and Financeiro contains a note with Café in its full text
When the user searches cafe with All profiles scope
Then the result identifies Pessoal / Financeiro
And LGPD remains active until the user chooses Activate and open.

### AC-09: Restore context after restarting

Given Pessoal / Dieta is active with one open note and one hidden note
And another profile has notes individually marked open
When Pinleaf is restarted
Then Dieta remains active and only its one open note appears on the desktop.

### AC-10: Migrate an existing library

Given an existing database has open, hidden and soft-deleted notes
When the profile/group migration succeeds
Then all notes receive a valid initial General membership
And that group belongs to the initial Personal / Pessoal profile
And existing content, IDs, appearance, timestamps, deletion and open flags
remain unchanged
And only the previously open, non-deleted notes are displayed.

### AC-11: Change language without duplicating General

Given a profile contains its built-in General group
When the application uses pt-BR labels
Then that same group is displayed as Geral with the same notes and identity
And a second default group is not created.

### AC-12: Reject invalid names without changing context

Given a profile already contains a group named LGPD
When the user submits a blank name, an 81-code-point name, or lgpd as a new group
Then a field-level explanation identifies the validation failure
And no group is created and the active desktop context remains unchanged.

### AC-13: Delete a group and move its notes

Given active Seventh / LGPD contains an open note, a hidden note and a deleted note
When the user deletes LGPD and moves its notes to Freelancer / Geral
Then LGPD disappears and Seventh / Geral becomes active
And all three notes belong to the destination with their original open/deleted states
And the moved open note appears only when Freelancer / Geral becomes active.

### AC-14: Delete the active profile and its notes

Given Seventh is active and Pessoal last used Financeiro
When the user chooses Delete all notes for Seventh, selects Pessoal as the next
profile and confirms the stated note count
Then Seventh and all its groups disappear from navigation
And its notes disappear from search and the desktop using existing deletion semantics
And Pessoal / Financeiro becomes active with only its individually open notes visible.

### AC-15: Protect General and the last profile

Given Pessoal is the only remaining profile
When the user inspects the actions for Pessoal and its General group
Then General has no independent delete action
And profile deletion is unavailable with an explanation
And the active context and existing notes remain unchanged.

### AC-16: Preserve organization after a failed deletion

Given an affected open note has pending edits
When its required save or the container-deletion transaction fails
Then no group, profile, membership or note-deletion change is committed
And the prior active context and editor remain available for retry.

### AC-17: Create and activate a profile

Given Seventh / LGPD is active with an open note
When the user creates Freelancer with Create and activate
Then Freelancer / General becomes active and is initially empty
And the LGPD note keeps its individually open state for a later return.

### AC-18: Clear search on context change

Given a query and All profiles scope are selected
When the user activates another group
Then the query is cleared and the scope returns to Active group
And merely expanding a different group would have preserved the query and context.

## Data and Contracts

Inputs:
- Profile/group create, rename, activation and confirmed deletion actions.
- Note destination selections, search query and scope, startup saved context.
- Container-disposal choice, destination and replacement profile where required.

Outputs:
- Active context, organized panel contents, visible note windows and clear errors.

Persistence changes:
- Profile identity/name and last active group.
- Group identity/name, owning profile and built-in General designation.
- Note membership and application-wide active context.
- Existing individually open/hidden flags retain their meaning.
- Removed-container state and existing soft-deletion semantics, without orphaned
  memberships or references to a removed active context.

Migration contract:
- Add memberships transactionally to every existing note, including retained
  soft-deleted notes. Keep existing IDs, text, appearance and timestamps intact.
- Create the initial Personal/Pessoal profile and its General group; activate it.
- A failed migration leaves the pre-migration data intact. The technical plan
  must define schema validation, backup and compatibility with older binaries
  before implementation. See [technical plan](plan.md) and the
  [migration contract](contracts/migration-v5.json) for the planned data design.

## Quality Attributes

Security and privacy:
Profiles organize local notes; they do not promise account or security isolation.
No remote service, telemetry or note upload is introduced.

Accessibility:
All selection, expansion, activation and movement operations are keyboard
accessible. Announce selected profile/group, expanded state and hidden note
status. Retain Ctrl+F. Dialog cancellation restores focus to its invoking
control. Respect reduced motion and system theme.

Performance:
Preserve the MVP's startup target of two seconds with 100 short notes on the
supported desktop. Benchmark search and context changes with 1,000 short notes,
30 groups and three profiles before fixing additional numeric budgets in the
technical plan. Avoid creating windows for inactive or manually hidden notes.

Reliability:
Context changes, moves and container deletion preserve pending edits and
individual note state according to the confirmed disposal choice.
Main-panel closure/reopening and app shutdown do not reset active context.

Observability:
Report failed saves, migration and context changes through local diagnostic
errors without logging note contents. Expose actionable user-facing errors.

## Rollout and Operations

Migration:
All existing notes migrate to Personal/Pessoal -> General/Geral. Migration and
restart tests must cover active, hidden and deleted notes.

Configuration:
Use the existing local database; no account setup or feature service is needed.

Rollback:
Define and validate pre-migration backup/restore and old-schema compatibility
in the technical plan. Do not imply an older binary can open a newer schema.

Verification:
Derive domain, SQLite migration and GTK lifecycle tests from these acceptance
examples. Maintained execution cases must follow the playbook's Test Case
Standards. Record Wayland/X11 desktop checks separately from case definitions.

## Open Questions

No material product questions remain for the Plan phase. The maintainer
confirmed the initial migration destination, Create and activate, and search
defaults, and expanded the scope to include container deletion with a choice
to move or delete its notes.

DEL-02 through DEL-07 make the resulting lifecycle explicit while preserving
the accepted captive-General, single-active-context and hidden-note rules.
These details are recorded for review rather than left to implementation.

See [UX proposal](ux.md), [ordered tasks](tasks.md),
[verification cases](verification.md) and [spec review](review.md). This document
follows the engineering-playbook's Spec -> Clarify -> Check -> Plan -> Tasks
sequence. Implementation was subsequently authorized by the maintainer;
verification evidence is separate from these maintained acceptance examples.
