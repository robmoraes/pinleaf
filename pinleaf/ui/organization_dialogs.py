from __future__ import annotations

from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk, Pango

from pinleaf.models import Group
from pinleaf.organization import OrganizationError, StalePreviewError, group_label
from pinleaf.services.context_controller import TransitionError
from pinleaf.services.organization_service import DeletionPreview, OrganizationService


def _dropdown(strings: list[str], label: str) -> Gtk.DropDown:
    dropdown = Gtk.DropDown.new_from_strings(strings)
    factory = Gtk.SignalListItemFactory()
    factory.connect("setup", lambda _, item: item.set_child(Gtk.Label(
        xalign=0, ellipsize=Pango.EllipsizeMode.END, max_width_chars=30)))
    def bind(_factory, item) -> None:
        text = item.get_item().get_string()
        item.get_child().set_text(text)
        item.get_child().set_tooltip_text(text)
    factory.connect("bind", bind)
    dropdown.set_factory(factory)
    dropdown.set_list_factory(factory)
    dropdown.update_property([Gtk.AccessibleProperty.LABEL], [label])
    return dropdown


class OrganizationDialog(Adw.Window):
    def __init__(self, parent: Gtk.Window, title: str, execute: Callable) -> None:
        super().__init__(transient_for=parent, modal=True, title=title)
        self.execute = execute
        self.set_default_size(440, 280)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for side in ("top", "bottom", "start", "end"):
            getattr(self.body, f"set_margin_{side}")(18)
        self.error = Gtk.Label(wrap=True, xalign=0)
        self.error.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.error.add_css_class("error")
        self.error.set_visible(False)
        self.body.append(self.error)
        self.buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.buttons.set_halign(Gtk.Align.END)
        self.cancel = Gtk.Button(label="Cancel")
        self.cancel.connect("clicked", lambda _: self.close())
        self.confirm = Gtk.Button()
        self.buttons.append(self.cancel)
        self.buttons.append(self.confirm)
        self.body.append(self.buttons)
        toolbar.set_content(self.body)
        self.set_content(toolbar)
        self.set_default_widget(self.cancel)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key_pressed)
        self.add_controller(keys)

    def _key_pressed(self, _controller, keyval, _keycode, _state) -> bool:
        from gi.repository import Gdk
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def append(self, widget: Gtk.Widget) -> None:
        self.body.insert_child_after(widget, self.buttons.get_prev_sibling())

    def submit(self, action: Callable, affected_ids: set[str] | None = None) -> bool:
        try:
            self.execute(action, affected_ids=affected_ids)
        except (OrganizationError, TransitionError) as exc:
            self.show_error(str(exc))
        except Exception:
            self.show_error("Could not save this change. Your current context is preserved. Try again.")
        else:
            self.close()
            return True
        return False

    def show_error(self, message: str) -> None:
        self.error.set_text(message)
        self.error.set_visible(True)


class NameDialog(OrganizationDialog):
    def __init__(self, parent: Gtk.Window, organization: OrganizationService, execute: Callable,
                 kind: str, *, container_id: str | None = None, name: str = "") -> None:
        creating = container_id is None
        super().__init__(parent, f"{'New' if creating else 'Rename'} {kind}", execute)
        self.organization = organization
        self.kind = kind
        self.container_id = container_id
        self.entry = Gtk.Entry(text=name)
        self.entry.set_placeholder_text("Name (up to 80 characters)")
        self.entry.update_property([Gtk.AccessibleProperty.LABEL], [f"{kind.capitalize()} name"])
        label = Gtk.Label(label=f"{kind.capitalize()} name", xalign=0)
        self.append(label)
        self.append(self.entry)
        self.confirm.set_label("Create and activate" if creating else "Save")
        self.confirm.add_css_class("suggested-action")
        self.confirm.connect("clicked", self._save)
        self.entry.connect("activate", self._save)
        self.connect("map", lambda _: self.entry.grab_focus())

    def _save(self, _widget) -> None:
        def action() -> None:
            if self.container_id is not None:
                self.organization.rename(self.kind, self.container_id, self.entry.get_text())
            elif self.kind == "profile":
                self.organization.create_profile(self.entry.get_text())
            else:
                self.organization.create_group(self.entry.get_text())
        self.submit(action, set() if self.container_id else None)


