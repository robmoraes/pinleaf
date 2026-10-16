from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from threading import Event
from unittest.mock import MagicMock, Mock, patch

from pinleaf.backup_format import decode
from pinleaf.backup_format import AuthenticationError, BackupError, PasswordRequired
from pinleaf.services.backup_service import BackupService
from pinleaf.services.drive_auth import DriveConnection
from pinleaf.services.drive_backup import (
    API, APP, UPLOAD, BACKUP_MIME, CHUNK_SIZE, FOLDER_MIME, DriveDestination,
    DriveCopy, DriveError, DriveHTTPError, DriveTransport, UploadAttempt,
)
from pinleaf.storage.atomic_files import OperationCancelled, check_cancel
from pinleaf.storage.library_backup import capture, read_library
from pinleaf.storage.sqlite_store import NoteStore
from pinleaf.services.note_service import NoteService


class FakeDrive:
    """Stateful provider double, including lost responses after remote commits."""
    def __init__(self):
        self.files, self.sessions, self.raw = {}, {}, {}
        self.calls = []
        self.counter = 0
        self.page_size = 100
        self.after = lambda _stage, _item: None
        self.before = lambda _method, _url: None

    def next_id(self):
        self.counter += 1
        return f"file-{self.counter}"

    def folder(self, name, kind=None, parent=None):
        file_id = self.next_id()
        item = {"id": file_id, "name": name, "mimeType": FOLDER_MIME,
                "trashed": False, "parents": [parent] if parent else [],
                "appProperties": {"application": APP, "kind": kind} if kind else {}}
        self.files[file_id] = item
        return file_id

    def request(self, method, url, cancel, *, params=None, body=None, data=None, headers=None, accepted=(200, 201)):
        check_cancel(cancel)
        params, headers = params or {}, headers or {}
        self.calls.append((method, url, copy.deepcopy(params), copy.deepcopy(body), headers.copy()))
        self.before(method, url)
        if method == "GET" and url == API:
            query = params["q"]
            kind = re.search(r"key='kind' and value='([^']+)'", query)[1]
            attempt = re.search(r"key='attempt' and value='([^']+)'", query)
            parent = re.search(r"'([^']+)' in parents", query)
            items = [copy.deepcopy(item) for item in self.files.values()
                     if item.get("appProperties", {}).get("application") == APP
                     and item["appProperties"].get("kind") == kind and not item.get("trashed")
                     and (not attempt or item["appProperties"].get("attempt") == attempt[1])
                     and (not parent or parent[1] in item.get("parents", []))]
            start = int(params.get("pageToken", "0"))
            page = {"files": items[start:start + self.page_size]}
            if start + self.page_size < len(items):
                page["nextPageToken"] = str(start + self.page_size)
            return 200, {}, page
        if method == "GET" and url == API + "/generateIds":
            return 200, {}, {"ids": [self.next_id()]}
        if method == "GET" and url.startswith(API + "/"):
            item = self.files.get(url.rsplit("/", 1)[1])
            if item is None:
                raise DriveHTTPError(404)
            result = copy.deepcopy(item)
            result.setdefault("capabilities", {"canDownload": True})
            return 200, {}, result
        if method == "POST" and url == API:
            file_id = self.folder(body["name"], body["appProperties"]["kind"], body.get("parents", [None])[0])
            self.after("folder", self.files[file_id])
            return 200, {}, copy.deepcopy(self.files[file_id])
        if method == "POST" and url == UPLOAD:
            if body["id"] in self.files:
                raise DriveHTTPError(409)
            location = UPLOAD + f"?uploadType=resumable&upload_id={len(self.sessions) + 1}"
            self.sessions[location] = {"metadata": copy.deepcopy(body), "data": b""}
            self.after("init", self.sessions[location])
            return 200, {"Location": location}, {}
        if method == "PUT" and url in self.sessions:
            session = self.sessions[url]
            total = int(headers["Content-Range"].split("/")[1])
            if headers["Content-Range"].startswith("bytes */"):
                if len(session["data"]) == total:
                    return 200, {}, copy.deepcopy(self.files[session["metadata"]["id"]])
                return 308, ({"Range": f"bytes=0-{len(session['data']) - 1}"} if session["data"] else {}), {}
            start = int(headers["Content-Range"].split(" ")[1].split("-")[0])
            if start != len(session["data"]):
                raise AssertionError("Wrong resumed offset")
            session["data"] += data
            final = len(session["data"]) == total
            if final:
                item = session["metadata"] | {"trashed": False, "size": str(total),
                        "md5Checksum": hashlib.md5(session["data"], usedforsecurity=False).hexdigest()}
                self.files[item["id"]] = item
                self.raw[item["id"]] = session["data"]
                self.after("uploaded", item)
                return 200, {}, copy.deepcopy(item)
            self.after("chunk", session)
            return 308, {"Range": f"bytes=0-{len(session['data']) - 1}"}, {}
        if method == "PATCH" and url.startswith(API + "/"):
            item = self.files[url.rsplit("/", 1)[1]]
            item.update(copy.deepcopy(body))
            self.after("published", item)
            return 200, {}, copy.deepcopy(item)
        raise AssertionError((method, url))

    def download(self, source, path, cancel):
        check_cancel(cancel)
        self.calls.append(("GET", f"{API}/{source.file_id}", {"alt": "media"}, None, {}))
        self.before("GET", f"{API}/{source.file_id}?alt=media")
        raw = self.raw[source.file_id]
        if len(raw) != source.size or hashlib.md5(raw, usedforsecurity=False).hexdigest() != source.checksum:
            raise DriveError("Synthetic changed download")
        with path.open("xb") as target:
            path.chmod(0o600)
            target.write(raw)
        self.after("downloaded", self.files[source.file_id])
        check_cancel(cancel)


