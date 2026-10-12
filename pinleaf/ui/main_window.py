from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, tzinfo

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk, Pango

from pinleaf.appearance import TextAppearance
from pinleaf.models import Group, Note, SearchScope
from pinleaf.organization import OrganizationError, group_label, is_portuguese
from pinleaf.services.context_controller import TransitionError
from pinleaf.services.note_service import NoteService
from pinleaf.ui.about import show_about
from pinleaf.ui.dialogs import confirm_delete, show_error
from pinleaf.ui.organization_dialogs import DeleteDialog, InspectNoteDialog, ManageProfilesDialog, MoveDialog, NameDialog
from pinleaf.ui.text_appearance_window import TextAppearanceWindow


class MainWindow(Adw.ApplicationWindow):
    def __init__(
        self,
        *,
        application: Adw.Application,
        note_service: NoteService,
        on_create_note: Callable[[], None],
        on_open_note: Callable[[str], None],
        on_delete_note: Callable[[str], None],
        on_execute: Callable | None = None,
        on_hide_note: Callable[[str], None] | None = None,
        on_create_shared_note: Callable[[], None] | None = None,
        on_backup: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(application=application)
        self.note_service = note_service
        self.on_create_note = on_create_note
        self.on_create_shared_note = on_create_shared_note or (
            lambda: self._perform(lambda: self.note_service.create_note(shared=True), affected_ids=set()))
        self.on_open_note = on_open_note
        self.on_delete_note = on_delete_note
        self.on_execute = on_execute
        self.on_hide_note = on_hide_note
        self.on_backup = on_backup
        self.organization = note_service.organization
        context = self.organization.context
        self.expanded: dict[str, bool] = {self.organization.repository.shared(context.profile.id).id: True}
        if context.group_id:
            self.expanded[context.group_id] = True
        self.group_rows: dict[str, Adw.ExpanderRow] = {}
        self.focus_targets: dict[str, Gtk.Widget] = {}
        self._search_expansion: dict[str, bool] | None = None
        self._profile_signature = None
        self._render_signature = None
        self._refreshing = False
        self._disposed = False
        self.text_appearance_window: TextAppearanceWindow | None = None

        self.set_title("Pinleaf")
        self.set_default_size(520, 620)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)
        self.profile_button = Gtk.MenuButton()
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.profile_label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END, max_width_chars=22)
        self.profile_label.add_css_class("heading")
        self.group_label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END, max_width_chars=24)
        self.group_label.add_css_class("dim-label")
        title_box.append(self.profile_label)
        title_box.append(self.group_label)
        title = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title.append(title_box)
        title.append(Gtk.Image(icon_name="pan-down-symbolic"))
        self.profile_button.set_child(title)
        header.set_title_widget(self.profile_button)

        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_tooltip_text("Main menu")
        menu_button.set_popover(self._build_menu())
        header.pack_end(menu_button)

        self.new_button = Gtk.MenuButton(label="New")
        self.new_button.set_tooltip_text("Create a note or group")
        self.new_button.set_popover(self._action_popover([
            ("New Note", self.on_create_note),
            ("New Group…", lambda: self._present_dialog(NameDialog(
                self, self.organization, self.execute, "group"))),
        ]))
        header.pack_start(self.new_button)

        self.stack = Gtk.Stack()
        self.stack.set_vexpand(True)
        self.stack.set_hexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        self.list_box = Gtk.ListBox()
        self.list_box.add_css_class("boxed-list")
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.connect("row-activated", self._on_row_activated)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)
        scroller.set_child(self.list_box)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_property("placeholder-text", "Search notes")
        self.search_entry.set_tooltip_text("Search all note text (Ctrl+F)")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("search-changed", lambda _: self.refresh())
        self.search_entry.connect("stop-search", lambda _: self.search_entry.set_text(""))

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_vexpand(True)
        content.set_hexpand(True)
        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)
        content.append(self._build_migration_notice())
        content.append(self.search_entry)
        self.scope = Gtk.DropDown.new_from_strings(["Contexto atual" if is_portuguese() else "Current context", "Current profile", "All profiles"])
        self.scope.set_tooltip_text("Search scope")
        self.scope.update_property([Gtk.AccessibleProperty.LABEL], ["Search scope"])
        self.scope_label = Gtk.Label(label="Search scope", xalign=0)
        self.scope.update_relation([Gtk.AccessibleRelation.LABELLED_BY],
                                   [Gtk.AccessibleList.new_from_list([self.scope_label])])
        self.scope_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.scope_row.append(self.scope_label)
        self.scope.set_hexpand(True)
        self.scope_row.append(self.scope)
        self.scope_row.set_visible(False)
        self.scope.set_visible(False)
        self.scope.connect("notify::selected", lambda *_: self.refresh())
        content.append(self.scope_row)
        content.append(self.stack)

        self.stack.add_named(scroller, "list")
        self.stack.add_named(self._build_no_results_state(), "no-results")

        toolbar.set_content(content)
        self.set_content(toolbar)
        self.connect("close-request", self._hide_panel)

        key_controller = Gtk.EventControllerKey()
        key_controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_controller.connect("key-pressed", self._on_key_pressed)
        self.add_controller(key_controller)

    def _build_migration_notice(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        notice = self.note_service.store.migration_notice()
        box.set_visible(notice is not None)
        if notice is None:
            return box
        text = ("Geral agora é Compartilhado. Suas notas aparecem junto do grupo ativo."
                if is_portuguese() else "General is now Shared. Its notes appear alongside the active group.")
        for rename in notice["renames"]:
            text += f"\n{rename['profile']}: {rename['from']} → {rename['to']}"
        label = Gtk.Label(label=text, wrap=True, xalign=0, hexpand=True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        box.append(label)
        dismiss = Gtk.Button(icon_name="window-close-symbolic", valign=Gtk.Align.START)
        dismiss.set_tooltip_text("Dispensar aviso" if is_portuguese() else "Dismiss notice")
        dismiss.update_property([Gtk.AccessibleProperty.LABEL], [dismiss.get_tooltip_text()])
        def dismissed(_button) -> None:
            self._perform(self.note_service.store.dismiss_migration_notice, affected_ids=set())
            box.set_visible(self.note_service.store.migration_notice() is not None)
        dismiss.connect("clicked", dismissed)
        box.append(dismiss)
        return box

    def _build_menu(self) -> Gtk.Popover:
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)

        text_appearance = Gtk.Button()
        text_appearance.add_css_class("flat")
        text_appearance.set_tooltip_text("Configure default text appearance for new notes")
        text_appearance.connect("clicked", lambda _: self._show_text_appearance_window())

        self.text_appearance_label = Gtk.Label()
        text_appearance.set_child(self.text_appearance_label)
        box.append(text_appearance)

        if self.on_backup is not None:
            backup = Gtk.Button(label="Backup & Restore…")
            backup.add_css_class("flat")
            backup.connect("clicked", lambda _: (popover.popdown(), self.on_backup()))
            box.append(backup)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        about = Gtk.Button(label="About Pinleaf")
        about.add_css_class("flat")
        about.connect("clicked", lambda _: show_about(self))
        box.append(about)

        self._sync_text_appearance_label()
        popover.set_child(box)
        return popover

    def _show_text_appearance_window(self) -> None:
        if self.text_appearance_window is not None:
            self.text_appearance_window.present()
            return
        self.text_appearance_window = TextAppearanceWindow(
            parent=self,
            appearance=self.note_service.get_default_text_appearance(),
            on_save=self._save_default_text_appearance,
            error_heading="Could not save text settings",
            error_body="New notes may keep using the previous text settings.",
            on_saved=self._sync_text_appearance_label,
        )
        self.text_appearance_window.connect(
            "close-request",
            self._on_text_appearance_window_closed,
        )
        self.text_appearance_window.present()

    def _on_text_appearance_window_closed(self, _: Gtk.Window) -> bool:
        self.text_appearance_window = None
        return False

    def _sync_text_appearance_label(self) -> None:
        label = getattr(self, "text_appearance_label", None)
        if label is None:
            return
        label.set_text("Text Settings")

    def _save_default_text_appearance(self, appearance: TextAppearance) -> None:
        if self._disposed:
            raise TransitionError("This library has been replaced. Reopen Text Settings.")
        self.note_service.set_default_text_appearance(
            font_family=appearance.font_family,
            font_size=appearance.font_size,
            text_color=appearance.text_color,
        )

    def refresh(self) -> None:
        if self._refreshing or self._disposed:
            return
        self._refreshing = True
        try:
            self._refresh()
        finally:
            self._refreshing = False

    def _hide_panel(self, _window) -> bool:
        self.set_visible(False)
        return True

    def destroy(self) -> None:
        self._disposed = True
        super().destroy()

    def _refresh(self) -> None:
        query = self.search_entry.get_text()
        searching = bool(query.strip())
        if searching and self._search_expansion is None:
            self._search_expansion = self.expanded.copy()
        elif not searching and self._search_expansion is not None:
            self.expanded = self._search_expansion
            self._search_expansion = None
        self.scope.set_visible(searching)
        self.scope_row.set_visible(searching)
        scope = list(SearchScope)[self.scope.get_selected()]
        context = self.organization.context
        groups = self.organization.list_groups(context.profile.id)
        notes = self.note_service.list_notes(query=query, scope=scope if searching else SearchScope.CURRENT_PROFILE)
        self._sync_profiles()
        all_groups = self.organization.list_groups() if searching and scope == SearchScope.ALL_PROFILES else groups
        all_profiles = self.organization.list_profiles()
        signature = (query, scope, context, tuple(all_groups), tuple(all_profiles), tuple(notes))
        if signature == self._render_signature:
            return
        focused = self.get_focus()
        focus_key = None
        while focused is not None:
            focus_key = getattr(focused, "focus_key", None)
            if focus_key:
                break
            focused = focused.get_parent()
        self.focus_targets = {}
        self.group_rows = {}
        self._visible_group_ids = {self.organization.repository.shared(context.profile.id).id, context.group_id}
        self._shared_group_ids = {group.id for group in all_groups if group.is_shared}
        profiles = {profile.id: profile.name for profile in all_profiles}
        self._paths = {group.id: f"{profiles[group.profile_id]} / {group_label(group)}" for group in all_groups}
        self._clear_list()
        if searching and scope != SearchScope.CURRENT_PROFILE:
            for note in notes:
                self.list_box.append(self._build_row(note, breadcrumb=scope == SearchScope.ALL_PROFILES))
        else:
            for group in groups:
                members = [note for note in notes if note.group_id == group.id]
                if not searching or members:
                    self.list_box.append(self._build_group(group, members, searching=searching))
        self.stack.set_visible_child_name("no-results" if searching and not notes else "list")
        self._render_signature = signature
        if focus_key in self.focus_targets:
            self.focus_targets[focus_key].grab_focus()
        elif focus_key and focus_key.startswith("activate:"):
            if context.group_id in self.group_rows:
                self.group_rows[context.group_id].child_focus(Gtk.DirectionType.TAB_FORWARD)
            else:
                self.search_entry.grab_focus()

    def context_changed(self) -> None:
        self._search_expansion = None
        context = self.organization.context
        self.expanded[self.organization.repository.shared(context.profile.id).id] = True
        if context.group_id:
            self.expanded[context.group_id] = True
        self._refreshing = True
        self.search_entry.set_text("")
        self.scope.set_selected(0)
        self._refreshing = False
        self._render_signature = None

    def execute(self, action: Callable, *, affected_ids: set[str] | None = None):
        if self._disposed:
            raise TransitionError("This library has been replaced. Reopen the panel.")
        previous = self.organization.context.identity
        if self.on_execute is not None:
            result = self.on_execute(action, affected_ids=affected_ids)
        else:
            # Widget-only consumers have no desktop editors to reconcile.
            result = action()
        if self.organization.context.identity != previous:
            self.context_changed()
        self.refresh()
        return result

    def _perform(self, action: Callable, *, affected_ids: set[str] | None = None) -> None:
        try:
            self.execute(action, affected_ids=affected_ids)
        except (OrganizationError, TransitionError) as exc:
            show_error(self, "Could not complete this change", str(exc))
        except Exception:
            show_error(self, "Could not save this change", "Your current context is preserved. Try again.")

    def _present_dialog(self, dialog: Gtk.Window) -> None:
        focused = self.get_focus()
        control = focused
        focus_key = None
        while control is not None:
            focus_key = getattr(control, "focus_key", None)
            if focus_key:
                break
            control = control.get_parent()
        def closed(_window) -> bool:
            if focus_key in self.focus_targets:
                self.focus_targets[focus_key].grab_focus()
            elif focused is not None and focused.get_root() is self and focused.get_mapped():
                focused.grab_focus()
            else:
                self.profile_button.grab_focus()
            return False
        dialog.connect("close-request", closed)
        dialog.present()

    def _sync_profiles(self) -> None:
        profiles = self.organization.list_profiles()
        context = self.organization.context
        self.profile_label.set_text(context.profile.name)
        self.group_label.set_text(group_label(context.group))
        self.profile_button.set_tooltip_text(f"Switch profile, {context.profile.name} / {group_label(context.group)}")
        self.profile_button.update_property([Gtk.AccessibleProperty.LABEL], [f"Switch profile, {context.profile.name}"])
        signature = (tuple(profiles), context.profile.id)
        if signature == self._profile_signature:
            return
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(8)
        for profile in profiles:
            button = Gtk.Button()
            button.set_child(Gtk.Label(label=("✓ " if profile.id == context.profile.id else "") + profile.name,
                                       ellipsize=Pango.EllipsizeMode.END, max_width_chars=30))
            button.set_tooltip_text(profile.name)
            button.update_property([Gtk.AccessibleProperty.LABEL], [
                profile.name + (", current profile" if profile.id == context.profile.id else "")])
            button.add_css_class("flat")
            button.connect("clicked", lambda _, p=profile: (popover.popdown(), self._perform(
                lambda: self.organization.activate_profile(p.id))))
            box.append(button)
        box.append(Gtk.Separator())
        for label, factory in (
            ("New profile…", lambda: NameDialog(self, self.organization, self.execute, "profile")),
            ("Manage profiles…", lambda: ManageProfilesDialog(self, self.organization, self.execute)),
        ):
            button = Gtk.Button(label=label)
            button.add_css_class("flat")
            button.connect("clicked", lambda _, make=factory: (popover.popdown(), self._present_dialog(make())))
            box.append(button)
        popover.set_child(box)
        self.profile_button.set_popover(popover)
        self._profile_signature = signature

    def _focusable(self, widget: Gtk.Widget, key: str) -> Gtk.Widget:
        widget.focus_key = key
        self.focus_targets[key] = widget
        return widget

    def _build_group(self, group: Group, notes: list[Note], *, searching: bool) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow(title=group_label(group))
        row.set_use_markup(False)
        active = group.id == self.organization.context.group_id
        count = len(notes) if searching else group.note_count
        row.set_subtitle(f"{count} {'note' if count == 1 else 'notes'}" + (" · Active" if active else ""))
        self._focusable(row, f"group:{group.id}")
        if not active and not group.is_shared:
            activate = Gtk.Button(label="Activate", valign=Gtk.Align.CENTER)
            activate.set_tooltip_text(f"Activate {group_label(group)} on the desktop")
            activate.connect("clicked", lambda _: self._perform(lambda: self.organization.activate_group(group.id)))
            row.add_suffix(self._focusable(activate, f"activate:{group.id}"))
        if group.is_shared:
            explanation = ("Aparece junto do grupo ativo" if is_portuguese() else "Shown alongside the active group")
            row.set_subtitle(f"{count} {'note' if count == 1 else 'notes'} · {explanation}")
            row.set_tooltip_text(explanation)
            create = Gtk.Button(icon_name="list-add-symbolic", valign=Gtk.Align.CENTER)
            create.set_tooltip_text("Criar nota compartilhada" if is_portuguese() else "Create shared note")
            create.update_property([Gtk.AccessibleProperty.LABEL], [create.get_tooltip_text()])
            create.connect("clicked", lambda _: self.on_create_shared_note())
            row.add_suffix(self._focusable(create, f"shared-create:{group.id}"))
        else:
            actions = self._action_menu([
                ("Rename group…", lambda: self._present_dialog(NameDialog(
                    self, self.organization, self.execute, "group", container_id=group.id, name=group.name))),
                ("Delete group…", lambda: self._present_dialog(DeleteDialog(
                    self, self.organization, self.execute, self.organization.preview_deletion("group", group.id)))),
            ], f"Actions for {group_label(group)}")
            row.add_suffix(self._focusable(actions, f"group-menu:{group.id}"))
        nested_list = None
        for note in notes:
            child = self._build_row(note)
            row.add_row(child)
            nested_list = child.get_parent()
        if isinstance(nested_list, Gtk.ListBox):
            nested_list.connect("row-activated", self._on_row_activated)
        if not notes:
            empty = Adw.ActionRow(title="No notes in this group")
            if active or group.is_shared:
                create = Gtk.Button(label="Create Note", valign=Gtk.Align.CENTER)
                create.connect("clicked", lambda _: self.on_create_shared_note() if group.is_shared else self.on_create_note())
                empty.add_suffix(create)
            row.add_row(empty)
        row.set_expanded(True if searching else self.expanded.get(group.id, False))
        row.connect("notify::expanded", lambda widget, _: self._expanded(group.id, widget, searching))
        self.group_rows[group.id] = row
        return row

    def _expanded(self, group_id: str, row: Adw.ExpanderRow, searching: bool) -> None:
        if not searching:
            self.expanded[group_id] = row.get_expanded()

    def _action_menu(self, actions: list[tuple[str, Callable]], description: str) -> Gtk.MenuButton:
        button = Gtk.MenuButton(icon_name="view-more-symbolic", valign=Gtk.Align.CENTER)
        button.set_tooltip_text(description)
        button.set_create_popup_func(lambda *_: button.set_popover(self._action_popover(actions)))
        return button

    def _action_popover(self, actions: list[tuple[str, Callable]]) -> Gtk.Popover:
        popover = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        for side in ("top", "bottom", "start", "end"):
            getattr(box, f"set_margin_{side}")(6)
        for label, action in actions:
            item = Gtk.Button()
            item.set_child(Gtk.Label(label=label, ellipsize=Pango.EllipsizeMode.END, max_width_chars=38))
            item.set_tooltip_text(label)
            item.add_css_class("flat")
            item.connect("clicked", lambda _, callback=action: (popover.popdown(), callback()))
            box.append(item)
        popover.set_child(box)
        return popover

    def _on_key_pressed(
        self,
        _: Gtk.EventControllerKey,
        keyval: int,
        _keycode: int,
        state: Gdk.ModifierType,
    ) -> bool:
        if keyval in (Gdk.KEY_f, Gdk.KEY_F) and state & Gdk.ModifierType.CONTROL_MASK:
            self.search_entry.grab_focus()
            self.search_entry.select_region(0, -1)
            return True
        return False

    def _build_no_results_state(self) -> Gtk.Widget:
        status = Adw.StatusPage()
        status.set_icon_name("system-search-symbolic")
        status.set_title("No matching notes")
        status.set_description("Try a different search or clear the search field.")

        clear = Gtk.Button(label="Clear Search")
        clear.set_halign(Gtk.Align.CENTER)
        clear.connect("clicked", lambda _: self.search_entry.set_text(""))
        status.set_child(clear)
        return status

    def _build_row(self, note: Note, *, breadcrumb: bool = False) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(True)
        row.set_activatable(True)
        row.add_css_class("note-list-row")
        row.note_id = note.id  # type: ignore[attr-defined]
        self._focusable(row, f"note:{note.id}")

        container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        container.add_css_class("note-list-row-content")
        container.set_vexpand(False)
        container.set_hexpand(True)
        container.set_margin_top(10)
        container.set_margin_bottom(10)
        container.set_margin_start(12)
        container.set_margin_end(12)

        color = Gtk.Box()
        color.add_css_class("note-color-dot")
        color.add_css_class(f"note-{note.color.value}")
        color.set_valign(Gtk.Align.CENTER)
        container.append(color)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        text.set_hexpand(True)

        preview = Gtk.Label(label=_preview(note))
        preview.set_xalign(0)
        preview.set_ellipsize(Pango.EllipsizeMode.END)
        _apply_hidden_text_style(preview, note)
        text.append(preview)

        updated = Gtk.Label(label=f"Updated {_format_timestamp(note.updated_at)}")
        updated.add_css_class("dim-label")
        updated.set_xalign(0)
        updated.set_ellipsize(Pango.EllipsizeMode.END)
        _apply_hidden_text_style(updated, note)
        text.append(updated)
        active = note.group_id in self._visible_group_ids
        path = self._paths[note.group_id]
        row.set_tooltip_text(("Hidden note · " if not note.is_open else "") + path)
        row.update_property([Gtk.AccessibleProperty.LABEL], [
            ("Hidden note. " if not note.is_open else "Note. ") + _preview(note) + f". {path}"])
        if breadcrumb:
            trail = Gtk.Label(label=path, xalign=0, ellipsize=Pango.EllipsizeMode.END)
            trail.add_css_class("dim-label")
            text.append(trail)
        container.append(text)
        open_label = "Open" if active else ("Switch profile and open" if note.group_id in self._shared_group_ids else "Activate and open")
        actions = [(open_label if active else f"{open_label} · {path}", lambda: self.on_open_note(note.id))]
        if active and note.is_open and self.on_hide_note is not None:
            actions.append(("Hide", lambda: self.on_hide_note(note.id)))
        actions.extend([
            ("Move to…", lambda: self._present_dialog(MoveDialog(self, self.organization, self.execute, note.id))),
            ("Delete…", lambda: self._confirm_delete(note)),
        ])
        menu = self._action_menu(actions, f"Note actions · {path}")
        container.append(self._focusable(menu, f"note-menu:{note.id}"))

        row.set_child(container)
        return row

    def _clear_list(self) -> None:
        child = self.list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.list_box.remove(child)
            child = next_child

    def _on_row_activated(self, _: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        note_id = getattr(row, "note_id", None)
        if note_id is not None:
            note = self.note_service.get_note(note_id)
            if note is not None:
                self._inspect_or_open(note)

    def _inspect_or_open(self, note: Note) -> None:
        context = self.organization.context
        group = self.organization.repository.get_group(note.group_id)
        if note.group_id == context.group_id or (group.is_shared and group.profile_id == context.profile.id):
            self.on_open_note(note.id)
            return
        owner = self.organization.repository.get_profile(group.profile_id)
        self._present_dialog(InspectNoteDialog(self, f"{owner.name} / {group_label(group)}", note.content,
                                               lambda: self.on_open_note(note.id),
                                               open_label="Switch profile and open" if group.is_shared else "Activate and open"))

    def _confirm_delete(self, note: Note) -> None:
        confirm_delete(self, note, lambda: self.on_delete_note(note.id))


def _preview(note: Note) -> str:
    text = " ".join(note.content.split())
    if not text:
        return "Empty note"
    return text if len(text) <= 100 else f"{text[:97]}..."


def _apply_hidden_text_style(label: Gtk.Label, note: Note) -> None:
    if note.is_open:
        return
    attributes = Pango.AttrList()
    attributes.insert(Pango.attr_strikethrough_new(True))
    label.set_attributes(attributes)


def _format_timestamp(value: str, local_tz: tzinfo | None = None) -> str:
    try:
        timestamp = datetime.fromisoformat(value)
    except ValueError:
        return value
    if timestamp.tzinfo is None:
        timestamp = timestamp.astimezone()
    local = timestamp.astimezone(local_tz)
    return local.strftime("%b %-d, %Y %-I:%M %p %Z")
