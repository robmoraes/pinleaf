"""Explicit desktop authorization. Importing this module never contacts Google."""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import time
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Event
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlsplit

from pinleaf.config import resource_path
from pinleaf.storage.atomic_files import check_cancel

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
AUTH_URI = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URI = "https://oauth2.googleapis.com/token"

if TYPE_CHECKING:
    from google.oauth2.credentials import Credentials


class DriveAuthError(Exception):
    """Safe to display; never contains provider responses or credentials."""


class CredentialStoreError(DriveAuthError):
    pass


def credential_json(credentials: Credentials) -> str:
    """Google Auth 1.5 (Ubuntu 24.04) predates Credentials.to_json()."""
    serialize = getattr(credentials, "to_json", None)
    if callable(serialize):
        return serialize()
    # The SDK's from_authorized_user_info consumes this documented refresh
    # material. Old SDKs refresh explicitly on Connect; no token file is used.
    return json.dumps({"refresh_token": credentials.refresh_token,
                       "token_uri": credentials.token_uri,
                       "client_id": credentials.client_id,
                       "client_secret": credentials.client_secret,
                       "scopes": list(credentials.scopes)})


def client_configuration() -> dict:
    """A development override is explicit; never scan arbitrary JSON files."""
    path = Path(os.environ.get("PINLEAF_GOOGLE_CLIENT_FILE", "")) if os.environ.get("PINLEAF_GOOGLE_CLIENT_FILE") else resource_path("resources", "google-client.json")
    try:
        with path.open("rb") as source:
            raw = source.read(65537)
        value = json.loads(raw) if len(raw) <= 65536 else None
        installed = value["installed"]
        if (not isinstance(installed, dict)
                or not isinstance(installed.get("client_id"), str)
                or not installed["client_id"].endswith(".apps.googleusercontent.com")
                or not isinstance(installed.get("client_secret"), str)
                or installed.get("auth_uri") != AUTH_URI
                or installed.get("token_uri") != TOKEN_URI):
            raise ValueError()
        return {"installed": {key: installed[key] for key in ("client_id", "client_secret", "auth_uri", "token_uri")}}
    except (OSError, ValueError, KeyError, TypeError):
        raise DriveAuthError("Google Drive client configuration is unavailable or invalid.") from None


def authorize(config: dict, cancel: Event, *, timeout: float = 180,
              opener=None, flow_factory=None) -> object:
    """Bounded loopback flow with explicit PKCE and state, without token logging."""
    check_cancel(cancel)
    try:
        if flow_factory is None:
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow_factory = InstalledAppFlow.from_client_config
        flow = flow_factory(config, [DRIVE_SCOPE], code_verifier=secrets.token_urlsafe(64))
        state = secrets.token_urlsafe(32)
        result: dict[str, str] = {}

        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *_args) -> None:
                pass

            def do_GET(self) -> None:
                parsed = urlsplit(self.path)
                values = parse_qs(parsed.query)
                valid = (len(self.path) <= 8192 and parsed.path == "/oauth2callback"
                         and values.get("state") == [state]
                         and ((len(values.get("code", [])) == 1 and "error" not in values)
                              or (len(values.get("error", [])) == 1 and "code" not in values)))
                self.send_response(200 if valid else 400)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(b"Return to Pinleaf to check the connection." if valid else b"Invalid authorization response.")
                if valid:
                    result.update({key: values[key][0] for key in ("code", "error") if key in values})

        class Listener(HTTPServer):
            def get_request(self):
                connection, address = super().get_request()
                connection.settimeout(0.25)
                return connection, address

        with Listener(("127.0.0.1", 0), Callback) as server:
            server.timeout = 0.2
            flow.redirect_uri = f"http://127.0.0.1:{server.server_port}/oauth2callback"
            url, _ = flow.authorization_url(state=state, access_type="offline", prompt="consent", code_challenge_method="S256")
            if not (opener or webbrowser.open)(url):
                raise DriveAuthError("Could not open the browser. Check your default browser and retry.")
            deadline = time.monotonic() + timeout
            while not result:
                check_cancel(cancel)
                if time.monotonic() >= deadline:
                    raise DriveAuthError("Google authorization timed out. Connect again to retry.")
                server.handle_request()
        check_cancel(cancel)
        if "error" in result:
            raise DriveAuthError("Google authorization was declined. Your notes were kept locally.")
        flow.fetch_token(code=result["code"], timeout=(10, 30))
        check_cancel(cancel)
        scopes = flow.oauth2session.token.get("scope", [])
        scopes = scopes.split() if isinstance(scopes, str) else scopes
        if set(scopes) != {DRIVE_SCOPE}:
            raise DriveAuthError("Google did not grant the expected backup permission. Connect again.")
        credentials = flow.credentials
        if not credentials.refresh_token:
            raise DriveAuthError("Google did not provide offline access. Connect again.")
        return credentials
    except (DriveAuthError,):
        raise
    except Exception as exc:
        from pinleaf.storage.atomic_files import OperationCancelled
        if isinstance(exc, OperationCancelled):
            raise
        raise DriveAuthError("Google authorization failed. Check your connection and retry.") from None


