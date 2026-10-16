"""Bounded Drive v3 destination for portable backups; no startup network."""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from pinleaf.backup_format import MAX_FILE_BYTES
from pinleaf.services.drive_auth import DriveAuthError
from pinleaf.storage.atomic_files import OperationCancelled, check_cancel

API = "https://www.googleapis.com/drive/v3/files"
UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
APP = "dev.pinleaf.Pinleaf"
FOLDER_MIME = "application/vnd.google-apps.folder"
BACKUP_MIME = "application/octet-stream"
FIELDS = "id,name,mimeType,parents,appProperties,size,md5Checksum,trashed,capabilities(canDownload)"
MAX_PAGES = 100
MAX_ITEMS = 10000
CHUNK_SIZE = 256 * 1024


class DriveError(DriveAuthError):
    pass


class DriveHTTPError(DriveError):
    def __init__(self, status: int) -> None:
        self.status = status
        messages = {
            401: "Google access expired or was revoked. Disconnect and reconnect.",
            403: "Google denied access or a quota was reached. Check Drive access and storage, then retry.",
            404: "The Drive item is no longer available. Refresh the list or retry the save.",
            409: "The Drive item already exists. Retry to check this attempt before uploading again.",
            410: "The Drive upload session expired. Retry this save.",
            429: "Google is limiting requests. Wait and retry deliberately.",
        }
        super().__init__(messages.get(status, "Google Drive could not finish this request. Check your connection and retry."))


def _identifier(value: object) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value) is None:
        raise DriveError("Google returned an invalid file identifier. Refresh and retry.")
    return value


def _timestamp(value: object) -> str:
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError()
    stamp = datetime.fromisoformat(value)
    if stamp.tzinfo is None:
        raise ValueError()
    return value


@dataclass(frozen=True)
class DriveCopy:
    file_id: str
    name: str
    captured_at: str
    size: int
    protected: bool
    checksum: str


@dataclass
class UploadAttempt:
    owner: tuple[str, str]
    captured_at: str
    protected: bool
    raw: bytes = field(repr=False)
    attempt_id: str = field(default_factory=lambda: str(uuid4()))
    file_id: str | None = None
    folder_id: str | None = None
    upload_url: str | None = field(default=None, repr=False)

    @property
    def name(self) -> str:
        stamp = datetime.fromisoformat(self.captured_at).strftime("%Y%m%dT%H%M%SZ")
        return f"pinleaf-{stamp}-{self.attempt_id}.pinleaf-backup"

    @property
    def properties(self) -> dict[str, str]:
        return {"application": APP, "kind": "backup", "format": "1",
                "status": "pending", "attempt": self.attempt_id,
                "captured_at": self.captured_at,
                "protection": "password" if self.protected else "none"}


