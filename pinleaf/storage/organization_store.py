from __future__ import annotations

from typing import TYPE_CHECKING

from pinleaf.models import ActiveContext, Group, Profile
from pinleaf.organization import OrganizationError

if TYPE_CHECKING:
    from pinleaf.storage.sqlite_store import NoteStore


class OrganizationStore:
    def __init__(self, store: NoteStore) -> None:
        self.store = store
        self.connection = store.connection

    def list_profiles(self) -> list[Profile]:
        return [Profile(row["id"], row["name"]) for row in self.connection.execute(
            "SELECT id,name FROM profiles WHERE deleted_at IS NULL ORDER BY name_key,id"
        )]

    def get_profile(self, profile_id: str) -> Profile:
        row = self.connection.execute(
            "SELECT id,name FROM profiles WHERE id=? AND deleted_at IS NULL", (profile_id,)
        ).fetchone()
        if row is None:
            raise OrganizationError("The profile is no longer available.")
        return Profile(row["id"], row["name"])

    def list_groups(self, profile_id: str | None = None) -> list[Group]:
        sql = """SELECT g.*,COUNT(n.id) AS note_count FROM groups g
            JOIN profiles p ON p.id=g.profile_id AND p.deleted_at IS NULL
            LEFT JOIN notes n ON n.group_id=g.id AND n.deleted_at IS NULL
            WHERE g.deleted_at IS NULL"""
        args = ()
        if profile_id is not None:
            sql += " AND g.profile_id=?"
            args = (profile_id,)
        sql += " GROUP BY g.id ORDER BY g.is_general DESC,g.name_key,g.id"
        return [Group(row["id"], row["profile_id"], row["name"], bool(row["is_general"]), row["note_count"])
                for row in self.connection.execute(sql, args)]

    def get_group(self, group_id: str) -> Group:
        row = self.connection.execute("""SELECT g.* FROM groups g JOIN profiles p ON p.id=g.profile_id
            WHERE g.id=? AND g.deleted_at IS NULL AND p.deleted_at IS NULL""", (group_id,)).fetchone()
        if row is None:
            raise OrganizationError("The group is no longer available.")
        return Group(row["id"], row["profile_id"], row["name"], bool(row["is_general"]))

    def general(self, profile_id: str) -> Group:
        row = self.connection.execute("SELECT id FROM groups WHERE profile_id=? AND is_general=1 AND deleted_at IS NULL",
                                      (profile_id,)).fetchone()
        if row is None:
            raise RuntimeError("The profile has no permanent General group.")
        return self.get_group(row[0])

    def context(self) -> ActiveContext:
        row = self.connection.execute("SELECT group_id FROM active_context WHERE singleton_id=1").fetchone()
        if row is None:
            raise RuntimeError("The active context is missing.")
        group = self.get_group(row[0])
        return ActiveContext(self.get_profile(group.profile_id), group)

    def last_group(self, profile_id: str) -> Group:
        self.get_profile(profile_id)
        row = self.connection.execute("SELECT last_group_id FROM profile_context WHERE profile_id=?", (profile_id,)).fetchone()
        if row is not None:
            try:
                group = self.get_group(row[0])
                if group.profile_id == profile_id:
                    return group
            except OrganizationError:
                pass
        return self.general(profile_id)

    def activate(self, group_id: str) -> ActiveContext:
        group = self.get_group(group_id)
        current = self.connection.execute("SELECT group_id FROM active_context WHERE singleton_id=1").fetchone()
        last = self.connection.execute("SELECT last_group_id FROM profile_context WHERE profile_id=?", (group.profile_id,)).fetchone()
        if current is not None and current[0] == group.id and last is not None and last[0] == group.id:
            return self.context()
        self.connection.execute("""INSERT INTO active_context VALUES (1,?)
            ON CONFLICT(singleton_id) DO UPDATE SET group_id=excluded.group_id""", (group.id,))
        self.connection.execute("""INSERT INTO profile_context VALUES (?,?)
            ON CONFLICT(profile_id) DO UPDATE SET last_group_id=excluded.last_group_id""", (group.profile_id, group.id))
        return self.context()

    def repair_context(self) -> bool:
        repaired = False
        with self.store.transaction():
            profiles = self.list_profiles()
            if not profiles:
                raise RuntimeError("The library has no live profile.")
            cursor = self.connection.execute("DELETE FROM profile_context WHERE profile_id NOT IN (SELECT id FROM profiles WHERE deleted_at IS NULL)")
            repaired = cursor.rowcount > 0
            for profile in profiles:
                group = self.last_group(profile.id)
                row = self.connection.execute("SELECT last_group_id FROM profile_context WHERE profile_id=?", (profile.id,)).fetchone()
                if row is None or row[0] != group.id:
                    repaired = True
                    self.connection.execute("""INSERT INTO profile_context VALUES (?,?)
                        ON CONFLICT(profile_id) DO UPDATE SET last_group_id=excluded.last_group_id""", (profile.id, group.id))
            row = self.connection.execute("SELECT group_id FROM active_context WHERE singleton_id=1").fetchone()
            try:
                self.context()
            except (OrganizationError, RuntimeError):
                owner = None if row is None else self.connection.execute(
                    "SELECT profile_id FROM groups WHERE id=?", (row[0],)).fetchone()
                live = {profile.id for profile in profiles}
                profile_id = owner[0] if owner is not None and owner[0] in live else min(live)
                self.activate(self.general(profile_id).id)
                repaired = True
            if self.connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeError("Database foreign-key integrity validation failed.")
        return repaired
