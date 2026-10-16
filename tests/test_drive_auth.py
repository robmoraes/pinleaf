from __future__ import annotations

import json
import hashlib
import base64
import os
import tempfile
import unittest
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import urlopen
from urllib.error import HTTPError

from pinleaf.services.drive_auth import (
    AUTH_URI, TOKEN_URI, DRIVE_SCOPE, CredentialStoreError, DriveAuth,
    DriveAuthError, SecretCredentials, authorize, client_configuration,
)
from pinleaf.storage.atomic_files import OperationCancelled


CONFIG = {"installed": {"client_id": "synthetic.apps.googleusercontent.com",
                        "client_secret": "synthetic", "auth_uri": AUTH_URI, "token_uri": TOKEN_URI}}


class DriveAuthTests(unittest.TestCase):
    def test_configuration_requires_desktop_and_google_endpoints(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "client.json"
            with patch.dict(os.environ, PINLEAF_GOOGLE_CLIENT_FILE=str(path)):
                for value in ({"web": CONFIG["installed"]},
                              {"installed": CONFIG["installed"] | {"token_uri": "https://example.org/token"}},
                              {}, None):
                    path.write_text(json.dumps(value))
                    with self.assertRaises(DriveAuthError):
                        client_configuration()
                path.write_text(json.dumps(CONFIG))
                self.assertEqual(client_configuration(), CONFIG)
                path.write_text(" " * 65537)
                with self.assertRaises(DriveAuthError):
                    client_configuration()

    def _flow(self):
        flow = Mock()
        flow.oauth2session.token = {"scope": DRIVE_SCOPE}
        flow.credentials = SimpleNamespace(refresh_token="synthetic-refresh")
        flow.authorization_url.side_effect = lambda **kwargs: ("https://accounts.google.com/?" + urlencode(kwargs), kwargs["state"])
        return flow

    def _browser(self, flow, *, invalid_first=False, denied=False):
        threads = []
        def opener(url):
            state = parse_qs(urlsplit(url).query)["state"][0]
            def callback():
                if invalid_first:
                    try:
                        urlopen(flow.redirect_uri + "?" + urlencode({"state": "wrong", "code": "bad"}), timeout=3)
                    except HTTPError as error:
                        error.close()
                with urlopen(flow.redirect_uri + "?" + urlencode({"state": state, "error" if denied else "code": "access_denied" if denied else "synthetic-code"}), timeout=3) as response:
                    response.read()
            thread = Thread(target=callback)
            threads.append(thread)
            thread.start()
            return True
        self.addCleanup(lambda: [thread.join(5) for thread in threads])
        return opener

    def test_loopback_state_pkce_and_bounded_exchange(self):
        flow = self._flow()
        factory = Mock(return_value=flow)
        result = authorize(CONFIG, Event(), flow_factory=factory,
                           opener=self._browser(flow, invalid_first=True))
        self.assertIs(result, flow.credentials)
        verifier = factory.call_args.kwargs["code_verifier"]
        self.assertTrue(43 <= len(verifier) <= 128)
        self.assertEqual(flow.authorization_url.call_args.kwargs["code_challenge_method"], "S256")
        self.assertEqual(factory.call_args.args[1], [DRIVE_SCOPE])
        flow.fetch_token.assert_called_once_with(code="synthetic-code", timeout=(10, 30))
        # Listener is closed after the response.
        with self.assertRaises(Exception):
            urlopen(flow.redirect_uri, timeout=0.2)

    def test_browser_decline_timeout_and_cancel_do_not_exchange(self):
        for scenario in ("browser", "decline", "timeout", "cancel"):
            with self.subTest(scenario=scenario):
                flow = self._flow()
                cancel = Event()
                if scenario == "decline":
                    opener = self._browser(flow, denied=True)
                else:
                    def opener(_url):
                        if scenario == "cancel":
                            cancel.set()
                        return scenario != "browser"
                with self.assertRaises(OperationCancelled if scenario == "cancel" else DriveAuthError):
                    authorize(CONFIG, cancel, flow_factory=Mock(return_value=flow), opener=opener, timeout=0.01)
                flow.fetch_token.assert_not_called()

    def test_missing_or_excess_scopes_and_refresh_token_are_rejected(self):
        for scope, refresh in (("", "refresh"), (DRIVE_SCOPE + " other", "refresh"), (DRIVE_SCOPE, None)):
            with self.subTest(scope=scope, refresh=refresh):
                flow = self._flow()
                flow.oauth2session.token = {"scope": scope}
                flow.credentials.refresh_token = refresh
                with self.assertRaises(DriveAuthError):
                    authorize(CONFIG, Event(), flow_factory=Mock(return_value=flow), opener=self._browser(flow))

    def test_provider_exception_does_not_expose_tokens(self):
        flow = self._flow()
        flow.fetch_token.side_effect = RuntimeError("private-token-value")
        with self.assertRaises(DriveAuthError) as error:
            authorize(CONFIG, Event(), flow_factory=Mock(return_value=flow), opener=self._browser(flow))
        self.assertNotIn("private-token", str(error.exception))

    def test_real_flow_generates_s256_challenge_without_network(self):
        from google_auth_oauthlib.flow import InstalledAppFlow
        captured = {}
        cancel = Event()
        def factory(*args, **kwargs):
            captured["verifier"] = kwargs["code_verifier"]
            return InstalledAppFlow.from_client_config(*args, **kwargs)
        def opener(url):
            captured["query"] = parse_qs(urlsplit(url).query)
            cancel.set()
            return True
        with self.assertRaises(OperationCancelled):
            authorize(CONFIG, cancel, flow_factory=factory, opener=opener)
        expected = base64.urlsafe_b64encode(hashlib.sha256(captured["verifier"].encode()).digest()).decode().rstrip("=")
        self.assertEqual(captured["query"]["code_challenge"], [expected])
        self.assertEqual(captured["query"]["code_challenge_method"], ["S256"])
        self.assertEqual(captured["query"]["scope"], [DRIVE_SCOPE])

    def _service(self):
        store = Mock()
        store.load.return_value = None
        credentials = Mock()
        credentials.to_json.return_value = '{"token":"synthetic"}'
        auth = DriveAuth(Path("/tmp/synthetic-installation"), store=store,
                         authorizer=Mock(return_value=credentials),
                         identify=Mock(return_value=("account-id", "test@example.org")))
        return auth, store, credentials

    @patch("pinleaf.services.drive_auth.client_configuration", return_value=CONFIG)
    def test_session_only_never_reads_or_writes_keyring(self, _config):
        auth, store, credentials = self._service()
        result = auth.connect(Event(), session_only=True)
        self.assertTrue(result.session_only)
        self.assertIs(auth.credentials, credentials)
        self.assertEqual(store.mock_calls, [])
        auth.disconnect(Event())
        self.assertIsNone(auth.credentials)
        self.assertEqual(store.mock_calls, [])

    @patch("pinleaf.services.drive_auth.client_configuration", return_value=CONFIG)
    def test_saved_access_disconnect_is_installation_local(self, _config):
        auth, store, credentials = self._service()
        result = auth.connect(Event())
        self.assertFalse(result.session_only)
        store.save.assert_called_once_with(CONFIG["installed"]["client_id"], "account-id", credentials.to_json())
        auth.disconnect(Event())
        store.delete.assert_called_once_with(CONFIG["installed"]["client_id"])
        self.assertIsNone(auth.connection)
        credentials.revoke.assert_not_called()

    @patch("pinleaf.services.drive_auth.client_configuration", return_value=CONFIG)
    def test_locked_keyring_does_not_silently_authorize_session(self, _config):
        auth, store, _ = self._service()
        store.load.side_effect = CredentialStoreError("Locked")
        with self.assertRaises(CredentialStoreError):
            auth.connect(Event())
        auth.authorizer.assert_not_called()
        self.assertIsNone(auth.credentials)

    @patch("pinleaf.services.drive_auth.client_configuration", return_value=CONFIG)
    def test_restart_loads_saved_credentials_only_on_explicit_connect(self, _config):
        auth, store, credentials = self._service()
        store.load.return_value = {"client_id": CONFIG["installed"]["client_id"], "token_uri": TOKEN_URI, "scopes": [DRIVE_SCOPE]}
        credentials.valid = True
        with patch("google.oauth2.credentials.Credentials.from_authorized_user_info", return_value=credentials):
            auth.connect(Event())
        auth.authorizer.assert_not_called()
        auth.identify.assert_called_once_with(credentials)
        store.save.assert_called_once()

    @patch("pinleaf.services.drive_auth.client_configuration", return_value=CONFIG)
    def test_expired_saved_access_refreshes_with_timeout(self, _config):
        auth, store, credentials = self._service()
        store.load.return_value = {"client_id": CONFIG["installed"]["client_id"], "token_uri": TOKEN_URI, "scopes": [DRIVE_SCOPE]}
        credentials.valid = False
        credentials.refresh.side_effect = lambda request: request("https://oauth2.googleapis.com/token", timeout=999)
        with patch("google.oauth2.credentials.Credentials.from_authorized_user_info", return_value=credentials), patch("google.auth.transport.requests.Request") as request:
            auth.connect(Event())
        self.assertEqual(request.return_value.call_args.kwargs["timeout"], 30)
        auth.authorizer.assert_not_called()

    @patch("pinleaf.services.drive_auth.client_configuration", return_value=CONFIG)
    def test_revoked_saved_access_requires_reconnect_without_browser_fallback(self, _config):
        auth, store, credentials = self._service()
        store.load.return_value = {"client_id": CONFIG["installed"]["client_id"], "token_uri": TOKEN_URI, "scopes": [DRIVE_SCOPE]}
        credentials.valid = False
        credentials.refresh.side_effect = RuntimeError("private-refresh-token")
        with patch("google.oauth2.credentials.Credentials.from_authorized_user_info", return_value=credentials):
            with self.assertRaises(DriveAuthError) as error:
                auth.connect(Event())
        self.assertNotIn("private-refresh-token", str(error.exception))
        auth.authorizer.assert_not_called()
        store.save.assert_not_called()

    @patch("pinleaf.services.drive_auth.client_configuration", return_value=CONFIG)
    def test_cancel_before_and_during_save_keeps_connection_absent(self, _config):
        for during_save in (False, True):
            auth, store, _ = self._service()
            cancel = Event()
            if during_save:
                store.save.side_effect = lambda *_: cancel.set()
            else:
                auth.identify.side_effect = lambda _: (cancel.set() or "account-id", "test@example.org")
            with self.assertRaises(OperationCancelled):
                auth.connect(cancel)
            self.assertIsNone(auth.credentials)
            if during_save:
                store.delete.assert_called_once()
            else:
                store.save.assert_not_called()

    def test_store_keys_separate_installations_and_clients(self):
        one = DriveAuth(Path("/tmp/install-one"))
        two = DriveAuth(Path("/tmp/install-two"))
        self.assertNotEqual(one.store._attributes("client"), two.store._attributes("client"))
        self.assertNotEqual(one.store._attributes("a"), one.store._attributes("b"))

    def test_secret_service_failure_has_no_plaintext_fallback(self):
        store = SecretCredentials("synthetic")
        with patch.object(store, "_open", side_effect=RuntimeError("private data")):
            for action in (lambda: store.load("client"), lambda: store.save("client", "account", "secret"), lambda: store.delete("client")):
                with self.assertRaises(CredentialStoreError) as error:
                    action()
                self.assertNotIn("private data", str(error.exception))

    def test_constructor_does_not_load_configuration_or_credentials(self):
        with patch("pinleaf.services.drive_auth.client_configuration") as config:
            store = Mock()
            DriveAuth(Path("/tmp/synthetic"), store=store)
            config.assert_not_called()
            self.assertEqual(store.mock_calls, [])

    def test_account_lookup_has_bounded_response_and_no_redirects(self):
        credentials = SimpleNamespace(token="synthetic")
        response = Mock(status_code=200)
        response.iter_content.return_value = [b'{"user":{"permissionId":"id","emailAddress":"test@example.org"}}']
        with patch("requests.get") as get:
            get.return_value.__enter__.return_value = response
            self.assertEqual(DriveAuth._identify(credentials), ("id", "test@example.org"))
            self.assertEqual(get.call_args.kwargs["timeout"], (10, 30))
            self.assertFalse(get.call_args.kwargs["allow_redirects"])
            response.iter_content.return_value = [b"x" * 65537]
            with self.assertRaises(DriveAuthError):
                DriveAuth._identify(credentials)