class DriveTransport:
    """Explicit bearer requests, no redirects or automatic transfer retries."""
    def __init__(self, auth, *, session=None) -> None:
        self.auth = auth
        self.session = session

    def request(self, method: str, url: str, cancel: Event, *, params=None,
                body: dict | None = None, data: bytes | None = None,
                headers: dict | None = None, accepted=(200, 201)) -> tuple[int, dict, dict]:
        parts = urlsplit(url)
        if (parts.scheme != "https" or parts.netloc != "www.googleapis.com"
                or parts.fragment or not (parts.path == "/drive/v3/files"
                    or parts.path.startswith("/drive/v3/files/")
                    or parts.path == "/upload/drive/v3/files"
                    or parts.path.startswith("/upload/drive/v3/files/"))):
            raise DriveError("Google returned an unexpected upload destination.")
        check_cancel(cancel)
        token = self.auth.access_token(cancel)
        try:
            import requests
            own_session = self.session is None
            session = self.session or requests.Session()
            try:
                with session.request(method, url, params=params, json=body, data=data,
                                     headers=(headers or {}) | {"Authorization": f"Bearer {token}"},
                                     timeout=(10, 30), allow_redirects=False, stream=True) as response:
                    if response.status_code not in accepted:
                        raise DriveHTTPError(response.status_code)
                    raw = bytearray()
                    for chunk in response.iter_content(8192):
                        check_cancel(cancel)
                        raw.extend(chunk)
                        if len(raw) > 2 * 1024 * 1024:
                            raise DriveError("Google returned too much metadata. Refresh and retry.")
                    result = json.loads(raw) if raw else {}
                    if not isinstance(result, dict):
                        raise DriveError("Google returned invalid metadata. Refresh and retry.")
                    check_cancel(cancel)
                    return response.status_code, dict(response.headers), result
            finally:
                if own_session:
                    session.close()
        except (DriveError, OperationCancelled):
            raise
        except Exception:
            raise DriveError("Drive transfer interrupted. Check your connection and retry; the same attempt will be checked first.") from None

    def download(self, copy: DriveCopy, path: Path, cancel: Event) -> None:
        """Stream a selected blob into an exclusive private file, capped at 64 MiB."""
        file_id = _identifier(copy.file_id)
        if not 0 < copy.size <= MAX_FILE_BYTES:
            raise DriveError("This Drive backup exceeds the supported size limit.")
        check_cancel(cancel)
        token = self.auth.access_token(cancel)
        created = False
        try:
            import requests
            own_session = self.session is None
            session = self.session or requests.Session()
            try:
                with session.get(f"{API}/{file_id}", params={"alt": "media"},
                                 headers={"Authorization": f"Bearer {token}", "Accept-Encoding": "identity"},
                                 timeout=(10, 30), allow_redirects=False, stream=True) as response:
                    if response.status_code != 200:
                        raise DriveHTTPError(response.status_code)
                    length = response.headers.get("Content-Length")
                    if length is not None and int(length) != copy.size:
                        raise DriveError("The Drive backup size changed. Refresh and select it again.")
                    digest, size = hashlib.md5(usedforsecurity=False), 0
                    with path.open("xb") as target:
                        created = True
                        path.chmod(0o600)
                        for chunk in response.iter_content(64 * 1024):
                            check_cancel(cancel)
                            size += len(chunk)
                            if size > copy.size or size > MAX_FILE_BYTES:
                                raise DriveError("The Drive download exceeds its expected size. Refresh and retry.")
                            target.write(chunk)
                            digest.update(chunk)
                        if size != copy.size or digest.hexdigest() != copy.checksum:
                            raise DriveError("The Drive download is incomplete or changed. Refresh and retry.")
                        target.flush()
                        os.fsync(target.fileno())
                    check_cancel(cancel)
            finally:
                if own_session:
                    session.close()
        except BaseException as error:
            if created:
                path.unlink(missing_ok=True)
            if isinstance(error, (DriveError, OperationCancelled, KeyboardInterrupt, SystemExit)):
                raise
            raise DriveError("Could not download the Drive backup. Check your connection and available storage, then retry.") from None


