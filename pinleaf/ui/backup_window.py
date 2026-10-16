from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from pinleaf.backup_format import AuthenticationError, BackupError, PasswordRequired, decode, read_bytes
from pinleaf.services.drive_backup import DriveCopy
from pinleaf.services.backup_service import BackupService, DriveExportResult, ExportResult
from pinleaf.services.context_controller import TransitionError
from pinleaf.services.drive_auth import DriveAuthError
from pinleaf.storage.atomic_files import OperationCancelled, check_cancel
from pinleaf.storage.restore_recovery import PreparedRestore, RestorePreview
from pinleaf.ui.dialogs import show_error


def _label(text: str) -> Gtk.Label:
    return Gtk.Label(label=text, xalign=0, wrap=True, selectable=True)


class PasswordWindow(Adw.Window):
    """A new creation flow always starts with protection off."""
    def __init__(self, parent: Gtk.Window, submit: Callable[[str | None], None], *, unlock: bool = False,
                 submit_label: str = "Choose Location…") -> None:
        super().__init__(transient_for=parent, modal=True, title="Unlock Backup" if unlock else "Create Backup")
        self.set_default_size(400, 320)
        self.submit = submit
        self.unlock = unlock
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=18, margin_bottom=18, margin_start=18, margin_end=18)
        self.protection = Gtk.CheckButton(label="Protect with password", active=False)
        self.protection.set_visible(not unlock)
        box.append(self.protection)
        box.append(_label("Anyone with access to an unprotected file can read it. A protected backup cannot be restored if you forget its password."
                          if not unlock else "Enter the password used when this backup was created."))
        self.fields = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.password = Gtk.PasswordEntry(show_peek_icon=True)
        self.password.set_property("placeholder-text", "Password")
        self.password.update_property([Gtk.AccessibleProperty.LABEL], ["Backup password"])
        self.confirmation = Gtk.PasswordEntry(show_peek_icon=True)
        self.confirmation.set_property("placeholder-text", "Confirm password")
        self.confirmation.update_property([Gtk.AccessibleProperty.LABEL], ["Confirm backup password"])
        self.fields.append(self.password)
        self.fields.append(self.confirmation)
        self.confirmation.set_visible(not unlock)
        self.fields.set_visible(unlock)
        self.protection.connect("toggled", lambda button: self.fields.set_visible(button.get_active()))
        box.append(self.fields)
        self.error = _label("")
        self.error.add_css_class("error")
        self.password.connect("changed", lambda _: self.error.set_text(""))
        self.confirmation.connect("changed", lambda _: self.error.set_text(""))
        box.append(self.error)
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, halign=Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel")
        cancel.connect("clicked", lambda _: self.close())
        actions.append(cancel)
        self.confirm = Gtk.Button(label="Unlock" if unlock else submit_label)
        self.confirm.add_css_class("suggested-action")
        self.confirm.connect("clicked", lambda _: self._submit())
        actions.append(self.confirm)
        box.append(actions)
        toolbar.set_content(box)
        self.set_content(toolbar)
        self.set_default_widget(self.confirm)
        self.connect("close-request", self._clear)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key)
        self.add_controller(keys)

    def _key(self, _, key, *_args) -> bool:
        from gi.repository import Gdk
        if key == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _clear(self, _) -> bool:
        self.password.set_text("")
        self.confirmation.set_text("")
        return False

    def _submit(self) -> None:
        protected = self.unlock or self.protection.get_active()
        password = self.password.get_text() if protected else None
        if protected:
            try:
                size = len(password.encode("utf-8"))
            except UnicodeError:
                size = 0
            if not 1 <= size <= 1024:
                self.error.set_text("Use a password between 1 and 1,024 UTF-8 bytes.")
                return
            if not self.unlock and password != self.confirmation.get_text():
                self.error.set_text("The passwords do not match.")
                return
        self.submit(password)
        self.close()


