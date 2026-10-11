# Review: Local backup and Google Drive

Current phase: Spec / Clarify. Consolidated on 2026-10-11 at the maintainer's
request. No Plan, Tasks, implementation, Google account access, version change
or remote publication has been performed for this workstream.

Standards applied:
- `~/wspace/engineering-playbook/engineering-playbook/architecture/spec-driven-development.md`
- `~/wspace/engineering-playbook/engineering-playbook/testing/test-case-standards.md`

## Decision ledger

| ID | Status | Decision / source |
| --- | --- | --- |
| D1 | Confirmed | Completely local/offline notes remain authoritative; requested by maintainer |
| D2 | Confirmed | Local backup/restore first, Google Drive as first destination; latest maintainer instruction |
| D3 | Confirmed | Personal use first; no operated Pinleaf storage service or S3 in this iteration |
| D4 | Proposed default | Explicit Save/Restore with distinct dated copies; no automatic sync, scheduling or pruning |
| D5 | Proposed default | Main menu opens dedicated Backup & Restore window with local/Drive sections |
| D6 | Proposed default | Visible Drive files, narrow drive.file authorization and one account per installation |
| D7 | Proposed default | Exclude credentials/device state; OS credential storage or explicit session-only authorization |
| Q1 | Awaiting maintainer | Whole-library backup and replacement restore with a validated local recovery copy, or selective/merge scope |
| Q2 | Resolved | Maintainer requests optional password protection to avoid making forgotten passwords block all recovery; support both modes locally and on Drive, with protection initially off per new backup |

Q1/Q2 were presented together as product choices while drafting. The maintainer
resolved Q2 as optional protection; the spec, contract and cases now cover both
modes. A protected copy still requires its password, without a plaintext fallback.
Q1 remains unanswered and conditional; silence does not accept its recommended
whole-library replacement behavior. Resolve Q1 before a technical plan; other
defaults remain reviewable recommendations without a new permission request.

## Repository fit

Current code already has private, validated SQLite snapshots before schema
upgrades, but they are not a user export/import feature. Note editors have
pending autosave state, and context transitions coordinate flushing and geometry.
Restore must account for all live connections and callbacks, not just replace a
file. Schema 6 has optional ordinary context and retained soft-deleted records;
the draft preservation contract covers all 15 Note fields and portable text
settings. Existing migration notices and previous snapshots are not library
content to export. No technical implementation strategy is chosen yet.

## Quality checklist

- [x] Intent, primary user, scope and non-goals are bounded.
- [x] Local slice precedes the Google Drive slice; synchronization is deferred.
- [x] Confirmed decisions are distinguished from defaults and unanswered choices.
- [x] UX explains entry point, creation, preview, explicit restore and status.
- [x] Data inclusion/exclusion and hidden/deleted/context behavior are explicit.
- [x] Failures, interruption, recovery and stale editor writes have concrete examples.
- [x] Machine-readable behavior contract and maintained verification cases exist.
- [x] Provider documentation is primary-source and linked with consultation date.
- [x] Q2 resolved as optional protection; UX, requirements, contract and cases updated.
- [ ] Maintainer answers Q1 and conditional requirements/contracts are updated.
- [ ] Check complete; technical Plan requested and written with required ADRs,
      encoding schema, limits, compatibility matrix and valid/invalid examples.
- [ ] Tasks derived, implementation authorized and evidence produced.

## Verification boundary

This phase validates documentation, JSON syntax, preservation-field coverage,
traceability and local links only. Acceptance examples and verification cases
are design artifacts, not executed product tests. Do not claim a working local
backup, encryption, Drive connection or restoration from this specification.

Public provider references support the proposed OAuth flow and narrow scopes;
cross-installation Drive discovery and actual file access still require real
qualification. Testing-mode refresh-token lifetime belongs in the operating
instructions. No account identifiers or credentials are captured here.

Documentation checks on 2026-10-11 passed: 23 unique requirements and 17
acceptance examples trace to 16 maintained verification cases; the JSON contract
parses and covers all 15 current Note fields and all three portable text settings;
13 local links resolve. Version 0.8.0 is unchanged and no Plan/Tasks exist yet.
Application tests are not execution evidence for this documentation-only change.
