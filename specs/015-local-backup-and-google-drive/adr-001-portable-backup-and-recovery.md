# ADR 001: Logical portable files and coordinated local replacement

Status: accepted for the technical plan on 2026-10-11; not implemented.
Traceability: BK-02–06, RS-01–07, PR-01/02, UX-02 in [spec](spec.md).

## Context

Notes are a local SQLite library with pending editor state, retained deleted
records and profile/group context. A portable file must restore independently
of the source machine. Password protection is optional; restoration replaces
the full library while retaining a recoverable current copy. The existing
migration snapshots do not provide this UI/data lifecycle.

## Decision

Use versioned JSON logical records with a strict envelope/payload contract.
Unprotected files have a corruption-detection checksum; protected files encrypt
the full private payload through cryptography's AESGCM, with a Scrypt-derived
key and authenticated fixed header. Version 1 fixes parameters rather than
accepting attacker-controlled work factors. See [format](contracts/format-v1.md).
Use established primitives without designing a new cipher/KDF. JSON schema and
semantic checks precede trusted staged SQLite reconstruction; input supplies no
SQL, schema or extraction paths. Keep producer/library/format versions distinct.

Keep the live schema at 6. Device/operation state is a separate private file,
excluded from backup. A healthy library restores logical records in one durable
SQLite transaction after saving pending edits, producing a verified recovery
file and invalidating every old editor generation. A durable attempt journal
allows startup to identify a complete old/new outcome before ordinary startup
can seed data. A failed-open library uses preserved raw original files plus
journaled installation of a clean trusted staged database; it never has to pass
logical validation before its original bytes are preserved.

## Alternatives and consequences

- Copying the live DB directly risks consistency and journal coupling, and
  exposes schema/code from input. A validated raw SQLite snapshot remains useful
  for migration recovery but is not the portable import contract.
- ZIP/SQL dumps add extraction or execution boundaries unnecessary for text notes.
- Always requiring encryption would make recovery depend on a forgotten password;
  omitting encryption entirely would remove the user's privacy choice.
- Replacing healthy DB/WAL/SHM files introduces a larger multi-file commit than
  SQLite's own transaction. Use file installation only when the original cannot
  be opened and preserve its complete recovery set first.

The logical format needs explicit adapters as schemas evolve and bounds the
first implementation to 32 MiB of canonical library payload. Two runtime
dependencies are introduced. Encryption protects selected portable copies,
not the already-local SQLite database or its private recovery files. Python
cannot guarantee secret-string zeroization. Tests must cover format compatibility,
both protection modes, exact values, interruption and stale callbacks.

## Reference basis

Consulted 2026-10-11:
- [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html) supports the
  choice of a transaction for healthy-library replacement; filesystem failure
  assumptions still require process/fault verification.
- [cryptography AESGCM](https://cryptography.io/en/41.0.7/hazmat/primitives/aead/)
  and [Scrypt](https://cryptography.io/en/41.0.7/hazmat/primitives/key-derivation-functions/)
  define the library primitives used by the format.
- [OWASP Scrypt work factors](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html#scrypt)
  inform the selected N=32768, r=8, p=3 cost; this is a backup-key derivation
  design decision, not a claim of password-storage certification.