class BackupWindow(Adw.Window):
    def __init__(self, *, parent: Gtk.Window, service: BackupService,
                 capture: Callable[[], dict] | None, gate: Callable[[bool], None],
                 apply: Callable[[PreparedRestore], Path], startup_only: bool = False,
                 on_closed: Callable[[], None] = lambda: None) -> None:
        super().__init__(transient_for=parent, title="Backup & Restore")
        self.set_application(parent.get_application())
        self.set_default_size(500, 580)
        self.service, self.capture, self.gate, self.apply = service, capture, gate, apply
        self.on_closed = on_closed
        self.preview: RestorePreview | None = None
        self.selected_raw: bytes | None = None
        self.selected_drive: DriveCopy | None = None
        self.password_window: PasswordWindow | None = None
        self.chooser: Gtk.FileChooserNative | None = None
        self.confirmation: Adw.MessageDialog | None = None
        self.gated = False
        self.disconnect_pending = False
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18,
                          margin_top=18, margin_bottom=18, margin_start=18, margin_end=18)
        heading = _label("Local backups")
        heading.add_css_class("title-3")
        content.append(heading)
        content.append(_label("Save your complete library, including profiles, groups and hidden notes. Restore replaces the current library and keeps a recovery copy."))
        self.create_button = Gtk.Button(label="Create Backup…")
        self.create_button.set_visible(not startup_only and capture is not None)
        self.create_button.connect("clicked", lambda _: self._create())
        content.append(self.create_button)
        self.restore_button = Gtk.Button(label="Restore Backup…")
        self.restore_button.connect("clicked", lambda _: self._choose_restore())
        content.append(self.restore_button)
        self.status = _label("")
        self.status.add_css_class("dim-label")
        self._show_last_status()
        content.append(self.status)
        drive_heading = _label("Google Drive")
        drive_heading.add_css_class("title-3")
        content.append(drive_heading)
        content.append(_label("Save dated copies of your complete library to Google Drive. Refresh to select a copy, validate it and preview a replacement restore."))
        self.drive_status = _label("")
        content.append(self.drive_status)
        self.session_only = Gtk.CheckButton(label="Connect for this session only (do not save access)")
        content.append(self.session_only)
        self.connect_drive = Gtk.Button(label="Connect Google Drive…")
        self.connect_drive.connect("clicked", lambda _: self._connect_drive())
        content.append(self.connect_drive)
        self.disconnect_drive = Gtk.Button(label="Disconnect / Forget Saved Access")
        self.disconnect_drive.connect("clicked", lambda _: self._disconnect_drive())
        content.append(self.disconnect_drive)
        self.save_drive = Gtk.Button(label="Save Backup to Drive…")
        self.save_drive.set_visible(not startup_only and capture is not None)
        self.save_drive.connect("clicked", lambda _: self._create_drive())
        content.append(self.save_drive)
        self.retry_drive = Gtk.Button(label="Retry Drive Save")
        self.retry_drive.connect("clicked", lambda _: self._retry_drive())
        content.append(self.retry_drive)
        self.refresh_drive = Gtk.Button(label="Refresh Drive Copies")
        self.refresh_drive.connect("clicked", lambda _: self._refresh_drive())
        content.append(self.refresh_drive)
        self.drive_transfer_status = _label("")
        content.append(self.drive_transfer_status)
        self.drive_copies = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.drive_copies.append(_label("Refresh to discover completed copies. Contents will be validated when restoring."))
        copies_scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER,
                                          max_content_height=260, propagate_natural_height=True)
        copies_scroll.set_child(self.drive_copies)
        content.append(copies_scroll)
        self._drive_status()
        self._show_drive_last_status()
        self.progress = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.spinner = Gtk.Spinner()
        self.progress.append(self.spinner)
        self.progress_text = _label("")
        self.progress_text.set_hexpand(True)
        self.progress.append(self.progress_text)
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.connect("clicked", lambda _: self.service.cancel())
        self.progress.append(self.cancel_button)
        self.progress.set_visible(False)
        content.append(self.progress)
        self.unlock_button = Gtk.Button(label="Enter Backup Password…")
        self.unlock_button.connect("clicked", lambda _: self._ask_password())
        self.unlock_button.set_visible(False)
        content.append(self.unlock_button)
        self.preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.preview_text = _label("")
        self.preview_box.append(self.preview_text)
        self.final_restore = Gtk.Button(label="Restore This Backup…")
        self.final_restore.add_css_class("destructive-action")
        self.final_restore.connect("clicked", lambda _: self._confirm_restore())
        self.preview_box.append(self.final_restore)
        cancel_preview = Gtk.Button(label="Cancel Preview")
        cancel_preview.connect("clicked", lambda _: self._cancel_preview())
        self.preview_box.append(cancel_preview)
        self.cancel_preview = cancel_preview
        self.preview_box.set_visible(False)
        content.append(self.preview_box)
        scroll = Gtk.ScrolledWindow(hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True)
        scroll.set_child(content)
        toolbar.set_content(scroll)
        self.set_content(toolbar)
        self.connect("close-request", self._close)
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._key)
        self.add_controller(keys)

    def _key(self, _, key, *_args) -> bool:
        from gi.repository import Gdk
        if key == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _show_last_status(self) -> None:
        local = self.service.state().get("local", {})
        if isinstance(local, dict) and isinstance(local.get("captured_at"), str) and isinstance(local.get("location"), str):
            self.status.set_text(f"Last local backup: {local['captured_at']}\n{local['location']}")
        else:
            self.status.set_text("No local backup recorded on this computer.")

    def _busy(self, active: bool, message: str = "") -> None:
        for widget in (self.create_button, self.restore_button, self.final_restore,
                       self.connect_drive, self.disconnect_drive, self.session_only,
                       self.save_drive, self.retry_drive, self.refresh_drive,
                       self.drive_copies, self.unlock_button, self.cancel_preview):
            widget.set_sensitive(not active)
        self.progress.set_visible(active)
        self.spinner.set_spinning(active)
        self.progress_text.set_text(message)
        self.cancel_button.set_sensitive(active)
        if not active:
            self._drive_status()

    def _run(self, message: str, job: Callable, done: Callable) -> None:
        self._busy(True, message)
        def complete(result) -> None:
            self._busy(False)
            done(result)
        try:
            self.service.start(job, complete, self._failed)
        except Exception as exc:
            self._failed(exc)

    def _failed(self, error: Exception) -> None:
        self._busy(False)
        self._ungate()
        if isinstance(error, PasswordRequired):
            self.unlock_button.set_visible(True)
            self._ask_password()
            return
        if isinstance(error, AuthenticationError):
            self.unlock_button.set_visible(self.selected_raw is not None)
        message = str(error) if isinstance(error, (BackupError, OSError, TransitionError, DriveAuthError)) else "Could not complete this operation. Check available storage and retry."
        self._restore_status(message)
        self._drive_status()
        if not isinstance(error, OperationCancelled):
            show_error(self, "Backup operation could not finish", message)

    def _ask_password(self) -> None:
        if self.selected_raw is None:
            return
        self.password_window = PasswordWindow(self, lambda password: self._read_selection(password), unlock=True)
        self.password_window.present()
        self.password_window.password.grab_focus()

    def _restore_status(self, message: str) -> None:
        destination = self.drive_transfer_status if self.selected_drive is not None else self.status
        destination.set_text(message)

    def _drive_status(self) -> None:
        connection = self.service.drive_auth.connection
        if connection is None:
            self.drive_status.set_text("Not connected in this session. Connect to use saved access or authorize in your browser.")
            self.disconnect_drive.set_label("Forget Saved Access")
        else:
            mode = "This session only" if connection.session_only else "Access saved in the system keyring"
            self.drive_status.set_text(f"Connected: {connection.account}\n{mode}")
            self.disconnect_drive.set_label("Disconnect This Session" if connection.session_only else "Disconnect / Forget Saved Access")
        self.connect_drive.set_sensitive(connection is None and not self.service.busy)
        available = connection is not None and not self.service.busy
        self.save_drive.set_sensitive(available)
        self.refresh_drive.set_sensitive(available)
        attempt = self.service.drive_attempt
        retryable = attempt is not None and connection is not None and attempt.owner == (self.service.drive_auth.client_id, connection.account)
        self.retry_drive.set_visible(retryable)
        self.retry_drive.set_sensitive(available and retryable)

    def _connect_drive(self) -> None:
        session_only = self.session_only.get_active()
        self._run("Connecting Google Drive. Complete authorization in your browser…",
                  lambda cancel: self.service.drive_auth.connect(cancel, session_only=session_only),
                  lambda _: self._connected_drive())

    def _connected_drive(self) -> None:
        self._drive_status()
        self._show_drive_last_status()
        self._clear_drive_copies()
        self.drive_copies.append(_label("Refresh to discover completed copies."))

    def _show_drive_last_status(self) -> None:
        last = self.service.last_drive_status()
        if last is not None:
            self.drive_transfer_status.set_text(f"Last recorded Drive upload: captured {last['captured_at']}. Refresh to check available copies.")
        elif self.service.drive_auth.connection is not None:
            self.drive_transfer_status.set_text("No Drive upload recorded on this computer. Refresh to discover copies.")

    def _disconnect_drive(self) -> None:
        if self.service.busy:
            self.disconnect_pending = True
            self.service.cancel()
            self.disconnect_drive.set_sensitive(False)
            self.drive_transfer_status.set_text("Cancelling the Drive operation before disconnecting…")
            return
        self._clear_drive_copies()
        self.drive_transfer_status.set_text("")
        self._run("Forgetting Google Drive access on this computer…",
                  self.service.disconnect_drive, lambda _: self._drive_status())

    def _create_drive(self) -> None:
        self.password_window = PasswordWindow(self, self._save_drive, submit_label="Save to Drive")
        self.password_window.present()

    def _save_drive(self, password: str | None) -> None:
        try:
            payload = self.capture()
        except Exception as exc:
            self._failed(exc)
            return
        self._run_drive("Saving backup to Drive…", lambda cancel: self.service.save_drive(payload, password, cancel), self._drive_saved)

    def _run_drive(self, message: str, job: Callable, done: Callable, *, cancel_message: str | None = None) -> None:
        self.drive_transfer_status.set_text(message)
        self._busy(True, message)
        def completed(result) -> None:
            self._busy(False)
            if not self.disconnect_pending:
                done(result)
            self._finish_pending_disconnect()
        def failed(error) -> None:
            self._busy(False)
            message = str(error) if isinstance(error, (DriveAuthError, BackupError, OperationCancelled)) else "Drive operation failed. Check your connection and retry."
            if isinstance(error, OperationCancelled):
                message = cancel_message or "Drive operation cancelled. Retry checks the same copy; refresh can reveal a copy that finished remotely."
            self.drive_transfer_status.set_text(message)
            if not isinstance(error, OperationCancelled) and not self.disconnect_pending:
                show_error(self, "Google Drive operation could not finish", message)
            self._finish_pending_disconnect()
        try:
            self.service.start(job, completed, failed)
            self.disconnect_drive.set_sensitive(self.service.drive_auth.connection is not None)
        except Exception as exc:
            failed(exc)

    def _finish_pending_disconnect(self) -> None:
        if self.disconnect_pending:
            self.disconnect_pending = False
            self._disconnect_drive()

    def _drive_saved(self, result: DriveExportResult) -> None:
        copy = result.copy
        self.drive_transfer_status.set_text(f"Drive backup saved. Captured {copy.captured_at}\n{copy.name}"
                                          + (f"\n{result.warning}" if result.warning else ""))
        self._clear_drive_copies()
        self.drive_copies.append(_label("Refresh to list this and other completed copies."))
        self._drive_status()

    def _retry_drive(self) -> None:
        self._run_drive("Checking and retrying the same Drive copy…", self.service.retry_drive, self._drive_saved)

    def _clear_drive_copies(self) -> None:
        while child := self.drive_copies.get_first_child():
            self.drive_copies.remove(child)

    def _refresh_drive(self) -> None:
        self._clear_drive_copies()
        def listed(copies) -> None:
            self._clear_drive_copies()
            if not copies:
                self.drive_copies.append(_label("No completed compatible copies found."))
            for copy in copies:
                mode = "Password protected" if copy.protected else "Unprotected"
                row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                row.append(_label(f"{copy.captured_at} · {mode} · {copy.size:,} bytes\n{copy.name}"))
                select = Gtk.Button(label="Preview & Restore…")
                select.update_property([Gtk.AccessibleProperty.LABEL], [f"Preview and restore Drive backup {copy.name}"])
                select.connect("clicked", lambda _, selected=copy: self._download_drive(selected))
                row.append(select)
                self.drive_copies.append(row)
            self.drive_transfer_status.set_text(f"Found {len(copies)} completed copies. Select one to download and validate before restoring.")
        self._run_drive("Listing Drive copies…", self.service.list_drive, listed,
                        cancel_message="Listing cancelled. Your current library was kept. Refresh to try again.")

    def _download_drive(self, copy: DriveCopy) -> None:
        if self.service.busy or self.gated:
            return
        self._clear_selection()
        self._run_drive("Downloading the selected Drive backup…",
                        lambda cancel: self.service.download_drive(copy, cancel),
                        lambda raw: self._selected(raw, drive_copy=copy),
                        cancel_message="Download cancelled. Your current library was kept. Select a copy to try again.")

    def _create(self) -> None:
        self.password_window = PasswordWindow(self, self._choose_save)
        self.password_window.present()

    def _filter(self) -> Gtk.FileFilter:
        pattern = Gtk.FileFilter()
        pattern.set_name("Pinleaf backups")
        pattern.add_pattern("*.pinleaf-backup")
        return pattern

    def _choose_save(self, password: str | None) -> None:
        chooser = Gtk.FileChooserNative.new("Create Backup", self, Gtk.FileChooserAction.SAVE, "Save", "Cancel")
        chooser.add_filter(self._filter())
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        chooser.set_current_name(f"pinleaf-{stamp}-{uuid4()}.pinleaf-backup")
        self.chooser = chooser
        def response(dialog, response_id) -> None:
            selected = dialog.get_file() if response_id == Gtk.ResponseType.ACCEPT else None
            dialog.destroy()
            self.chooser = None
            if selected is None:
                return
            name = selected.get_path()
            if name is None:
                self._failed(BackupError("Choose a local file destination."))
                return
            path = Path(name)
            if path.exists():
                confirm = Adw.MessageDialog(transient_for=self, heading="Replace the existing backup?",
                    body=f"A file already exists at {path}. Replace it with a new backup?")
                confirm.add_response("cancel", "Cancel")
                confirm.add_response("replace", "Replace")
                confirm.set_default_response("cancel")
                confirm.set_close_response("cancel")
                confirm.set_response_appearance("replace", Adw.ResponseAppearance.DESTRUCTIVE)
                confirm.connect("response", lambda _, answer: self._export(path, password, True) if answer == "replace" else None)
                confirm.present()
            else:
                self._export(path, password, False)
        chooser.connect("response", response)
        chooser.show()

    def _export(self, path: Path, password: str | None, overwrite: bool = False) -> None:
        try:
            payload = self.capture()
        except Exception as exc:
            self._failed(exc)
            return
        def saved(result: ExportResult) -> None:
            self.status.set_text(f"Local backup saved. Captured {result.captured_at}\n{result.path}"
                                 + (f"\n{result.warning}" if result.warning else ""))
        self._run("Saving local backup…", lambda cancel: self.service.export(payload, path, password, overwrite, cancel), saved)

    def _choose_restore(self) -> None:
        chooser = Gtk.FileChooserNative.new("Restore Backup", self, Gtk.FileChooserAction.OPEN, "Open", "Cancel")
        chooser.add_filter(self._filter())
        self.chooser = chooser
        def response(dialog, response_id) -> None:
            selected = dialog.get_file() if response_id == Gtk.ResponseType.ACCEPT else None
            dialog.destroy()
            self.chooser = None
            if selected is None:
                return
            name = selected.get_path()
            if name is None:
                self._failed(BackupError("Choose a local backup file."))
                return
            self._run("Reading backup…", lambda cancel: self._read_file(Path(name), cancel), self._selected)
        chooser.connect("response", response)
        chooser.show()

    def _read_file(self, path, cancel) -> bytes:
        raw = read_bytes(path)
        check_cancel(cancel)
        return raw

    def _clear_selection(self) -> None:
        self.selected_raw = None
        self.selected_drive = None
        self.unlock_button.set_visible(False)
        if self.preview is not None:
            self.service.recovery.discard(self.preview)
            self.preview = None
        self.preview_box.set_visible(False)

    def _cancel_preview(self) -> None:
        if not self.service.busy and not self.gated:
            self._restore_status("Preview cancelled. Your current library was kept.")
            self._clear_selection()

    def _selected(self, raw: bytes, *, drive_copy: DriveCopy | None = None) -> None:
        self._clear_selection()
        self.selected_raw = raw
        self.selected_drive = drive_copy
        self._read_selection(None)

    def _read_selection(self, password: str | None) -> None:
        raw = self.selected_raw
        if raw is None:
            return
        selected = self.selected_drive
        job = (lambda cancel: self.service.stage_drive(raw, selected, password, cancel)) if selected is not None else (lambda cancel: self.service.recovery.stage(decode(raw, password), cancel))
        self._run("Validating backup…", job, self._show_preview)

    def _show_preview(self, preview: RestorePreview) -> None:
        self.preview = preview
        self.selected_raw = None
        self.unlock_button.set_visible(False)
        self._restore_status("Backup validated. Your current library has not been replaced.")
        payload = preview.backup.payload
        library = payload["library"]
        profiles = sum(row["deleted_at"] is None for row in library["profiles"])
        groups = sum(row["deleted_at"] is None for row in library["groups"])
        notes = [row for row in library["notes"] if row["deleted_at"] is None]
        hidden = sum(not row["is_open"] for row in notes)
        recovery = preview.recovery if self.capture else preview.stage.parent / "original"
        counts = " · ".join(f"{count} {name if count == 1 else name + 's'}" for count, name in
                            ((profiles, "profile"), (groups, "group"), (len(notes), "note")))
        source = f"Source: Google Drive · {self.selected_drive.name}\n" if self.selected_drive is not None else ""
        self.preview_text.set_text(source + f"Backup captured {payload['created_at']}\nPinleaf {payload['producer']['version']}\n"
            f"{counts} ({hidden} hidden)\n"
            f"{'Password protected' if preview.backup.protected else 'Unprotected backup'}\n\n"
            f"Restore replaces the entire current library. Recovery copy:\n{recovery}")
        self.preview_box.set_visible(True)
        self.final_restore.grab_focus()

    def _confirm_restore(self) -> None:
        if self.preview is None:
            return
        dialog = Adw.MessageDialog(transient_for=self, heading="Replace all current notes?",
            body="All profiles, groups and notes will be replaced by this backup. The current library will be preserved in the recovery location shown in the preview.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("restore", "Restore")
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.set_response_appearance("restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", lambda _, response: self._prepare_restore() if response == "restore" else None)
        self.confirmation = dialog
        dialog.present()

    def _prepare_restore(self) -> None:
        try:
            current = self.capture() if self.capture else None
            self.gate(True)
            self.gated = True
        except Exception as exc:
            self._failed(exc)
            return
        preview = self.preview
        self._run("Preserving the current library…", lambda cancel: self.service.recovery.prepare(preview, current, cancel), self._apply)

    def _apply(self, prepared: PreparedRestore) -> None:
        self._busy(True, "Restoring library…")
        self.cancel_button.set_sensitive(False)
        try:
            location = self.apply(prepared)
            self._restore_status(f"Library restored. Previous data preserved at:\n{location}")
            self.preview = None
            self.preview_box.set_visible(False)
        except Exception as exc:
            self._failed(exc)
        finally:
            self._ungate()
            self._busy(False)

    def _ungate(self) -> None:
        if self.gated:
            self.gate(False)
            self.gated = False

    def _close(self, _) -> bool:
        if self.service.busy or self.gated:
            self.service.cancel()
            self.progress_text.set_text("Cancelling operation…")
            return True
        if self.chooser is not None:
            self.chooser.destroy()
        if self.password_window is not None:
            self.password_window.destroy()
        if self.preview is not None:
            self.service.recovery.discard(self.preview)
        self.selected_raw = None
        self.selected_drive = None
        self.on_closed()
        self.destroy()
        return True