def attempt(raw=b"synthetic portable bytes", protected=False):
    return UploadAttempt(("client", "test@example.org"), "2026-10-16T12:00:00+00:00", protected, raw)


class DriveDestinationTests(unittest.TestCase):
    def setUp(self):
        self.provider = FakeDrive()
        self.destination = DriveDestination(self.provider)

    def test_two_saves_have_distinct_ids_and_generic_names(self):
        first, second = attempt(), attempt(protected=True)
        one = self.destination.upload(first, Event())
        two = self.destination.upload(second, Event())
        self.assertNotEqual(one.file_id, two.file_id)
        self.assertNotEqual(one.name, two.name)
        self.assertFalse(one.protected)
        self.assertTrue(two.protected)
        self.assertEqual(len(self.destination.list_copies(Event())), 2)
        folders = [item for item in self.provider.files.values() if item["mimeType"] == FOLDER_MIME]
        self.assertEqual([item["name"] for item in folders], ["Pinleaf", "Backups"])

    def test_lost_upload_or_publish_response_reconciles_without_duplicate(self):
        for stage in ("uploaded", "published"):
            with self.subTest(stage=stage):
                provider = FakeDrive()
                destination = DriveDestination(provider)
                source = attempt()
                def lost(current, _item):
                    if current == stage:
                        raise DriveError("Synthetic lost response")
                provider.after = lost
                with self.assertRaises(DriveError):
                    destination.upload(source, Event())
                provider.after = lambda *_: None
                result = destination.upload(source, Event())
                self.assertEqual(result.file_id, source.file_id)
                self.assertEqual(len(provider.raw), 1)
                self.assertEqual(sum(method == "POST" and url == UPLOAD for method, url, *_ in provider.calls), 1)

    def test_mid_chunk_failure_resumes_from_provider_offset(self):
        source = attempt(b"x" * (CHUNK_SIZE * 2 + 7))
        def lost(stage, _item):
            if stage == "chunk":
                raise DriveError("Synthetic interrupted chunk")
        self.provider.after = lost
        with self.assertRaises(DriveError):
            self.destination.upload(source, Event())
        self.assertEqual(self.destination.list_copies(Event()), [])
        self.provider.after = lambda *_: None
        self.destination.upload(source, Event())
        self.assertEqual(self.provider.raw[source.file_id], source.raw)
        ranges = [headers["Content-Range"] for method, _, _, _, headers in self.provider.calls if method == "PUT"]
        self.assertIn(f"bytes */{len(source.raw)}", ranges)
        self.assertEqual(ranges.count(f"bytes 0-{CHUNK_SIZE - 1}/{len(source.raw)}"), 1)

    def test_cancelled_uploaded_copy_is_pending_until_deliberate_retry(self):
        source, cancel = attempt(), Event()
        self.provider.after = lambda stage, _: cancel.set() if stage == "uploaded" else None
        with self.assertRaises(OperationCancelled):
            self.destination.upload(source, cancel)
        self.assertEqual(self.destination.list_copies(Event()), [])
        self.provider.after = lambda *_: None
        self.destination.upload(source, Event())
        self.assertEqual(len(self.destination.list_copies(Event())), 1)

    def test_corrupted_upload_is_not_published(self):
        def corrupt(stage, item):
            if stage == "uploaded":
                item["md5Checksum"] = "0" * 32
        self.provider.after = corrupt
        with self.assertRaises(DriveError):
            self.destination.upload(attempt(), Event())
        self.assertEqual(self.destination.list_copies(Event()), [])
        self.assertFalse(any(method == "PATCH" for method, *_ in self.provider.calls))

    def test_quota_failure_preserves_earlier_copy_and_does_not_retry(self):
        first = self.destination.upload(attempt(), Event())
        self.provider.before = lambda method, url: (_ for _ in ()).throw(DriveHTTPError(403)) if method == "POST" and url == UPLOAD else None
        with self.assertRaises(DriveHTTPError):
            self.destination.upload(attempt(), Event())
        self.assertEqual([item.file_id for item in self.destination.list_copies(Event())], [first.file_id])
        self.assertEqual(sum(method == "POST" and url == UPLOAD for method, url, *_ in self.provider.calls), 2)

    def test_second_installation_discovers_all_marked_folders_and_pages(self):
        first = self.destination.upload(attempt(), Event())
        other_root = self.provider.folder("Pinleaf", "root")
        other_folder = self.provider.folder("Backups", "backups", other_root)
        second = attempt()
        second.folder_id = other_folder
        second.captured_at = "2026-10-17T12:00:00+00:00"
        two = self.destination.upload(second, Event())
        unrelated = self.provider.folder("Backups")
        unrelated_item = copy.deepcopy(self.provider.files[first.file_id])
        unrelated_item.update(id="unrelated", parents=[unrelated])
        self.provider.files["unrelated"] = unrelated_item
        self.provider.page_size = 1
        fresh = DriveDestination(self.provider)
        self.assertEqual([item.file_id for item in fresh.list_copies(Event())], [two.file_id, first.file_id])

    def test_unmarked_same_named_folders_are_never_reused(self):
        unrelated = self.provider.folder("Pinleaf")
        nested = self.provider.folder("Backups", parent=unrelated)
        source = attempt()
        self.destination.upload(source, Event())
        self.assertNotEqual(source.folder_id, nested)
        self.assertEqual(self.provider.files[nested]["appProperties"], {})

    def test_removed_pending_newer_and_malformed_copies_are_not_listed(self):
        result = self.destination.upload(attempt(), Event())
        original = copy.deepcopy(self.provider.files[result.file_id])
        for changes in ({"trashed": True}, {"size": "not-a-number"}, {"md5Checksum": "bad"},
                        {"appProperties": original["appProperties"] | {"status": "pending"}},
                        {"appProperties": original["appProperties"] | {"format": "99"}},
                        {"appProperties": original["appProperties"] | {"captured_at": "bad"}}):
            self.provider.files[result.file_id] = original | changes
            self.assertEqual(self.destination.list_copies(Event()), [])
        del self.provider.files[result.file_id]
        self.assertEqual(self.destination.list_copies(Event()), [])

    def test_repeated_pagination_and_incomplete_search_fail_visibly(self):
        for page in ({"files": [], "nextPageToken": "same"}, {"files": [], "incompleteSearch": True}):
            provider = Mock()
            provider.request.return_value = (200, {}, page)
            with self.assertRaises(DriveError):
                DriveDestination(provider).list_copies(Event())
            self.assertLessEqual(provider.request.call_count, 2)

    def test_expired_resumable_session_keeps_reserved_file_id(self):
        source = attempt()
        source.file_id = "reserved"
        source.folder_id = self.provider.folder("Backups", "backups")
        source.upload_url = UPLOAD + "?upload_id=expired"
        def fault(method, url):
            if url.endswith("upload_id=expired"):
                raise DriveHTTPError(410)
        self.provider.before = fault
        self.assertEqual(self.destination.upload(source, Event()).file_id, "reserved")

    def test_foreign_or_changed_metadata_is_never_updated(self):
        source = attempt()
        result = self.destination.upload(source, Event())
        self.provider.files[result.file_id]["appProperties"]["attempt"] = "foreign"
        previous = len(self.provider.calls)
        with self.assertRaises(DriveError):
            self.destination.upload(source, Event())
        self.assertFalse(any(method in ("POST", "PATCH", "PUT", "DELETE") for method, *_ in self.provider.calls[previous:]))

    def test_download_rechecks_selection_and_removal_before_transfer(self):
        selected = self.destination.upload(attempt(), Event())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "download"
            self.provider.files[selected.file_id]["md5Checksum"] = "0" * 32
            with self.assertRaises(DriveError):
                self.destination.download(selected, target, Event())
            del self.provider.files[selected.file_id]
            with self.assertRaises(DriveError):
                self.destination.download(selected, target, Event())
            self.assertFalse(target.exists())
            self.assertFalse(any(params.get("alt") == "media" for _, _, params, *_ in self.provider.calls))

    def test_download_rejects_restricted_or_moved_file(self):
        selected = self.destination.upload(attempt(), Event())
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "download"
            item = self.provider.files[selected.file_id]
            item["capabilities"] = {"canDownload": False}
            with self.assertRaises(DriveError):
                self.destination.download(selected, target, Event())
            item["capabilities"] = {"canDownload": True}
            item["parents"] = [self.provider.folder("Backups")]
            with self.assertRaises(DriveError):
                self.destination.download(selected, target, Event())
            self.assertFalse(target.exists())

    def test_download_changed_during_transfer_is_discarded(self):
        selected = self.destination.upload(attempt(), Event())
        def changed(stage, item):
            if stage == "downloaded":
                item["appProperties"]["status"] = "pending"
        self.provider.after = changed
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "download"
            with self.assertRaises(DriveError):
                self.destination.download(selected, target, Event())
            self.assertFalse(target.exists())