class DriveDestination:
    def __init__(self, transport: DriveTransport) -> None:
        self.transport = transport

    def _request(self, method, url, cancel, **kwargs):
        return self.transport.request(method, url, cancel, **kwargs)

    def _list(self, query: str, cancel: Event) -> list[dict]:
        result, seen, tokens = [], set(), set()
        token = None
        for _ in range(MAX_PAGES):
            check_cancel(cancel)
            params = {"q": query, "spaces": "drive", "pageSize": 100,
                      "fields": f"nextPageToken,incompleteSearch,files({FIELDS})"}
            if token is not None:
                params["pageToken"] = token
            _, _, page = self._request("GET", API, cancel, params=params)
            files = page.get("files")
            if not isinstance(files, list) or page.get("incompleteSearch", False) is not False:
                raise DriveError("Drive returned an incomplete listing. Refresh and retry.")
            for item in files:
                if not isinstance(item, dict):
                    raise DriveError("Drive returned invalid file metadata.")
                file_id = _identifier(item.get("id"))
                if file_id not in seen:
                    seen.add(file_id)
                    result.append(item)
                    if len(result) > MAX_ITEMS:
                        raise DriveError("Too many Drive items. Manage old copies in Drive before refreshing.")
            token = page.get("nextPageToken")
            if token is None:
                return result
            if not isinstance(token, str) or not token or len(token) > 4096 or token in tokens:
                raise DriveError("Drive pagination is invalid. Refresh and retry.")
            tokens.add(token)
        raise DriveError("Drive listing reached its limit. Manage old copies in Drive before refreshing.")

    @staticmethod
    def _query(kind: str) -> str:
        return ("trashed = false and "
                f"appProperties has {{ key='application' and value='{APP}' }} and "
                f"appProperties has {{ key='kind' and value='{kind}' }}")

    def _folders(self, kind: str, cancel: Event, parent: str | None = None) -> list[dict]:
        query = self._query(kind) + f" and mimeType = '{FOLDER_MIME}'"
        if parent is not None:
            query += f" and '{_identifier(parent)}' in parents"
        items = self._list(query, cancel)
        result = []
        for item in items:
            props, parents = item.get("appProperties"), item.get("parents", [])
            if (item.get("mimeType") == FOLDER_MIME and item.get("trashed") is False
                    and isinstance(props, dict) and props.get("application") == APP
                    and props.get("kind") == kind and isinstance(parents, list)
                    and (parent is None or parent in parents)):
                result.append(item)
        return result

    def _folder(self, kind: str, name: str, cancel: Event, parent: str | None = None) -> str:
        items = self._folders(kind, cancel, parent)
        if items:
            return min(item["id"] for item in items)
        body = {"name": name, "mimeType": FOLDER_MIME,
                "appProperties": {"application": APP, "kind": kind}}
        if parent is not None:
            body["parents"] = [parent]
        _, _, result = self._request("POST", API, cancel, body=body, params={"fields": FIELDS})
        if (result.get("mimeType") != FOLDER_MIME or result.get("trashed") is not False
                or result.get("appProperties") != body["appProperties"]
                or (parent is not None and parent not in result.get("parents", []))):
            raise DriveError("Google did not confirm the backup folder. Retry to discover it.")
        return _identifier(result.get("id"))

    def _get(self, file_id: str, cancel: Event) -> dict | None:
        try:
            _, _, result = self._request("GET", f"{API}/{_identifier(file_id)}", cancel, params={"fields": FIELDS})
            return result
        except DriveHTTPError as error:
            if error.status == 404:
                return None
            raise

    @staticmethod
    def _copy(item: dict) -> DriveCopy | None:
        try:
            props = item["appProperties"]
            if (props.get("application") != APP or props.get("kind") != "backup"
                    or props.get("format") != "1" or props.get("status") != "complete"
                    or props.get("protection") not in ("none", "password")
                    or item.get("trashed") is not False or item.get("mimeType") != BACKUP_MIME):
                return None
            UUID(props["attempt"])
            captured = _timestamp(props["captured_at"])
            size = int(item["size"])
            if (not 0 < size <= MAX_FILE_BYTES or str(size) != str(item["size"])
                    or re.fullmatch(r"[a-f0-9]{32}", item["md5Checksum"]) is None):
                return None
            file_id = _identifier(item["id"])
            name = item["name"]
            if not isinstance(name, str) or not 0 < len(name) <= 512:
                return None
            return DriveCopy(file_id, name, captured, size, props["protection"] == "password", item["md5Checksum"])
        except (KeyError, ValueError, TypeError, AttributeError, DriveError):
            return None

    def list_copies(self, cancel: Event) -> list[DriveCopy]:
        folders = {item["id"] for item in self._folders("backups", cancel)}
        if not folders:
            return []
        copies = []
        for item in self._list(self._query("backup"), cancel):
            parents = item.get("parents")
            if not isinstance(parents, list) or not any(parent in folders for parent in parents if isinstance(parent, str)):
                continue
            copy = self._copy(item)
            if copy is not None:
                copies.append(copy)
        return sorted(copies, key=lambda copy: (datetime.fromisoformat(copy.captured_at), copy.file_id), reverse=True)

    def download(self, copy: DriveCopy, path: Path, cancel: Event) -> None:
        """Recheck the selected complete copy before and after reading its bytes."""
        check_cancel(cancel)
        item = self._get(copy.file_id, cancel)
        if item is None or self._copy(item) != copy:
            raise DriveError("This Drive copy was removed or changed. Refresh and select a backup again.")
        capabilities = item.get("capabilities")
        if not isinstance(capabilities, dict) or capabilities.get("canDownload") is not True:
            raise DriveError("Google does not allow downloading this copy. Check access or select another backup.")
        folders = {folder["id"] for folder in self._folders("backups", cancel)}
        parents = item.get("parents", [])
        if not isinstance(parents, list) or not any(parent in folders for parent in parents if isinstance(parent, str)):
            raise DriveError("This copy is no longer in a Pinleaf backup folder. Refresh and select another backup.")
        self.transport.download(copy, path, cancel)
        try:
            confirmed = self._get(copy.file_id, cancel)
            if (confirmed is None or self._copy(confirmed) != copy
                    or confirmed.get("parents") != parents):
                raise DriveError("The Drive copy changed during download. Refresh and select it again.")
            check_cancel(cancel)
        except BaseException:
            path.unlink(missing_ok=True)
            raise

    def _verify(self, attempt: UploadAttempt, item: dict) -> None:
        props = item.get("appProperties", {})
        expected = attempt.properties
        if (item.get("id") != attempt.file_id or item.get("trashed") is not False
                or item.get("mimeType") != BACKUP_MIME
                or not isinstance(item.get("parents"), list) or attempt.folder_id not in item["parents"]
                or not isinstance(props, dict)
                or any(props.get(key) != value for key, value in expected.items() if key != "status")
                or props.get("status") not in ("pending", "complete")
                or item.get("size") != str(len(attempt.raw))
                or item.get("md5Checksum") != hashlib.md5(attempt.raw, usedforsecurity=False).hexdigest()):
            raise DriveError("The uploaded copy does not match this attempt. It was not published; start a new save.")

    def upload(self, attempt: UploadAttempt, cancel: Event) -> DriveCopy:
        check_cancel(cancel)
        if not 0 < len(attempt.raw) <= MAX_FILE_BYTES:
            raise DriveError("The backup exceeds the supported size limit.")
        if attempt.folder_id is None:
            root = self._folder("root", "Pinleaf", cancel)
            attempt.folder_id = self._folder("backups", "Backups", cancel, root)
        if attempt.file_id is None:
            # Reconcile the UUID before allocating a file, even without local history.
            matches = self._list(self._query("backup") + f" and appProperties has {{ key='attempt' and value='{UUID(attempt.attempt_id)}' }}", cancel)
            if len(matches) > 1:
                raise DriveError("Several Drive files match this attempt. Start a new save.")
            if matches:
                attempt.file_id = _identifier(matches[0]["id"])
            else:
                _, _, result = self._request("GET", f"{API}/generateIds", cancel, params={"count": 1, "space": "drive", "type": "files"})
                ids = result.get("ids")
                if not isinstance(ids, list) or len(ids) != 1:
                    raise DriveError("Google did not allocate a backup identifier. Retry.")
                attempt.file_id = _identifier(ids[0])
        existing = self._get(attempt.file_id, cancel)
        if existing is None:
            self._upload_bytes(attempt, cancel)
            existing = self._get(attempt.file_id, cancel)
        if existing is None:
            raise DriveError("Google has not confirmed the uploaded copy. Retry to check the same attempt.")
        self._verify(attempt, existing)
        if existing["appProperties"]["status"] != "complete":
            check_cancel(cancel)
            self._request("PATCH", f"{API}/{attempt.file_id}", cancel,
                          body={"appProperties": attempt.properties | {"status": "complete"}}, params={"fields": FIELDS})
        confirmed = self._get(attempt.file_id, cancel)
        if confirmed is None:
            raise DriveError("The completed copy is no longer available. Refresh or start a new save.")
        self._verify(attempt, confirmed)
        result = self._copy(confirmed)
        if result is None:
            raise DriveError("Google has not confirmed publication. Retry the same attempt.")
        attempt.upload_url = None
        return result

    def _upload_bytes(self, attempt: UploadAttempt, cancel: Event) -> None:
        size, offset = len(attempt.raw), 0
        if attempt.upload_url is not None:
            try:
                status, headers, _ = self._request("PUT", attempt.upload_url, cancel, data=b"",
                                                  headers={"Content-Range": f"bytes */{size}"}, accepted=(200, 201, 308))
                if status in (200, 201):
                    return
                offset = self._offset(headers, size)
            except DriveHTTPError as error:
                if error.status not in (404, 410):
                    raise
                attempt.upload_url = None
        if attempt.upload_url is None:
            body = {"id": attempt.file_id, "name": attempt.name, "mimeType": BACKUP_MIME,
                    "parents": [attempt.folder_id], "appProperties": attempt.properties}
            _, headers, _ = self._request("POST", UPLOAD, cancel, params={"uploadType": "resumable", "fields": FIELDS},
                                          body=body, headers={"X-Upload-Content-Type": BACKUP_MIME,
                                                             "X-Upload-Content-Length": str(size)})
            location = headers.get("Location") or headers.get("location")
            if not isinstance(location, str):
                raise DriveError("Google did not return an upload session. Retry the same save.")
            parts = urlsplit(location)
            if (parts.scheme != "https" or parts.netloc != "www.googleapis.com"
                    or parts.path != "/upload/drive/v3/files" or parts.fragment):
                raise DriveError("Google returned an unexpected upload destination.")
            attempt.upload_url = location
        while offset < size:
            check_cancel(cancel)
            end = min(offset + CHUNK_SIZE, size)
            status, headers, _ = self._request("PUT", attempt.upload_url, cancel, data=attempt.raw[offset:end],
                                              headers={"Content-Type": BACKUP_MIME,
                                                       "Content-Range": f"bytes {offset}-{end - 1}/{size}"}, accepted=(200, 201, 308))
            if status in (200, 201):
                if end != size:
                    raise DriveError("Google completed an incomplete transfer. Retry to check the copy.")
                return
            next_offset = self._offset(headers, size)
            if not offset < next_offset <= end:
                raise DriveError("Google returned an invalid upload offset. Retry the same save.")
            offset = next_offset
        raise DriveError("Google did not confirm the final upload chunk. Retry to check the copy.")

    @staticmethod
    def _offset(headers: dict, size: int) -> int:
        value = headers.get("Range") or headers.get("range")
        if value is None:
            return 0
        match = re.fullmatch(r"bytes=0-(\d+)", value)
        if match is None or not 0 < int(match[1]) + 1 <= size:
            raise DriveError("Google returned an invalid upload offset. Retry the same save.")
        return int(match[1]) + 1
