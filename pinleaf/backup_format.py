"""Bounded, portable backups. No GTK, database or network dependencies."""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import os
import copy
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from jsonschema import Draft202012Validator, FormatChecker, RefResolver, ValidationError

from pinleaf.config import resource_path
from pinleaf.organization import name_key


MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_PAYLOAD_BYTES = 32 * 1024 * 1024
MAX_DEPTH = 16
KDF = {"name": "scrypt", "n": 32768, "r": 8, "p": 3}
PORTABLE_SETTINGS = ("default_font_family", "default_font_size", "default_text_color")


class BackupError(ValueError):
    """Safe to display: never includes library content or credentials."""


class PasswordRequired(BackupError):
    pass


class AuthenticationError(BackupError):
    pass


def canonical(value: object) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (ValueError, UnicodeError, TypeError, RecursionError) as exc:
        raise BackupError("The backup contains unsupported data.") from exc


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise BackupError("The backup contains duplicate JSON fields.")
        result[key] = value
    return result


def _reject_number(_: str) -> None:
    raise BackupError("The backup contains an unsupported number.")


def parse(raw: bytes, *, limit: int = MAX_FILE_BYTES) -> dict:
    if len(raw) > limit:
        raise BackupError("The backup exceeds the supported size limit.")
    try:
        text = raw.decode("utf-8")
        # Bound nesting before json.loads can allocate/recursively parse it.
        depth, quoted, escaped = 0, False, False
        for char in text:
            if quoted:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    quoted = False
            elif char == '"':
                quoted = True
            elif char in "[{":
                depth += 1
                if depth > MAX_DEPTH:
                    raise BackupError("The backup is nested too deeply.")
            elif char in "]}":
                depth -= 1
        value = json.loads(text, object_pairs_hook=_object, parse_float=_reject_number,
                           parse_constant=_reject_number)
    except (UnicodeError, ValueError, RecursionError) as exc:
        if isinstance(exc, BackupError):
            raise
        raise BackupError("This is not a valid UTF-8 Pinleaf backup.") from exc
    if not isinstance(value, dict):
        raise BackupError("The backup must contain a JSON object.")
    _check_types(value)
    return value