class DriveTransportTests(unittest.TestCase):
    def setUp(self):
        self.auth = Mock()
        self.auth.access_token.return_value = "synthetic-token"
        self.session = MagicMock()
        self.response = Mock(status_code=200, headers={})
        self.response.iter_content.return_value = [b"{}"]
        self.session.request.return_value.__enter__.return_value = self.response
        self.transport = DriveTransport(self.auth, session=self.session)

    def test_redirects_external_hosts_and_plain_http_never_receive_tokens(self):
        for url in ("http://www.googleapis.com/drive/v3/files", "https://evil.example/upload", "https://www.googleapis.com.evil.example/drive/v3/files", "https://user@www.googleapis.com/drive/v3/files"):
            with self.assertRaises(DriveError):
                self.transport.request("GET", url, Event())
        self.auth.access_token.assert_not_called()
        self.response.status_code = 302
        with self.assertRaises(DriveHTTPError):
            self.transport.request("GET", API, Event())
        self.assertFalse(self.session.request.call_args.kwargs["allow_redirects"])

    def test_timeouts_bounds_and_safe_provider_errors(self):
        self.transport.request("GET", API, Event())
        self.assertEqual(self.session.request.call_args.kwargs["timeout"], (10, 30))
        self.response.iter_content.return_value = [b"x" * (2 * 1024 * 1024 + 1)]
        with self.assertRaises(DriveError):
            self.transport.request("GET", API, Event())
        self.session.request.side_effect = RuntimeError("synthetic-private-token")
        with self.assertRaises(DriveError) as error:
            self.transport.request("GET", API, Event())
        self.assertNotIn("private-token", str(error.exception))

    def test_cancel_never_contacts_provider(self):
        cancel = Event()
        cancel.set()
        with self.assertRaises(OperationCancelled):
            self.transport.request("GET", API, cancel)
        self.session.request.assert_not_called()

    def selected(self, raw=b"synthetic-backup"):
        return DriveCopy("file-1", "backup", "2026-10-16T12:00:00+00:00", len(raw), False,
                         hashlib.md5(raw, usedforsecurity=False).hexdigest())

    def test_download_is_private_bounded_and_disables_redirects(self):
        raw = b"synthetic-backup"
        selected = self.selected(raw)
        self.session.get.return_value.__enter__.return_value = self.response
        self.response.headers = {"Content-Length": str(len(raw))}
        self.response.iter_content.return_value = [raw[:4], raw[4:]]
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "download"
            self.transport.download(selected, target, Event())
            self.assertEqual(target.read_bytes(), raw)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
        args = self.session.get.call_args
        self.assertEqual(args.kwargs["params"], {"alt": "media"})
        self.assertEqual(args.kwargs["timeout"], (10, 30))
        self.assertFalse(args.kwargs["allow_redirects"])

    def test_download_corruption_truncation_size_lies_and_redirect_are_rejected(self):
        selected = self.selected()
        self.session.get.return_value.__enter__.return_value = self.response
        for chunks, headers, status in (([b"x" * selected.size], {}, 200), ([b"small"], {}, 200),
                                        ([b"x" * (selected.size + 1)], {}, 200), ([], {"Content-Length": "999999999"}, 200),
                                        ([], {}, 302), ([], {}, 206), ([], {}, 401), ([], {}, 403), ([], {}, 404)):
            with self.subTest(status=status, headers=headers), tempfile.TemporaryDirectory() as directory:
                self.response.status_code, self.response.headers = status, headers
                self.response.iter_content.return_value = chunks
                target = Path(directory) / "download"
                with self.assertRaises(DriveError):
                    self.transport.download(selected, target, Event())
                self.assertFalse(target.exists())

    def test_download_cancel_midstream_and_connection_loss_remove_partial_file(self):
        selected = self.selected()
        self.session.get.return_value.__enter__.return_value = self.response
        for cancelled in (True, False):
            cancel = Event()
            def chunks(_size):
                yield b"synt"
                if cancelled:
                    cancel.set()
                    yield b"hetic"
                else:
                    raise RuntimeError("synthetic-private-token")
            self.response.iter_content.side_effect = chunks
            with tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "download"
                with self.assertRaises(OperationCancelled if cancelled else DriveError) as error:
                    self.transport.download(selected, target, cancel)
                self.assertNotIn("private-token", str(error.exception))
                self.assertFalse(target.exists())

    def test_download_never_clobbers_existing_file_or_uses_invalid_ids(self):
        self.session.get.return_value.__enter__.return_value = self.response
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "download"
            target.write_bytes(b"previous")
            with self.assertRaises(DriveError):
                self.transport.download(self.selected(), target, Event())
            self.assertEqual(target.read_bytes(), b"previous")
            for source in (replace(self.selected(), file_id="../escape"), replace(self.selected(), size=64 * 1024 * 1024 + 1)):
                self.auth.reset_mock()
                with self.assertRaises(DriveError):
                    self.transport.download(source, target, Event())
                self.auth.access_token.assert_not_called()


class DriveBackupServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.service = BackupService(Path(self.directory.name) / "notes.sqlite3", lambda call: call())
        self.service.drive_auth.connection = DriveConnection("test@example.org", True)
        self.service.drive_auth.client_id = "client"
        self.provider = FakeDrive()
        self.service.drive = DriveDestination(self.provider)
        root = Path(__file__).resolve().parents[1]
        self.payload = json.loads((root / "specs/015-local-backup-and-google-drive/contracts/examples/valid-unprotected.pinleaf-backup").read_bytes())["payload"]

    def tearDown(self):
        self.service.close()
        self.directory.cleanup()

    def test_both_modes_preserve_entire_captured_payload_and_keep_local_status(self):
        self.service.state_path.write_text('{"local":{"captured_at":"previous"}}')
        for password in (None, "synthetic-password"):
            result = self.service.save_drive(self.payload, password, Event())
            self.assertEqual(decode(self.provider.raw[result.copy.file_id], password).payload, self.payload)
            self.assertEqual(self.service.state()["local"]["captured_at"], "previous")
            self.assertEqual(self.service.state()["drive"]["file_id"], result.copy.file_id)
            self.assertEqual(self.service.last_drive_status()["file_id"], result.copy.file_id)
        self.assertIsNone(self.service.drive_attempt)
        self.service.drive_auth.connection = DriveConnection("other@example.org", True)
        self.assertIsNone(self.service.last_drive_status())
        self.assertFalse((Path(self.directory.name) / "notes.sqlite3").exists())

    def test_retry_reuses_identical_encrypted_bytes_and_preserves_last_success(self):
        first = self.service.save_drive(self.payload, None, Event())
        saved_state = self.service.state()
        def lost(stage, _item):
            if stage == "uploaded":
                raise DriveError("Synthetic lost response")
        self.provider.after = lost
        with self.assertRaises(DriveError):
            self.service.save_drive(self.payload, "synthetic-password", Event())
        pending = self.service.drive_attempt
        raw, file_id, uuid = pending.raw, pending.file_id, pending.attempt_id
        self.assertEqual(self.service.state(), saved_state)
        self.provider.after = lambda *_: None
        result = self.service.retry_drive(Event())
        self.assertEqual(result.copy.file_id, file_id)
        self.assertEqual(self.provider.raw[file_id], raw)
        self.assertEqual(self.provider.files[file_id]["appProperties"]["attempt"], uuid)
        self.assertNotEqual(result.copy.file_id, first.copy.file_id)

    def test_retry_cannot_upload_to_a_different_account(self):
        self.service.drive_attempt = attempt()
        self.service.drive_auth.connection = DriveConnection("other@example.org", True)
        with self.assertRaises(DriveError):
            self.service.retry_drive(Event())
        self.assertEqual(self.provider.calls, [])

    def test_successful_upload_survives_local_status_write_failure(self):
        with patch("pinleaf.services.backup_service.write_private", side_effect=OSError("Synthetic full disk")):
            result = self.service.save_drive(self.payload, None, Event())
        self.assertIsNotNone(result.warning)
        self.assertEqual(len(self.service.list_drive(Event())), 1)

    def test_no_connection_and_invalid_payload_create_no_remote_files(self):
        with self.assertRaises(ValueError):
            self.service.save_drive({}, None, Event())
        self.service.drive_auth.connection = None
        with self.assertRaises(DriveError):
            self.service.list_drive(Event())
        self.assertEqual(self.provider.calls, [])