class DestinationPicker(Gtk.Box):
    def __init__(self, organization: OrganizationService, *, excluded: tuple[str, ...] = (),
                 selected: str | None = None, on_changed: Callable = lambda: None) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.organization = organization
        self.excluded = excluded
        self.on_changed = lambda: None
        self.profiles = [profile for profile in organization.list_profiles()
                         if any(group.id not in excluded for group in organization.list_groups(profile.id))]
        self.groups: list[Group] = []
        self.profile = _dropdown([profile.name for profile in self.profiles], "Destination profile")
        self.group = _dropdown([], "Destination group")
        self.path = Gtk.Label(xalign=0, wrap=True)
        self.path.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        profile_label = Gtk.Label(label="Profile", xalign=0)
        group_label_widget = Gtk.Label(label="Group", xalign=0)
        self.profile.update_relation([Gtk.AccessibleRelation.LABELLED_BY],
                                    [Gtk.AccessibleList.new_from_list([profile_label])])
        self.group.update_relation([Gtk.AccessibleRelation.LABELLED_BY],
                                  [Gtk.AccessibleList.new_from_list([group_label_widget])])
        self.append(profile_label)
        self.append(self.profile)
        self.append(group_label_widget)
        self.append(self.group)
        self.append(self.path)
        self.profile.set_tooltip_text("Destination profile")
        self.group.set_tooltip_text("Destination group")
        self.profile.update_property([Gtk.AccessibleProperty.LABEL], ["Destination profile"])
        self.group.update_property([Gtk.AccessibleProperty.LABEL], ["Destination group"])
        if selected:
            for index, profile in enumerate(self.profiles):
                if any(group.id == selected for group in organization.list_groups(profile.id)):
                    self.profile.set_selected(index)
        self.profile.connect("notify::selected", self._profile_changed)
        self.group.connect("notify::selected", self._group_changed)
        self._profile_changed()
        for index, group in enumerate(self.groups):
            if group.id == selected:
                self.group.set_selected(index)
        self.on_changed = on_changed

    @property
    def destination(self) -> Group | None:
        index = self.group.get_selected()
        return self.groups[index] if index < len(self.groups) else None

    @property
    def identity(self) -> tuple[str, str, str, str] | None:
        destination = self.destination
        index = self.profile.get_selected()
        if destination is None or index >= len(self.profiles):
            return None
        profile = self.profiles[index]
        return profile.id, profile.name, destination.id, destination.name

    def _profile_changed(self, *_args) -> None:
        index = self.profile.get_selected()
        self.groups = (self.organization.list_groups(self.profiles[index].id)
                       if index < len(self.profiles) else [])
        self.groups = [group for group in self.groups if group.id not in self.excluded]
        self.group.set_model(Gtk.StringList.new([group_label(group) for group in self.groups]))
        if self.groups:
            self.group.set_selected(0)
        self._group_changed()

    def _group_changed(self, *_args) -> None:
        destination = self.destination
        index = self.profile.get_selected()
        self.path.set_text(f"{self.profiles[index].name} / {group_label(destination)}"
                           if destination is not None and index < len(self.profiles) else "No available destination")
        self.on_changed()


class MoveDialog(OrganizationDialog):
    def __init__(self, parent: Gtk.Window, organization: OrganizationService, execute: Callable,
                 note_id: str) -> None:
        super().__init__(parent, "Move note", execute)
        self.organization = organization
        self.note_id = note_id
        note = organization.store.get(note_id)
        self.source_id = note.group_id if note else None
        self.confirm.set_label("Move")
        self.confirm.add_css_class("suggested-action")
        self.picker = DestinationPicker(organization, selected=self.source_id, on_changed=self._changed)
        self.append(self.picker)
        self._changed()
        self.confirm.connect("clicked", self._move)

    def _changed(self) -> None:
        picker = getattr(self, "picker", None)
        if picker is not None:
            self.confirm.set_sensitive(picker.destination is not None and picker.destination.id != self.source_id)

    def _move(self, _widget) -> None:
        destination = self.picker.destination
        if destination is not None and destination.id != self.source_id:
            self.submit(lambda: self.organization.move_note(self.note_id, destination.id), {self.note_id})