class SecretCredentials:
    """Only Secret Service; unavailable or locked storage never falls back to disk."""
    def __init__(self, installation: str) -> None:
        self.installation = installation

    def _open(self):
        import secretstorage
        bus = secretstorage.dbus_init()
        try:
            collection = secretstorage.get_default_collection(bus)
            if collection.is_locked():
                raise CredentialStoreError("Unlock your system keyring or choose connection for this session only.")
            return bus, collection
        except Exception:
            bus.close()
            raise

    def _attributes(self, client_id: str) -> dict[str, str]:
        return {"application": "dev.pinleaf.Pinleaf", "client": client_id, "installation": self.installation}

    def load(self, client_id: str) -> dict | None:
        bus = None
        try:
            bus, collection = self._open()
            items = list(collection.search_items(self._attributes(client_id)))
            if not items:
                return None
            if len(items) != 1 or items[0].is_locked():
                raise ValueError()
            raw = items[0].get_secret()
            if len(raw) > 65536:
                raise ValueError()
            return json.loads(raw)
        except Exception:
            raise CredentialStoreError("Saved Google access is unavailable. Unlock your keyring or choose session-only access.") from None
        finally:
            if bus is not None:
                bus.close()

    def save(self, client_id: str, account: str, value: str) -> None:
        bus = None
        try:
            bus, collection = self._open()
            attributes = self._attributes(client_id) | {"account": account}
            collection.create_item("Pinleaf Google Drive", attributes, value.encode(), replace=True)
        except Exception:
            raise CredentialStoreError("Could not save Google access in the system keyring. Choose session-only access to continue.") from None
        finally:
            if bus is not None:
                bus.close()

    def delete(self, client_id: str) -> None:
        bus = None
        try:
            bus, collection = self._open()
            for item in collection.search_items(self._attributes(client_id)):
                if item.is_locked():
                    raise ValueError()
                item.delete()
        except Exception:
            raise CredentialStoreError("Could not forget saved Google access. Unlock your keyring and retry Disconnect.") from None
        finally:
            if bus is not None:
                bus.close()


@dataclass(frozen=True)
class DriveConnection:
    account: str
    session_only: bool


