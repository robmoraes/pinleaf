# ADR-001: Preserve note state across organization and schema upgrades

- **Status:** adopted in the local implementation; desktop qualification pending
- **Date:** 2026-10-10
- **Decision owners:** Pinleaf maintainer
- **Scope:** local organization storage, schema-5 migration and recovery
- **Supersedes:** none
- **Superseded by:** none

## Context

Pinleaf schema 4 has no organization membership. The accepted feature introduces
profiles/groups, one active context and container deletion with transfer or note
removal. Individually hidden notes must remain hidden; the existing note store
retains soft-deleted rows. A required membership migration changes the schema
that older binaries can read, making reversal and recovery consequential.

## Decision Drivers

- Every retained note needs exactly one valid group, including deleted notes.
- Membership, disposal and saved active context must change together.
- Container deletion must not silently turn existing soft deletion into a purge.
- A failed migration must leave the original library usable, with a validated
  recovery point for returning to a pre-upgrade binary.
- Retain SQLite, local XDG storage and the supported desktop dependencies.

## Considered Options

### A: Required membership, container tombstones and a validated snapshot

Introduce schema 5 with explicit profile/group/context tables and a required
note-group foreign key. Keep removed containers as tombstones and exclude them
from ordinary queries. Take a private SQLite snapshot before the atomic upgrade.

Advantages: enforceable membership, preservation of retained notes, one durable
context boundary and a defined recovery path without a new datastore.

Disadvantages: requires a notes-table rebuild, lifecycle filtering, backup disk
space and deliberate snapshot restore for downgrade. Restoring a snapshot does
not include edits made after it.

### B: Optional membership stored in settings

Advantages: smaller initial schema change.

Disadvantages: weak membership/ownership validation and ambiguous behavior when
groups disappear; does not satisfy the required-membership contract cleanly.

### C: Physical cascading deletion and an in-place upgrade without backup

Advantages: fewer retained rows and less initial migration machinery.

Disadvantages: changes existing retention semantics, removes recovery options
and leaves older binaries unable to read upgraded data without a safe restore.

## Decision

The implementation adopts option A. Use one SQLite connection with explicit transaction
ownership for organization changes. Keep note `is_open` independent of active
context, and retain existing soft-deletion behavior. Do not add an automatic
down-migration, restore UI, hard purge or remote backup service in this feature.

## Consequences

Positive: lifecycle changes preserve referential integrity and the existing
hidden/deleted state; upgrade rollback is defined before touching user data.

Negative: tombstones and private backups consume disk space. Ordinary reads must
exclude removed containers. An older binary must reject schema 5. A snapshot
restore loses subsequent changes from the restored view, so the newer database
must be preserved separately for later recovery.

Operational: abort an upgrade if backup or validation fails. Keep backups private
under the existing data directory. Stop Pinleaf before restoration and retain
SQLite sidecars with the newer recovery set. No automatic retention/pruning
policy or additional data egress is introduced.

## Validation and Review

Validate every supported legacy version, fresh creation, repeated startup,
forced migration failure, snapshot failure and a restore drill with an older
schema reader. Check all retained note values and soft-deleted memberships,
plus active/last-context repairs after each disposal path.

Review this decision if storage size, recovery requirements or a future
trash/purge feature changes. Implementation evidence and technical review
are recorded in [execution evidence](execution-2026-10-10.md), including remaining
desktop qualification. Snapshot restore has been drilled with the v0.7.0 reader.

## References

- [Specification](spec.md#data-and-contracts)
- [Technical plan](plan.md#migration-backup-and-compatibility)
- [Machine-readable migration contract](contracts/migration-v5.json)
- [Python SQLite backup API](https://docs.python.org/3.11/library/sqlite3.html#sqlite3.Connection.backup)