class InspectNoteDialog(OrganizationDialog):
    def __init__(self, parent: Gtk.Window, title: str, content: str, on_open: Callable) -> None:
        super().__init__(parent, title, lambda *_args, **_kwargs: None)
        self.set_default_size(480, 420)
        view = Gtk.TextView(editable=False, cursor_visible=False, wrap_mode=Gtk.WrapMode.WORD_CHAR)
        view.get_buffer().set_text(content or "Empty note")
        scroller = Gtk.ScrolledWindow(child=view, vexpand=True, min_content_height=180)
        self.append(scroller)
        self.cancel.set_label("Close")
        self.confirm.set_label("Activate and open")
        self.confirm.connect("clicked", lambda _: (self.close(), on_open()))


class DeleteDialog(OrganizationDialog):
    def __init__(self, parent: Gtk.Window, organization: OrganizationService, execute: Callable,
                 preview: DeletionPreview) -> None:
        super().__init__(parent, f"Delete {preview.kind}", execute)
        self.organization = organization
        self.preview = preview
        self.summary = Gtk.Label(wrap=True, xalign=0)
        self.summary.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.append(self.summary)
        self.move = Gtk.CheckButton(label="Move notes")
        self.remove = Gtk.CheckButton(label="Delete all notes")
        self.remove.set_group(self.move)
        self.move.set_active(True)
        self.append(self.move)
        self.append(self.remove)
        self.picker = DestinationPicker(organization, excluded=preview.group_ids, on_changed=self._changed)
        self.append(self.picker)
        self.replacements = [profile for profile in organization.list_profiles() if profile.id != preview.container_id]
        self.replacement_label = Gtk.Label(label="Profile to activate after deletion", xalign=0)
        self.replacement = _dropdown([profile.name for profile in self.replacements], "Profile to activate after deletion")
        self.replacement.update_property([Gtk.AccessibleProperty.LABEL], ["Profile to activate after deletion"])
        self.replacement.update_relation([Gtk.AccessibleRelation.LABELLED_BY],
                                        [Gtk.AccessibleList.new_from_list([self.replacement_label])])
        self.append(self.replacement_label)
        self.append(self.replacement)
        self.context_label = Gtk.Label(wrap=True, xalign=0)
        self.context_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.append(self.context_label)
        self.move.connect("toggled", self._changed)
        self.replacement.connect("notify::selected", self._changed)
        self.confirm.connect("clicked", self._delete)
        self._changed()

    def _changed(self, *_args) -> None:
        if not hasattr(self, "context_label"):
            return
        preview = self.preview
        count = preview.note_count
        moving = count > 0 and self.move.get_active()
        context = self.organization.context
        deleting_active_profile = preview.kind == "profile" and context.profile.id == preview.container_id
        replacing = deleting_active_profile and not moving
        quantity = f"{count} {'note' if count == 1 else 'notes'}"
        group_count = sum(deleted is None for _, _, deleted in preview.groups)
        self.summary.set_text(f"{preview.name}\n{quantity}, including hidden notes."
                              + (f" {group_count} {'group' if group_count == 1 else 'groups'}." if preview.kind == "profile" else ""))
        self.move.set_visible(count > 0)
        self.remove.set_visible(count > 0)
        self.picker.set_visible(moving)
        self.replacement_label.set_visible(replacing)
        self.replacement.set_visible(replacing)
        destination = self.picker.destination
        next_profile, next_group = context.profile.name, group_label(context.group)
        if context.group.id in preview.group_ids:
            if preview.kind == "group":
                next_group = group_label(self.organization.repository.general(context.profile.id))
            elif moving and destination is not None:
                next_profile = self.organization.repository.get_profile(destination.profile_id).name
                next_group = group_label(destination)
            elif replacing and self.replacement.get_selected() < len(self.replacements):
                profile = self.replacements[self.replacement.get_selected()]
                next_profile = profile.name
                next_group = group_label(self.organization.repository.last_group(profile.id))
        self.context_label.set_text(f"Active afterward: {next_profile} / {next_group}")
        self.replacement_identity = None
        if replacing and self.replacement.get_selected() < len(self.replacements):
            profile = self.replacements[self.replacement.get_selected()]
            group = self.organization.repository.last_group(profile.id)
            self.replacement_identity = (profile.id, profile.name, group.id, group.name)
        self.confirm.set_label(f"Delete {preview.kind} and move notes" if moving else
                               f"Delete {preview.kind} and {quantity}" if count else f"Delete {preview.kind}")
        self.confirm.remove_css_class("destructive-action")
        if not moving:
            self.confirm.add_css_class("destructive-action")
        self.confirm.set_sensitive((not moving or destination is not None)
                                   and (not replacing or bool(self.replacements)))

    def _delete(self, _widget) -> None:
        moving = self.preview.note_count > 0 and self.move.get_active()
        destination = self.picker.destination if moving else None
        replacement = (self.replacements[self.replacement.get_selected()].id
                       if self.replacement.get_selected() < len(self.replacements) else None)
        preview = self.preview

        def action() -> None:
            self.organization.delete_container(
                preview, destination_group_id=destination.id if destination else None,
                destination_identity=self.picker.identity if moving else None,
                delete_notes=preview.note_count > 0 and not moving,
                replacement_profile_id=replacement,
                replacement_identity=self.replacement_identity,
            )
        try:
            self.execute(action, affected_ids={note_id for note_id, _, _ in preview.notes})
        except StalePreviewError as exc:
            try:
                self.preview = self.organization.preview_deletion(preview.kind, preview.container_id)
                self.body.remove(self.picker)
                self.picker = DestinationPicker(self.organization, excluded=self.preview.group_ids, on_changed=self._changed)
                self.body.insert_child_after(self.picker, self.remove)
                self.replacements = [profile for profile in self.organization.list_profiles() if profile.id != preview.container_id]
                self.replacement.set_model(Gtk.StringList.new([profile.name for profile in self.replacements]))
                if self.replacements:
                    self.replacement.set_selected(0)
                self._changed()
            except OrganizationError:
                self.confirm.set_sensitive(False)
            self.show_error(str(exc))
        except (OrganizationError, TransitionError) as exc:
            self.show_error(str(exc))
        except Exception:
            self.show_error("Could not save this change. Your current context is preserved. Try again.")
        else:
            self.close()


