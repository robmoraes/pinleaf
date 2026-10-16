# Synthetic portable-format examples

These files validate the planned contract, not a shipped exporter/restorer.
They contain no user data or Google credentials. The protected interoperability
vector uses the public password `Synthetic-example-only-789` and fixed salt/nonce
for reproducibility. Production writers must generate fresh random salt/nonce
for every protected copy; never reuse this vector's values for actual backups.

| File | Expected outcome |
| --- | --- |
| [valid-unprotected](valid-unprotected.pinleaf-backup) | Schema/checksum/semantic acceptance; no password |
| [valid-protected](valid-protected.pinleaf-backup) | Authenticate with the synthetic password; same payload as unprotected |
| [valid-empty](valid-empty.pinleaf-backup) | Zero notes and Shared-only context are valid |
| [invalid-version](invalid-version.pinleaf-backup) | Unsupported envelope version, reject before crypto/import |
| [invalid-field](invalid-field.pinleaf-backup) | Unknown envelope member, schema rejection |
| [invalid-checksum](invalid-checksum.pinleaf-backup) | Shape valid, checksum invalid |
| [invalid-authentication](invalid-authentication.pinleaf-backup) | Shape valid, altered ciphertext cannot authenticate |
| [invalid-ownership](invalid-ownership.pinleaf-backup) | Shape/checksum valid, note owner absent |
| [invalid-duplicate-keys](invalid-duplicate-keys.pinleaf-backup) | Reject duplicate JSON keys during strict parsing |

Run contract-example checks with the system development dependencies:

```bash
/usr/bin/python3 specs/015-local-backup-and-google-drive/contracts/validate_examples.py
```

The checker also verifies wrong-password and authenticated-header rejection.
Full size/depth limits, every library invariant, durable filesystem behavior,
reader UI and real-process recovery remain implementation tasks; this small
fixture checker does not replace the product acceptance suite.
