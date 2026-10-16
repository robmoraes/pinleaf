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
        sql += " GROUP BY g.id ORDER BY g.is_shared DESC,g.name_key,g.id"
        return [Group(row["id"], row["profile_id"], row["name"], bool(row["is_shared"]), row["note_count"])
                for row in self.connection.execute(sql, args)]

    def get_group(self, group_id: str) -> Group:
        row = self.connection.execute("""SELECT g.* FROM groups g JOIN profiles p ON p.id=g.profile_id
            WHERE g.id=? AND g.deleted_at IS NULL AND p.deleted_at IS NULL""", (group_id,)).fetchone()
        if row is None:
            raise OrganizationError("The group is no longer available.")
        return Group(row["id"], row["profile_id"], row["name"], bool(row["is_shared"]))

    def shared(self, profile_id: str) -> Group:
        row = self.connection.execute("SELECT id FROM groups WHERE profile_id=? AND is_shared=1 AND deleted_at IS NULL",
                                      (profile_id,)).fetchone()
        if row is None:
            raise RuntimeError("The profile has no permanent Shared group.")
        return self.get_group(row[0])

    def context(self) -> ActiveContext:
        row = self.connection.execute("SELECT profile_id,group_id FROM active_context WHERE singleton_id=1").fetchone()
        if row is None:
            raise RuntimeError("The active context is missing.")
        profile = self.get_profile(row[0])
        group = self.get_group(row[1]) if row[1] is not None else None
        if group is not None and (group.profile_id != profile.id or group.is_shared):
            raise OrganizationError("The ordinary working group is unavailable.")
        return ActiveContext(profile, group)

    def last_group(self, profile_id: str) -> Group | None:
        self.get_profile(profile_id)
        row = self.connection.execute("SELECT last_group_id FROM profile_context WHERE profile_id=?", (profile_id,)).fetchone()
        if row is not None and row[0] is not None:
            try:
                group = self.get_group(row[0])
                if group.profile_id == profile_id and not group.is_shared:
                    return group
            except OrganizationError:
                pass
        return None

    def set_context(self, profile_id: str, group_id: str | None) -> ActiveContext:
        self.get_profile(profile_id)
        if group_id is not None:
            group = self.get_group(group_id)
            if group.profile_id != profile_id or group.is_shared:
                raise OrganizationError("Choose an ordinary group belonging to this profile.")
        current = self.connection.execute("SELECT profile_id,group_id FROM active_context WHERE singleton_id=1").fetchone()
        last = self.connection.execute("SELECT last_group_id FROM profile_context WHERE profile_id=?", (profile_id,)).fetchone()
        if current is not None and tuple(current) == (profile_id, group_id) and last is not None and last[0] == group_id:
            return self.context()
        self.connection.execute("""INSERT INTO active_context VALUES (1,?,?)
            ON CONFLICT(singleton_id) DO UPDATE SET profile_id=excluded.profile_id,group_id=excluded.group_id""", (profile_id, group_id))
        self.connection.execute("""INSERT INTO profile_context VALUES (?,?)
            ON CONFLICT(profile_id) DO UPDATE SET last_group_id=excluded.last_group_id""", (profile_id, group_id))
        return self.context()

    def activate(self, group_id: str) -> ActiveContext:
        group = self.get_group(group_id)
        return self.set_context(group.profile_id, group.id)

    def activate_profile(self, profile_id: str) -> ActiveContext:
        group = self.last_group(profile_id)
        return self.set_context(profile_id, group.id if group else None)

    def repair_context(self) -> bool:
        from pinleaf.storage.migrations import validate_context

        repaired = False
        with self.store.transaction():
            profiles = self.list_profiles()
            if not profiles:
                raise RuntimeError("The library has no live profile.")
            cursor = self.connection.execute("DELETE FROM profile_context WHERE profile_id NOT IN (SELECT id FROM profiles WHERE deleted_at IS NULL)")
            repaired = cursor.rowcount > 0
            for profile in profiles:
                group = self.last_group(profile.id)
                group_id = group.id if group else None
                row = self.connection.execute("SELECT last_group_id FROM profile_context WHERE profile_id=?", (profile.id,)).fetchone()
                if row is None or row[0] != group_id:
                    repaired = True
                    self.connection.execute("""INSERT INTO profile_context VALUES (?,?)
                        ON CONFLICT(profile_id) DO UPDATE SET last_group_id=excluded.last_group_id""", (profile.id, group_id))
            row = self.connection.execute("SELECT profile_id,group_id FROM active_context WHERE singleton_id=1").fetchone()
            try:
                context = self.context()
            except (OrganizationError, RuntimeError):
                live = {profile.id for profile in profiles}
                profile_id = row[0] if row is not None and row[0] in live else min(live)
                if row is not None and row[0] in live:
                    context = self.set_context(profile_id, None)
                else:
                    context = self.activate_profile(profile_id)
                repaired = True
            last = self.connection.execute("SELECT last_group_id FROM profile_context WHERE profile_id=?", (context.profile.id,)).fetchone()
            if last is None or last[0] != context.group_id:
                self.set_context(context.profile.id, context.group_id)
                repaired = True
            validate_context(self.connection)
            if self.connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
                raise RuntimeError("Database foreign-key integrity validation failed.")
        return repaired