class DriveRestoreServiceTests(unittest.TestCase):
    def setUp(self):
        DriveBackupServiceTests.setUp(self)
        self.target_root = Path(self.directory.name) / "second-installation"
        self.target_root.mkdir()
        self.target = BackupService(self.target_root / "notes.sqlite3", lambda call: call())
        self.target.drive_auth.connection = DriveConnection("test@example.org", True)
        self.target.drive_auth.client_id = "client"
        self.target.drive = DriveDestination(self.provider)
        self.store = NoteStore(self.target.recovery.database)
        self.notes = NoteService(self.store)
        self.note = self.notes.create_note()
        self.notes.update_content(self.note.id, "Original target library")

    def tearDown(self):
        self.target.close()
        self.store.close()
        DriveBackupServiceTests.tearDown(self)

    def selected(self, password=None):
        self.service.save_drive(self.payload, password, Event())
        self.assertFalse(self.target.state_path.exists())
        return self.target.list_drive(Event())[0]

    def test_fresh_installation_roundtrip_both_modes_and_repeated_restore(self):
        for password in (None, "synthetic-password"):
            selected = self.selected(password)
            raw = self.target.download_drive(selected, Event())
            self.assertEqual(list(self.target_root.glob("drive-download-*")), [])
            credentials = self.target.drive_auth.connection
            for _ in range(2):
                current = capture(self.store.connection)
                preview = self.target.stage_drive(raw, selected, password, Event())
                prepared = self.target.recovery.prepare(preview, current, Event())
                recovery = self.target.recovery.apply(self.store, prepared)
                self.assertEqual(read_library(self.store.connection), self.payload["library"])
                self.assertEqual(decode(recovery.read_bytes()).payload["library"], current["library"])
                self.assertIs(self.target.drive_auth.connection, credentials)
            self.assertFalse(self.target.state_path.exists())

    def test_password_detection_wrong_password_and_cancel_leave_library_unchanged(self):
        selected = self.selected("synthetic-password")
        current = read_library(self.store.connection)
        raw = self.target.download_drive(selected, Event())
        with self.assertRaises(PasswordRequired):
            self.target.stage_drive(raw, selected, None, Event())
        with self.assertRaises(AuthenticationError):
            self.target.stage_drive(raw, selected, "wrong", Event())
        preview = self.target.stage_drive(raw, selected, "synthetic-password", Event())
        self.target.recovery.discard(preview)
        self.assertFalse(preview.stage.exists())
        self.assertEqual(read_library(self.store.connection), current)

    def test_edits_after_remote_preview_are_preserved_in_recovery(self):
        selected = self.selected()
        raw = self.target.download_drive(selected, Event())
        preview = self.target.stage_drive(raw, selected, None, Event())
        self.notes.update_content(self.note.id, "Edit after remote preview")
        current = capture(self.store.connection)
        prepared = self.target.recovery.prepare(preview, current, Event())
        recovery = self.target.recovery.apply(self.store, prepared)
        self.assertEqual(decode(recovery.read_bytes()).payload["library"], current["library"])

    def test_malformed_or_incompatible_download_cannot_reach_restore(self):
        selected = self.selected()
        current = read_library(self.store.connection)
        for invalid in (b"{}", b"not-json"):
            self.provider.raw[selected.file_id] = invalid
            item = self.provider.files[selected.file_id]
            item["size"] = str(len(invalid))
            item["md5Checksum"] = hashlib.md5(invalid, usedforsecurity=False).hexdigest()
            copy = self.target.list_drive(Event())[0]
            raw = self.target.download_drive(copy, Event())
            with self.assertRaises(BackupError):
                self.target.stage_drive(raw, copy, None, Event())
        self.assertEqual(read_library(self.store.connection), current)
        self.assertFalse(self.target.recovery.staging.exists())

    def test_protection_and_capture_metadata_must_match_validated_contents(self):
        selected = self.selected()
        raw = self.target.download_drive(selected, Event())
        for changed in (replace(selected, protected=True), replace(selected, captured_at="2026-10-01T00:00:00+00:00")):
            with self.assertRaises(DriveError):
                self.target.stage_drive(raw, changed, None, Event())
        self.assertFalse(self.target.recovery.staging.exists())

    def test_failed_or_cancelled_download_cleans_private_staging(self):
        selected = self.selected()
        current = read_library(self.store.connection)
        def interrupted(method, url):
            if url.endswith("?alt=media"):
                raise DriveError("Synthetic network interruption")
        self.provider.before = interrupted
        with self.assertRaises(DriveError):
            self.target.download_drive(selected, Event())
        self.assertEqual(list(self.target_root.glob("drive-download-*")), [])
        self.provider.before = lambda *_: None
        cancel = Event()
        self.provider.after = lambda stage, _: cancel.set() if stage == "downloaded" else None
        with self.assertRaises(OperationCancelled):
            self.target.download_drive(selected, cancel)
        self.assertEqual(list(self.target_root.glob("drive-download-*")), [])
        self.assertEqual(read_library(self.store.connection), current)

    def test_validated_remote_preview_restores_offline_without_reconnecting(self):
        selected = self.selected()
        raw = self.target.download_drive(selected, Event())
        preview = self.target.stage_drive(raw, selected, None, Event())
        self.target.drive_auth.connection = None
        self.target.drive_auth.credentials = None
        self.provider.before = Mock(side_effect=AssertionError("No network after validation"))
        current = capture(self.store.connection)
        prepared = self.target.recovery.prepare(preview, current, Event())
        self.target.recovery.apply(self.store, prepared)
        self.assertEqual(read_library(self.store.connection), self.payload["library"])
        self.assertIsNone(self.target.drive_auth.connection)
        self.provider.before.assert_not_called()