class DriveAuth:
    def __init__(self, data_dir: Path, *, store=None, authorizer=authorize, identify=None) -> None:
        installation = hashlib.sha256(str(data_dir.resolve()).encode()).hexdigest()
        self.store = store if store is not None else SecretCredentials(installation)
        self.authorizer = authorizer
        self.identify = identify or self._identify
        self.credentials = None
        self.connection: DriveConnection | None = None
        self.client_id: str | None = None
        self.persisted = False
        self.account_id: str | None = None

    @staticmethod
    def _identify(credentials) -> tuple[str, str]:
        import requests
        # A deliberate operation only. This call cannot refresh or follow redirects.
        with requests.get("https://www.googleapis.com/drive/v3/about",
                          params={"fields": "user(permissionId,emailAddress)"},
                          headers={"Authorization": f"Bearer {credentials.token}"},
                          timeout=(10, 30), allow_redirects=False, stream=True) as response:
            if response.status_code != 200:
                raise DriveAuthError("Could not confirm Google Drive access. Reconnect and retry.")
            raw = bytearray()
            for chunk in response.iter_content(4096):
                raw.extend(chunk)
                if len(raw) > 65536:
                    raise DriveAuthError("Google returned an invalid account response.")
            user = json.loads(raw)["user"]
            account, email = user["permissionId"], user["emailAddress"]
            if not all(isinstance(value, str) and 0 < len(value) <= 320 for value in (account, email)):
                raise DriveAuthError("Google returned an invalid account response.")
            return account, email

    def connect(self, cancel: Event, *, session_only: bool = False) -> DriveConnection:
        check_cancel(cancel)
        config = client_configuration()
        client_id = config["installed"]["client_id"]
        try:
            credentials = None
            saved = None
            if not session_only:
                saved = self.store.load(client_id)
                if saved is not None:
                    from google.oauth2.credentials import Credentials
                    if (saved.get("client_id") != client_id or saved.get("token_uri") != TOKEN_URI
                            or set(saved.get("scopes", [])) != {DRIVE_SCOPE}):
                        raise DriveAuthError("Saved Google access is invalid. Disconnect and reconnect.")
                    credentials = Credentials.from_authorized_user_info(saved, scopes=[DRIVE_SCOPE])
                    if not credentials.valid:
                        from google.auth.transport.requests import Request
                        credentials.refresh(lambda *args, **kwargs: Request()(*args, **(kwargs | {"timeout": 30})))
            if credentials is None:
                credentials = self.authorizer(config, cancel)
            check_cancel(cancel)
            account, email = self.identify(credentials)
            check_cancel(cancel)
            if not session_only:
                self.store.save(client_id, account, credential_json(credentials))
                if cancel.is_set():
                    if saved is None:
                        self.store.delete(client_id)
                    else:
                        self.store.save(client_id, account, json.dumps(saved))
                    check_cancel(cancel)
            self.credentials, self.client_id = credentials, client_id
            self.account_id = account
            self.persisted = not session_only
            self.connection = DriveConnection(email, session_only)
            return self.connection
        except DriveAuthError:
            raise
        except Exception as exc:
            from pinleaf.storage.atomic_files import OperationCancelled
            if isinstance(exc, OperationCancelled):
                raise
            raise DriveAuthError("Could not connect Google Drive. Check your connection or reconnect after Disconnect.") from None

    def access_token(self, cancel: Event) -> str:
        """Refresh only within a user-requested Drive operation."""
        check_cancel(cancel)
        credentials = self.credentials
        if credentials is None or self.connection is None:
            raise DriveAuthError("Connect Google Drive before using remote backups.")
        try:
            if not credentials.valid:
                from google.auth.transport.requests import Request
                credentials.refresh(lambda *args, **kwargs: Request()(*args, **(kwargs | {"timeout": 30})))
                check_cancel(cancel)
                if self.persisted:
                    self.store.save(self.client_id, self.account_id, credential_json(credentials))
            check_cancel(cancel)
            if not isinstance(credentials.token, str) or not credentials.token:
                raise DriveAuthError("Google access is unavailable. Disconnect and reconnect.")
            return credentials.token
        except (DriveAuthError,):
            raise
        except Exception as exc:
            from pinleaf.storage.atomic_files import OperationCancelled
            if isinstance(exc, OperationCancelled):
                raise
            raise DriveAuthError("Google access expired or was revoked. Disconnect and reconnect.") from None

    def disconnect(self, cancel: Event) -> None:
        check_cancel(cancel)
        client_id = self.client_id or client_configuration()["installed"]["client_id"]
        # Clear memory even if the keyring is locked; report deletion failure truthfully.
        self.credentials = None
        self.connection = None
        self.account_id = None
        if self.persisted or self.client_id is None:
            self.store.delete(client_id)
        self.persisted = False
        self.client_id = None
