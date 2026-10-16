"""Live, explicit two-installation drill with synthetic notes and scoped cleanup.

Requires --live --cleanup-created and the registered development client override.
Both installations authorize independently in the system browser. Only files
created by this invocation are deleted; pre-existing Drive copies are preserved.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Event

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pinleaf.backup_format import decode
from pinleaf.services.backup_service import BackupService
from pinleaf.services.drive_auth import DriveAuth, DriveAuthError
from pinleaf.services.drive_backup import API, DriveCopy, DriveDestination, DriveError, DriveTransport
from pinleaf.services.note_service import NoteService
from pinleaf.storage.library_backup import build_stage, capture, read_library
from pinleaf.storage.sqlite_store import NoteStore

PASSWORD = "Synthetic-two-installations-only-789"


def synthetic_library() -> dict:
    payload = json.loads((ROOT / "specs/015-local-backup-and-google-drive/contracts/examples/valid-unprotected.pinleaf-backup").read_bytes())["payload"]
    prototype = payload["library"]["notes"][0]
    for index in range(1000 - len(payload["library"]["notes"])):
        note = copy.deepcopy(prototype)
        note.update(id=f"d04-synthetic-{index:04d}", content=f"Synthetic portability note {index}: café, checklist and Unicode ✓",
                    is_open=0, deleted_at=prototype["updated_at"] if index % 17 == 0 else None)
        payload["library"]["notes"].append(note)
    payload["library"]["notes"].sort(key=lambda note: note["id"])
    return payload


def run_drill(report: Path) -> None:
    cancel = Event()
    created: list[DriveCopy] = []
    auth_objects: list[DriveAuth] = []
    services: list[BackupService] = []
    stores: list[NoteStore] = []
    result = {"status": "RUNNING", "notes": 1000, "independent_authorizations": False,
              "modes": [], "a_disconnected_b_refreshed": False, "created_files": 0,
              "removed_files": 0, "preexisting_files_preserved": False}
    with tempfile.TemporaryDirectory(prefix="pinleaf-two-installations-") as directory:
        root = Path(directory)
        source_dir, target_dir = root / "installation-a", root / "installation-b"
        source_dir.mkdir(mode=0o700)
        target_dir.mkdir(mode=0o700)
        build_stage(synthetic_library(), source_dir / "notes.sqlite3")
        source_store, target_store = NoteStore(source_dir / "notes.sqlite3"), NoteStore(target_dir / "notes.sqlite3")
        stores.extend((source_store, target_store))
        source, target = BackupService(source_dir / "notes.sqlite3", lambda callback: callback()), BackupService(target_dir / "notes.sqlite3", lambda callback: callback())
        services.extend((source, target))
        auth_a, auth_b = source.drive_auth, target.drive_auth
        auth_objects.extend((auth_a, auth_b))
        cleanup_auth = None
        initial_ids = None
        try:
            print("AUTHORIZE_INSTALLATION_A_IN_BROWSER", flush=True)
            auth_a.connect(cancel)
            cleanup_auth = auth_a
            print("INSTALLATION_A_CONNECTED; AUTHORIZE_INSTALLATION_B_IN_BROWSER", flush=True)
            auth_b.connect(cancel)
            cleanup_auth = auth_b
            if auth_a.account_id != auth_b.account_id:
                raise DriveError("The two installations must use the same Google account.")
            result["independent_authorizations"] = True
            print("BOTH_INSTALLATIONS_CONNECTED_INDEPENDENTLY", flush=True)
            initial_ids = {item.file_id for item in target.list_drive(cancel)}
            payload = capture(source_store.connection)
            original_source = read_library(source_store.connection)
            for password in (None, PASSWORD):
                uploaded = source.save_drive(payload, password, cancel).copy
                created.append(uploaded)
                result["created_files"] = len(created)
                assert not target.state_path.exists(), "Target must have no source upload history"
                discovered = {item.file_id: item for item in target.list_drive(cancel)}
                selected = discovered[uploaded.file_id]
                raw = target.download_drive(selected, cancel)
                preview = target.stage_drive(raw, selected, password, cancel)
                # A genuine edit after preview must survive in the recovery copy.
                notes = NoteService(target_store)
                changed = notes.create_note()
                notes.update_content(changed.id, "Synthetic target edit made after preview")
                before = capture(target_store.connection)
                prepared = target.recovery.prepare(preview, before, cancel)
                recovery = target.recovery.apply(target_store, prepared)
                assert decode(recovery.read_bytes()).payload["library"] == before["library"]
                assert read_library(target_store.connection) == payload["library"]
                result["modes"].append("protected" if password else "unprotected")
                print("A_TO_B_RESTORE_PASS", result["modes"][-1], flush=True)
            # Uploading from B cannot replace either copy created by A.
            third = target.save_drive(capture(target_store.connection), None, cancel).copy
            created.append(third)
            result["created_files"] = len(created)
            assert len({item.file_id for item in created}) == 3
            assert {item.file_id for item in source.list_drive(cancel)}.issuperset(item.file_id for item in created)
            client_id = auth_a.client_id
            source.disconnect_drive(cancel)
            assert auth_a.store.load(client_id) is None
            assert read_library(source_store.connection) == original_source
            # A fresh B process-equivalent object reads only B's independent key.
            def no_new_consent(*_args):
                raise DriveAuthError("B's saved access was lost after disconnecting A.")
            restarted_b = DriveAuth(target_dir, authorizer=no_new_consent)
            auth_objects.append(restarted_b)
            assert restarted_b.connection is None and restarted_b.credentials is None
            restarted_b.connect(cancel)
            assert restarted_b.account_id == auth_b.account_id
            restarted_b.credentials.expiry = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=5)
            restarted_b.access_token(cancel)  # Real refresh, not just a cached access token.
            target.drive_auth = restarted_b
            target.drive = DriveDestination(DriveTransport(restarted_b))
            cleanup_auth = restarted_b
            assert {item.file_id for item in target.list_drive(cancel)}.issuperset(item.file_id for item in created)
            assert decode(target.download_drive(created[0], cancel)).payload["library"] == payload["library"]
            target_store.close()
            target_store = NoteStore(target_dir / "notes.sqlite3")
            stores.append(target_store)
            assert read_library(target_store.connection) == payload["library"]
            result["a_disconnected_b_refreshed"] = True
            print("DISCONNECT_A_RESTART_AND_REFRESH_B_PASS", flush=True)
            result["status"] = "PASS"
        finally:
            # This helper has no generic delete or pruning action. Every ID came
            # from this run's successful create result and is rechecked exactly.
            cleanup_errors = []
            if cleanup_auth is not None:
                transport = DriveTransport(cleanup_auth)
                destination = DriveDestination(transport)
                try:
                    for selected in created:
                        item = destination._get(selected.file_id, Event())
                        if item is not None:
                            if destination._copy(item) != selected:
                                raise DriveError("A test-created file changed; it was preserved rather than deleted.")
                            transport.request("DELETE", f"{API}/{selected.file_id}", Event(), accepted=(204,))
                        result["removed_files"] += 1
                    if initial_ids is not None:
                        final_ids = {item.file_id for item in destination.list_copies(Event())}
                        assert initial_ids <= final_ids, "A pre-existing copy changed during the drill"
                        assert not final_ids.intersection(item.file_id for item in created)
                        result["preexisting_files_preserved"] = True
                except (DriveAuthError, AssertionError):
                    cleanup_errors.append("Remote test cleanup needs inspection; unrelated files were not deleted.")
                    result["retained_test_files"] = [{"file_id": item.file_id, "name": item.name} for item in created[result["removed_files"]:]]
            for auth in reversed(auth_objects):
                try:
                    auth.disconnect(Event())
                except DriveAuthError:
                    cleanup_errors.append("A disposable installation's keyring item needs cleanup.")
            for service in services:
                service.close()
            for store in stores:
                store.close()
            report.parent.mkdir(parents=True, exist_ok=True)
            if cleanup_errors or result["status"] != "PASS":
                result["status"] = "FAIL"
                result["cleanup_notes"] = cleanup_errors
            report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)
    if result["status"] != "PASS":
        raise DriveError("The live drill did not finish all cleanup checks. See the local report.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.add_argument("--cleanup-created", action="store_true", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        run_drill(args.report)
    except DriveAuthError as error:
        raise SystemExit(str(error)) from None


if __name__ == "__main__":
    main()
