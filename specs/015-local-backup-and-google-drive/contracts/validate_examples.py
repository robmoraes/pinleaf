"""Validate planned contract fixtures; this is not the product backup reader."""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from jsonschema import Draft202012Validator, FormatChecker, RefResolver, ValidationError


ROOT = Path(__file__).resolve().parent
PASSWORD = b"Synthetic-example-only-789"


def strict_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key")
        result[key] = value
    return result


def reject_constant(value: str) -> None:
    raise ValueError("Non-finite value")


def parse(raw: str | bytes) -> dict:
    return json.loads(raw, object_pairs_hook=strict_object,
                      parse_constant=reject_constant, parse_float=reject_constant)


def canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def decrypt(envelope: dict, password: bytes) -> dict:
    header = {key: value for key, value in envelope.items() if key != "ciphertext"}
    salt = base64.b64decode(header["salt"], validate=True)
    nonce = base64.b64decode(header["nonce"], validate=True)
    assert len(salt) == 16 and len(nonce) == 12
    key = Scrypt(salt=salt, length=32, n=32768, r=8, p=3).derive(password)
    ciphertext = base64.b64decode(envelope["ciphertext"], validate=True)
    return parse(AESGCM(key).decrypt(nonce, ciphertext, canonical(header)))


def check_fixture_ownership(payload: dict) -> None:
    """Check the ownership fixture, not every planned product domain rule."""
    library = payload["library"]
    profiles = {row["id"] for row in library["profiles"]}
    groups = {row["id"] for row in library["groups"]}
    if any(row["profile_id"] not in profiles for row in library["groups"]):
        raise ValueError("Missing profile")
    if any(row["group_id"] not in groups for row in library["notes"]):
        raise ValueError("Missing group")


def main() -> None:
    schemas = [parse((ROOT / name).read_text()) for name in
               ("backup-envelope.schema.json", "backup-payload.schema.json")]
    store = {schema["$id"]: schema for schema in schemas}
    validators = []
    for schema in schemas:
        Draft202012Validator.check_schema(schema)
        validators.append(Draft202012Validator(
            schema, resolver=RefResolver.from_schema(schema, store=store),
            format_checker=FormatChecker()))
    envelope_validator, payload_validator = validators
    cases = {
        "valid-unprotected": "accepted", "valid-protected": "accepted",
        "valid-empty": "accepted", "invalid-version": "schema",
        "invalid-field": "schema", "invalid-checksum": "integrity",
        "invalid-authentication": "authentication", "invalid-ownership": "semantic",
        "invalid-duplicate-keys": "parse",
    }
    accepted = {}
    for name, expected in cases.items():
        stage = "parse"
        try:
            envelope = parse((ROOT / "examples" / f"{name}.pinleaf-backup").read_bytes())
            stage = "schema"
            envelope_validator.validate(envelope)
            if envelope["protection"] == "none":
                stage = "integrity"
                payload = envelope["payload"]
                if hashlib.sha256(canonical(payload)).hexdigest() != envelope["sha256"]:
                    raise ValueError("Invalid checksum")
            else:
                stage = "authentication"
                payload = decrypt(envelope, PASSWORD)
            stage = "schema"
            payload_validator.validate(payload)
            stage = "semantic"
            check_fixture_ownership(payload)
            stage = "accepted"
            accepted[name] = payload
        except (ValueError, InvalidTag, ValidationError):
            pass
        assert stage == expected, f"{name}: expected {expected}, got {stage}"
    assert accepted["valid-protected"] == accepted["valid-unprotected"]
    protected = parse((ROOT / "examples/valid-protected.pinleaf-backup").read_bytes())
    changed_header = dict(protected, nonce=base64.b64encode(b"X" * 12).decode("ascii"))
    for envelope, password in ((protected, b"wrong-password"), (changed_header, PASSWORD)):
        try:
            decrypt(envelope, password)
        except InvalidTag:
            continue
        raise AssertionError("Authentication unexpectedly succeeded")
    print("PASS: two schemas, nine synthetic fixtures, wrong password and header tampering")
    print("Contract examples only; product reader, restore and Drive are not implemented.")


if __name__ == "__main__":
    main()