def _check_types(value: object, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise BackupError("The backup is nested too deeply.")
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise BackupError("The backup contains unsupported fields.")
        for child in value.values():
            _check_types(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _check_types(child, depth + 1)
    elif type(value) is int:
        if not -(2**63) <= value < 2**63:
            raise BackupError("The backup contains an out-of-range integer.")
    elif value is not None and not isinstance(value, str):
        raise BackupError("The backup contains an unsupported value.")


@lru_cache(maxsize=2)
def _validator(kind: str) -> Draft202012Validator:
    schemas = [json.loads(resource_path("resources", "backup", f"backup-{name}.schema.json").read_text())
               for name in ("payload", "envelope")]
    store = {schema["$id"]: schema for schema in schemas}
    schema = schemas[0 if kind == "payload" else 1]
    if kind == "envelope":
        schema = copy.deepcopy(schema)
        # Authenticate/checksum before inspecting the private payload schema.
        schema["oneOf"][0]["properties"]["payload"] = {"type": "object"}
    def forbidden(_: str) -> None:
        raise BackupError("External backup schemas are not supported.")
    return Draft202012Validator(schema, format_checker=FormatChecker(),
        resolver=RefResolver.from_schema(schema, store=store,
                                        handlers={"http": forbidden, "https": forbidden}))


def _schema(value: dict, kind: str) -> None:
    try:
        _validator(kind).validate(value)
    except ValidationError as exc:
        raise BackupError("The backup has missing, invalid or unsupported fields.") from exc


def validate_payload(payload: dict) -> bytes:
    _check_types(payload)
    if payload.get("payload_version") != 1 or payload.get("library_schema_version") != 6:
        raise BackupError("Unsupported backup or library version. This reader supports format 1 and library 6.")
    raw = canonical(payload)
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise BackupError("The library exceeds the supported backup size.")
    _schema(payload, "payload")
    library = payload["library"]

    def indexed(table: str, key: str = "id") -> dict:
        result = {row[key]: row for row in library[table]}
        if len(result) != len(library[table]):
            raise BackupError("The backup contains duplicate record identifiers.")
        return result

    profiles, groups = indexed("profiles"), indexed("groups")
    indexed("notes")
    contexts, _settings = indexed("profile_context", "profile_id"), indexed("app_settings", "key")
    live_profiles = {key for key, row in profiles.items() if row["deleted_at"] is None}
    if not live_profiles:
        raise BackupError("The backup has no available profile.")
    names: set[tuple] = set()
    shared = dict.fromkeys(live_profiles, 0)
    for table, rows in (("profiles", profiles.values()), ("groups", groups.values())):
        for row in rows:
            if row["name"] != row["name"].strip() or row["name_key"] != name_key(row["name"]):
                raise BackupError("The backup contains an invalid profile or group name.")
            if table == "groups" and row["profile_id"] not in profiles:
                raise BackupError("The backup contains a group without its profile.")
            if row["deleted_at"] is not None:
                continue
            key = (table, row.get("profile_id"), row["name_key"])
            if key in names:
                raise BackupError("The backup contains conflicting profile or group names.")
            names.add(key)
            if table == "groups":
                owner = row["profile_id"]
                if owner not in live_profiles:
                    raise BackupError("The backup contains a live group in a removed profile.")
                if row["is_shared"]:
                    shared[owner] += 1
                elif row["name_key"] in {"shared", "compartilhado"}:
                    raise BackupError("The backup uses a reserved group name.")
    if any(count != 1 for count in shared.values()):
        raise BackupError("Each profile must have exactly one Shared group.")
    for row in library["notes"]:
        group = groups.get(row["group_id"])
        if group is None or (row["deleted_at"] is None and (
                group["deleted_at"] is not None or group["profile_id"] not in live_profiles)):
            raise BackupError("The backup contains a note without an available owner.")
    for context in [library["active_context"], *contexts.values()]:
        owner = context["profile_id"]
        group_id = context.get("group_id", context.get("last_group_id"))
        group = groups.get(group_id)
        if owner not in live_profiles or (group_id is not None and (
                group is None or group["profile_id"] != owner or group["is_shared"]
                or group["deleted_at"] is not None)):
            raise BackupError("The backup contains an invalid working context.")
    # Avoid NoteStore repairing incomplete saved contexts and altering imported data.
    if set(contexts) != live_profiles:
        raise BackupError("The backup is missing a profile's working context.")
    active = library["active_context"]
    if contexts[active["profile_id"]]["last_group_id"] != active["group_id"]:
        raise BackupError("The backup contains conflicting working contexts.")
    return raw


def _password(value: str) -> bytes:
    try:
        raw = value.encode("utf-8")
    except UnicodeError as exc:
        raise BackupError("The password must contain valid UTF-8 text.") from exc
    if not 1 <= len(raw) <= 1024:
        raise BackupError("Use a password between 1 and 1,024 UTF-8 bytes.")
    return raw


def _key(password: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=KDF["n"], r=KDF["r"], p=KDF["p"]).derive(_password(password))


def _b64(value: str, size: int | None = None) -> bytes:
    try:
        raw = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BackupError("The backup contains invalid encoded data.") from exc
    if base64.b64encode(raw).decode("ascii") != value or (size is not None and len(raw) != size):
        raise BackupError("The backup contains invalid encoded data.")
    return raw


@dataclass(frozen=True)
class ValidatedBackup:
    payload_bytes: bytes
    protected: bool

    @property
    def payload(self) -> dict:
        """Return a fresh copy; a preview cannot mutate the validated input."""
        return parse(self.payload_bytes, limit=MAX_PAYLOAD_BYTES)


def encode(payload: dict, password: str | None = None) -> bytes:
    raw = validate_payload(payload)
    envelope = {"format": "pinleaf-backup", "format_version": 1}
    if password is None:
        envelope.update(protection="none", payload=payload, sha256=hashlib.sha256(raw).hexdigest())
    else:
        salt, nonce = os.urandom(16), os.urandom(12)
        envelope.update(protection="scrypt-aes256-gcm", kdf=dict(KDF),
                        salt=base64.b64encode(salt).decode("ascii"),
                        nonce=base64.b64encode(nonce).decode("ascii"))
        ciphertext = AESGCM(_key(password, salt)).encrypt(nonce, raw, canonical(envelope))
        envelope["ciphertext"] = base64.b64encode(ciphertext).decode("ascii")
    result = canonical(envelope)
    if len(result) > MAX_FILE_BYTES:
        raise BackupError("The backup exceeds the supported file size.")
    return result


def decode(raw: bytes, password: str | None = None) -> ValidatedBackup:
    envelope = parse(raw)
    if envelope.get("format") != "pinleaf-backup" or envelope.get("format_version") != 1:
        raise BackupError("Unsupported backup format. Choose a format-1 Pinleaf backup.")
    _schema(envelope, "envelope")
    protected = envelope["protection"] != "none"
    if protected:
        salt, nonce = _b64(envelope["salt"], 16), _b64(envelope["nonce"], 12)
        ciphertext = _b64(envelope["ciphertext"])
        if not 16 <= len(ciphertext) <= MAX_PAYLOAD_BYTES + 16:
            raise BackupError("The encrypted backup exceeds supported bounds.")
        if password is None:
            raise PasswordRequired("Enter this backup's password to view and restore it.")
        header = {key: value for key, value in envelope.items() if key != "ciphertext"}
        try:
            plaintext = AESGCM(_key(password, salt)).decrypt(nonce, ciphertext, canonical(header))
        except InvalidTag as exc:
            raise AuthenticationError("Wrong password or damaged protected backup.") from exc
        payload = parse(plaintext, limit=MAX_PAYLOAD_BYTES)
    else:
        payload = envelope["payload"]
        if payload.get("payload_version") != 1 or payload.get("library_schema_version") != 6:
            raise BackupError("Unsupported backup or library version. This reader supports format 1 and library 6.")
        digest = hashlib.sha256(canonical(payload)).hexdigest()
        if not hmac.compare_digest(digest, envelope["sha256"]):
            raise BackupError("The backup checksum does not match. The file may be damaged.")
    return ValidatedBackup(validate_payload(payload), protected)


def read_bytes(path: Path) -> bytes:
    with path.open("rb") as source:
        raw = source.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise BackupError("The backup exceeds the supported file size.")
    return raw


def library_digest(library: dict) -> str:
    ordered = {key: sorted(rows, key=lambda row: row.get("id", row.get("profile_id", row.get("key"))))
               if isinstance(rows, list) else rows for key, rows in library.items()}
    return hashlib.sha256(canonical(ordered)).hexdigest()
