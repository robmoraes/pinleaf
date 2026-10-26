from __future__ import annotations

import os
from unicodedata import normalize

from pinleaf.models import Group


class OrganizationError(ValueError):
    """An organization command cannot satisfy the domain rules."""


class ProtectedContainerError(OrganizationError):
    pass


class StalePreviewError(OrganizationError):
    pass


def name_key(value: str) -> str:
    return normalize("NFC", normalize("NFC", value.strip()).casefold())


def validate_name(value: str, *, group: bool = False) -> tuple[str, str]:
    name = value.strip()
    if not name:
        raise OrganizationError("Enter a name.")
    if len(name) > 80:
        raise OrganizationError("Use at most 80 characters.")
    key = name_key(name)
    if group and key in {"shared", "compartilhado"}:
        raise OrganizationError("Shared/Compartilhado is reserved for the permanent group.")
    return name, key


def is_portuguese(language: str | None = None) -> bool:
    if language is None:
        language = next(
            (os.environ[key] for key in ("LC_ALL", "LC_MESSAGES", "LANG") if os.environ.get(key)),
            "en",
        )
    return language.replace("-", "_").lower().startswith("pt_br")


def initial_profile_name(language: str | None = None) -> str:
    return "Pessoal" if is_portuguese(language) else "Personal"


def group_label(group: Group | None, language: str | None = None) -> str:
    if group is None:
        return "Somente notas compartilhadas" if is_portuguese(language) else "Shared notes only"
    if group.is_shared:
        return "Compartilhado" if is_portuguese(language) else "Shared"
    return group.name
