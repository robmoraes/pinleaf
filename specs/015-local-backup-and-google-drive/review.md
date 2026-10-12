# Review: Local backup and Google Drive

Current phase: local slice A implemented and qualified on 2026-10-11;
[execution](execution.md) records product evidence. Google Drive slice B remains
pending. No Google account access, version change or remote publication has
been performed for this workstream.

Standards applied:
- `~/wspace/engineering-playbook/engineering-playbook/architecture/spec-driven-development.md`
- `~/wspace/engineering-playbook/engineering-playbook/testing/test-case-standards.md`

## Decision ledger

| ID | Status | Decision / source |
| --- | --- | --- |
| D1 | Confirmed | Completely local/offline notes remain authoritative; requested by maintainer |
| D2 | Confirmed | Local backup/restore first, Google Drive as first destination; latest maintainer instruction |
| D3 | Confirmed | Personal use first; no operated Pinleaf storage service or S3 in this iteration |
| D4 | Adopted design default | Explicit Save/Restore with distinct dated copies; no automatic sync, scheduling or pruning |
| D5 | Adopted design default | Main menu opens dedicated Backup & Restore window with local/Drive sections |
| D6 | Adopted design default | Visible Drive files, narrow drive.file authorization and one account per installation |
| D7 | Adopted design default | Exclude credentials/device state; OS credential storage or explicit session-only authorization |
| Q1 | Resolved | Maintainer accepted whole-library backup and replacement restore with a validated local recovery copy and requested advancing the workflow |
| Q2 | Resolved | Maintainer requests optional password protection to avoid making forgotten passwords block all recovery; support both modes locally and on Drive, with protection initially off per new backup |

Q1/Q2 are resolved. Whole-library replacement/recovery and optional protection
are the product agreement. No material ambiguity remains before Plan/Tasks.
A protected copy still requires its password, without a plaintext fallback.
Implementation choices and their consequences are in the plan and ADRs; live
OAuth setup/test-account consent is an operational dependency for slice B.

## Repository fit

Current code already has private, validated SQLite snapshots before schema
upgrades, but they are not a user export/import feature. Note editors have
pending autosave state, and context transitions coordinate flushing and geometry.
Restore must account for all live connections and callbacks, not just replace a
file. Schema 6 has optional ordinary context and retained soft-deleted records;
the agreed preservation contract covers all 15 Note fields and portable text
settings. Existing migration notices and previous snapshots are not library
content to export. ADR 001 chooses a logical JSON format and transactional
healthy-library replacement; ADR 002 isolates Drive as a destination.

## Quality checklist

- [x] Intent, primary user, scope and non-goals are bounded.
- [x] Local slice precedes the Google Drive slice; synchronization is deferred.
- [x] Confirmed decisions are distinguished from implementation design defaults.
- [x] UX explains entry point, creation, preview, explicit restore and status.
- [x] Data inclusion/exclusion and hidden/deleted/context behavior are explicit.
- [x] Failures, interruption, recovery and stale editor writes have concrete examples.
- [x] Machine-readable behavior contract and maintained verification cases exist.
- [x] Provider documentation is primary-source and linked with consultation date.
- [x] Q2 resolved as optional protection; UX, requirements, contract and cases updated.
- [x] Q1 resolved and conditional requirements/contracts updated.
- [x] Check complete; technical Plan requested and written with required ADRs,
      encoding schema, limits, compatibility matrix and valid/invalid examples.
- [x] Tasks derived in local-before-Drive order, with traceable validation routes.
- [x] Local implementation and product verification evidence produced.
- [ ] Google Drive implementation and real-provider verification produced.

## Verification boundary

The original planning phase validated documentation/contracts only. The later
local delivery executes product tests for format, encryption, persistence,
replacement, real-process interruption and native GTK workflows. Local evidence
is separate from the still-unimplemented Google Drive cases.

Public provider references support the proposed OAuth flow and narrow scopes;
cross-installation Drive discovery and actual file access still require real
qualification. Testing-mode refresh-token lifetime belongs in the operating
instructions. No account identifiers or credentials are captured here.

Documentation checks on 2026-10-11 passed: 23 unique requirements and 17
acceptance examples trace to 16 maintained verification cases; the JSON contract
parses and covers all 15 current Note fields and all three portable text settings;
52 local links resolve; 16 ordered tasks have unique IDs and only the two
specification/planning tasks are complete. The [fixture checker](contracts/validate_examples.py)
validates two schemas, nine synthetic files, wrong-password rejection and
authenticated-header rejection with system jsonschema 4.10.3/cryptography 41.0.7.
These were planning checks, not product tests. The local implementation now
preserves legacy null font-size/text-color values; canonical and packaged
schemas agree. Read-only startup preflight avoids discarding damaged database
sidecars before recovery. Original-file fallback is repeatable after interruption.
Version 0.8.0 and schema 6 remain unchanged. Drive remains pending.
