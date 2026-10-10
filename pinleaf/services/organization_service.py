from __future__ import annotations

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from uuid import uuid4

from pinleaf.models import ActiveContext, Group, Profile, utc_now_iso
from pinleaf.organization import OrganizationError, ProtectedContainerError, StalePreviewError, validate_name
from pinleaf.storage.migrations import validate_data
from pinleaf.storage.sqlite_store import NoteStore


@dataclass(frozen=True)
class DeletionPreview:
    kind: str
    container_id: str
    name: str
    groups: tuple[tuple[str, str, str | None], ...]
    notes: tuple[tuple[str, str, str | None], ...]

    @property
    def note_count(self) -> int:
        return sum(deleted is None for _, _, deleted in self.notes)

    @property
    def group_ids(self) -> tuple[str, ...]:
        return tuple(group[0] for group in self.groups)


class OrganizationService:
    def __init__(self, store: NoteStore, *, id_factory: Callable[[], str] | None = None,
                 clock: Callable[[], str] | None = None) -> None:
        self.store = store
        self.repository = store.organization
        self.connection = store.connection
        self.id_factory = id_factory or (lambda: str(uuid4()))
        self.clock = clock or utc_now_iso

    @property
    def context(self) -> ActiveContext:
        return self.repository.context()

    def list_profiles(self) -> list[Profile]:
        return self.repository.list_profiles()

    def list_groups(self, profile_id: str | None = None) -> list[Group]:
        return self.repository.list_groups(profile_id)

    def activate_group(self, group_id: str) -> ActiveContext:
        with self.store.transaction():
            return self.repository.activate(group_id)

    def activate_profile(self, profile_id: str) -> ActiveContext:
        return self.activate_group(self.repository.last_group(profile_id).id)

    def create_profile(self, name: str) -> Profile:
        name, key = validate_name(name)
        profile_id, group_id = self.id_factory(), self.id_factory()
        try:
            with self.store.transaction():
                self.connection.execute("INSERT INTO profiles(id,name,name_key) VALUES (?,?,?)", (profile_id, name, key))
                self.connection.execute("INSERT INTO groups(id,profile_id,name,name_key,is_general) VALUES (?,?,'General','general',1)", (group_id, profile_id))
                self.repository.activate(group_id)
        except sqlite3.IntegrityError as exc:
            raise OrganizationError("A profile with this name already exists.") from exc
        return self.repository.get_profile(profile_id)

    def create_group(self, name: str, profile_id: str | None = None) -> Group:
        name, key = validate_name(name, group=True)
        profile_id = profile_id or self.context.profile.id
        self.repository.get_profile(profile_id)
        group_id = self.id_factory()
        try:
            with self.store.transaction():
                self.connection.execute("INSERT INTO groups(id,profile_id,name,name_key,is_general) VALUES (?,?,?,?,0)", (group_id, profile_id, name, key))
                self.repository.activate(group_id)
        except sqlite3.IntegrityError as exc:
            raise OrganizationError("A group with this name already exists in this profile.") from exc
        return self.repository.get_group(group_id)

    def rename(self, kind: str, container_id: str, name: str) -> None:
        table = self._table(kind)
        if kind == "group":
            group = self.repository.get_group(container_id)
            if group.is_general:
                raise ProtectedContainerError("General cannot be renamed.")
        else:
            self.repository.get_profile(container_id)
        name, key = validate_name(name, group=kind == "group")
        try:
            with self.store.transaction():
                self.connection.execute(f"UPDATE {table} SET name=?,name_key=? WHERE id=?", (name, key, container_id))
        except sqlite3.IntegrityError as exc:
            raise OrganizationError("This name is already in use.") from exc

    def move_note(self, note_id: str, group_id: str) -> None:
        with self.store.transaction():
            self.repository.get_group(group_id)
            if self.store.get(note_id) is None:
                raise OrganizationError("The note is no longer available.")
            self.connection.execute("UPDATE notes SET group_id=? WHERE id=? AND deleted_at IS NULL", (group_id, note_id))

    def activate_and_open(self, note_id: str) -> None:
        with self.store.transaction():
            note = self.store.get(note_id)
            if note is None:
                raise OrganizationError("The note is no longer available.")
            self.repository.activate(note.group_id)
            self.connection.execute("UPDATE notes SET is_open=1 WHERE id=? AND deleted_at IS NULL", (note_id,))

    def preview_deletion(self, kind: str, container_id: str) -> DeletionPreview:
        self._table(kind)
        if kind == "group":
            group = self.repository.get_group(container_id)
            if group.is_general:
                raise ProtectedContainerError("General is permanent and cannot be deleted independently.")
            owner = self.repository.get_profile(group.profile_id)
            name = f"{owner.name} / {group.name}"
            groups = ((group.id, group.name, None),)
        else:
            profile = self.repository.get_profile(container_id)
            if len(self.list_profiles()) <= 1:
                raise ProtectedContainerError("Create another profile before deleting this one.")
            name = profile.name
            groups = tuple(tuple(row) for row in self.connection.execute(
                "SELECT id,name,deleted_at FROM groups WHERE profile_id=? ORDER BY id", (profile.id,)))
        ids = tuple(group[0] for group in groups)
        slots = ",".join("?" for _ in ids)
        notes = tuple(tuple(row) for row in self.connection.execute(
            f"SELECT id,group_id,deleted_at FROM notes WHERE group_id IN ({slots}) ORDER BY id", ids))
        return DeletionPreview(kind, container_id, name, groups, notes)

    def delete_container(self, preview: DeletionPreview, *, destination_group_id: str | None = None,
                         delete_notes: bool = False, replacement_profile_id: str | None = None,
                         destination_identity: tuple[str, str, str, str] | None = None,
                         replacement_identity: tuple[str, str, str, str] | None = None) -> None:
        with self.store.transaction():
            try:
                current = self.preview_deletion(preview.kind, preview.container_id)
            except OrganizationError as exc:
                raise StalePreviewError("The deletion scope changed. Review it again.") from exc
            if current != preview:
                raise StalePreviewError("The deletion scope changed. Review the note count and destination again.")
            active = self.context
            destination = None
            if not delete_notes and (preview.note_count or destination_group_id):
                if destination_group_id is None:
                    raise OrganizationError("Choose a destination for the notes.")
                try:
                    destination = self.repository.get_group(destination_group_id)
                    owner = self.repository.get_profile(destination.profile_id)
                except OrganizationError as exc:
                    raise StalePreviewError("The destination changed. Choose it again and review the summary.") from exc
                if destination_identity is not None and destination_identity != (owner.id, owner.name, destination.id, destination.name):
                    raise StalePreviewError("The destination changed. Choose it again and review the summary.")
                if destination.id in preview.group_ids:
                    raise OrganizationError("Choose a destination outside the removed profile/group.")
            next_group = active.group
            if active.group.id in preview.group_ids:
                if preview.kind == "group":
                    next_group = self.repository.general(active.profile.id)
                elif destination is not None:
                    next_group = destination
                else:
                    if replacement_profile_id is None or replacement_profile_id == preview.container_id:
                        raise OrganizationError("Choose the profile to activate after deletion.")
                    try:
                        replacement = self.repository.get_profile(replacement_profile_id)
                        next_group = self.repository.last_group(replacement_profile_id)
                    except OrganizationError as exc:
                        raise StalePreviewError("The replacement profile changed. Review the summary again.") from exc
                    if replacement_identity is not None and replacement_identity != (replacement.id, replacement.name, next_group.id, next_group.name):
                        raise StalePreviewError("The replacement context changed. Review the summary again.")
            slots = ",".join("?" for _ in preview.group_ids)
            now = self.clock()
            if destination is not None:
                self.connection.execute(f"UPDATE notes SET group_id=? WHERE group_id IN ({slots})", (destination.id, *preview.group_ids))
            elif delete_notes:
                self.connection.execute(f"UPDATE notes SET deleted_at=?,updated_at=? WHERE group_id IN ({slots}) AND deleted_at IS NULL", (now, now, *preview.group_ids))
            self.connection.execute(f"UPDATE groups SET deleted_at=? WHERE id IN ({slots}) AND deleted_at IS NULL", (now, *preview.group_ids))
            if preview.kind == "profile":
                self.connection.execute("DELETE FROM profile_context WHERE profile_id=?", (preview.container_id,))
                self.connection.execute("UPDATE profiles SET deleted_at=? WHERE id=?", (now, preview.container_id))
            self.repository.activate(next_group.id)
            self.repository.repair_context()
            validate_data(self.connection)

    @staticmethod
    def _table(kind: str) -> str:
        if kind not in {"group", "profile"}:
            raise OrganizationError("Unknown container type.")
        return "groups" if kind == "group" else "profiles"
