# Portable backup format 1

Status: planned contract, not an implemented exporter. Extension:
`.pinleaf-backup`; encoding: UTF-8 JSON without BOM. Outer and decrypted/plain
payload objects reject duplicate keys and non-finite numbers. JSON depth is at
most 16, the full file at most 64 MiB, and canonical payload bytes at most 32 MiB.
No compression, paths, scripts or SQL statements exist in this format.

Schemas: [envelope](backup-envelope.schema.json), [payload](backup-payload.schema.json).
Schema structure alone does not establish integrity, ownership, uniqueness,
counts, base64 validity or cryptographic authenticity; those checks are required.

## Canonical bytes and unprotected files

`C(value)` is Python-compatible JSON serialization with keys sorted, separators
`,` and `:`, `ensure_ascii=False`, `allow_nan=False`, no indentation/terminal
newline, encoded UTF-8. No Unicode normalization is performed on note content
or passwords. Canonical payload values contain only strings, integers, null,
arrays and objects; no floats. Integers must fit signed SQLite 64-bit values.

For protection `none`, payload is an ordinary object and `sha256` is the lowercase
hex digest of C(payload). Verify it before semantic/staged validation. This
detects accidental corruption; someone able to modify the file can recompute it.
It does not provide confidentiality or authentication against deliberate changes.

## Password-protected files

For protection `scrypt-aes256-gcm`, the header is exactly the envelope without
`ciphertext`. KDF parameters are fixed: Scrypt N=32768, r=8, p=3, derived length
32 bytes. Derive from the exact 1–1,024 UTF-8 password bytes using a fresh random
16-byte salt. Encrypt C(payload) with AES-256-GCM, a fresh random 12-byte nonce
and C(header) as associated data. Store RFC 4648 padded standard base64 salt,
nonce and ciphertext with its complete 16-byte tag. Require canonical base64
spelling and exact decoded lengths; reject alternate KDF/cipher parameters before
performing expensive work. No private payload metadata appears in the header.

Wrong password, wrong authenticated header or corrupted ciphertext returns one
authentication error without revealing private preview data or falling back to
`none`. Reject unsupported versions separately. Restore determines protection
from the file; a creation-dialog setting cannot bypass it. An unprotected file is
never claimed to be encrypted. Re-encrypting a payload generates new salt/nonce.

## Logical data and validation

Source schema 6 is the only supported library schema in format 1. Preserve all
whitelisted rows/fields, including deleted owners and notes. Array records are
ordered by ID, contexts by profile_id and settings by key for deterministic
library digests; semantic validation rejects duplicate keys/IDs regardless of
order. `active_context` omits the fixed SQLite singleton_id, rebuilt as 1.

Validate owner references, live-name keys/uniqueness, one Shared per live profile,
at least one live profile, live-note ownership and optional ordinary-group
context using the same domain rules as the current store. Only the three
portable app-setting keys are allowed and absent keys remain absent. Missing
fonts and out-of-display geometry are presentation concerns, not data rewriting.

Reader order: bounded bytes/depth → strict JSON → envelope version/shape and
fixed parameter validation → checksum or decryption → payload size/JSON/schema →
semantic invariants → trusted staged database/FK/integrity checks → preview.
There are no input-selected schema URLs or SQL commands at any stage.

The [examples](examples/README.md) are synthetic contract fixtures, not product
verification results. Future versions require an explicit compatibility matrix
and adapters; never accept a newer schema simply by dropping unknown properties.