class ManageProfilesDialog(OrganizationDialog):
    def __init__(self, parent: Gtk.Window, organization: OrganizationService, execute: Callable) -> None:
        super().__init__(parent, "Manage profiles", execute)
        self.organization = organization
        self.confirm.set_visible(False)
        self.cancel.set_label("Close")
        self.rows = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.rows.add_css_class("boxed-list")
        scroller = Gtk.ScrolledWindow(min_content_height=160, max_content_height=400,
                                     propagate_natural_height=True, child=self.rows)
        self.append(scroller)
        new = Gtk.Button(label="New profile…")
        new.connect("clicked", lambda _: self._child(NameDialog(self, organization, execute, "profile")))
        self.append(new)
        self.refresh()

    def _child(self, dialog: Gtk.Window) -> None:
        dialog.connect("close-request", lambda _: (self.refresh(), False)[1])
        dialog.present()

    def refresh(self) -> None:
        while self.rows.get_first_child() is not None:
            self.rows.remove(self.rows.get_first_child())
        profiles = self.organization.list_profiles()
        for profile in profiles:
            row = Adw.ActionRow(title=profile.name)
            row.set_use_markup(False)
            rename = Gtk.Button(label="Rename", valign=Gtk.Align.CENTER)
            rename.connect("clicked", lambda _, p=profile: self._child(
                NameDialog(self, self.organization, self.execute, "profile", container_id=p.id, name=p.name)))
            delete = Gtk.Button(label="Delete…", valign=Gtk.Align.CENTER)
            delete.set_sensitive(len(profiles) > 1)
            delete.set_tooltip_text("Delete profile" if len(profiles) > 1 else "Create another profile before deleting this one")
            delete.connect("clicked", lambda _, p=profile: self._child(DeleteDialog(
                self, self.organization, self.execute, self.organization.preview_deletion("profile", p.id))))
            row.add_suffix(rename)
            row.add_suffix(delete)
            self.rows.append(row)
