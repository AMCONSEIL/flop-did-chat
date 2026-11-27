"""Offline acceptance tests. Public RFC8032 fixture only; no wallet/network access."""
import copy
from decimal import Decimal
import hashlib
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from flop_chat import (Chat, ChatError, GENESIS, Gateway, Ledger, b58encode,
                       identity, make_handler, parse_identity, verify_signature)

SEED = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
KEY = Ed25519PrivateKey.from_private_bytes(SEED)
IDENTITY = identity(KEY.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw))
MODEL = "qwen/qwen3-8b"
NOW = 1_800_000_000
SECRET = "fixture-bearer-never-in-browser"

def model(name=MODEL):
    return {"id": name, "name": name, "top_provider": {"max_completion_tokens": 8192},
            "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
            "supported_parameters": ["max_tokens"]}

def receipt(request_id, state="settled", status=200):
    return {"request_id": request_id, "correlation_id": request_id, "model": MODEL,
            "reserved_spend": 0.39, "settled_spend": 0.25 if state == "settled" else None,
            "settled_spend_raw": "250000000000000000" if state == "settled" else None,
            "terminal_event": "pooled-event" if state == "settled" else None,
            "channel_id": "channel-test" if state == "settled" else None,
            "created_at": NOW * 1000, "state": state, "response_status": status}

class FakeGateway:
    def __init__(self):
        self.calls = []
        self.receipts = {}
        self.mode = "success"
        self.on_chat = None
        self.catalog = [model(), model("other/not-allowed")]
        self.quota = 20_000
        self.read_error = False
        self.challenge_message = "\n".join([
            "FLOP wallet connection", "Action: flop-testnet-enroll/v1", "Domain: https://gateway.testnet.flop.network",
            "Genesis: " + GENESIS, "Address: " + IDENTITY["address"], "Nonce: " + "1" * 64,
            "Issued At: " + str(NOW * 1000), "Expires At: " + str((NOW + 300) * 1000)])

    def request(self, path, payload=None, key=None, request_id=None):
        self.calls.append((path, copy.deepcopy(payload), key, request_id))
        if path == "/models":
            return {"data": copy.deepcopy(self.catalog)}, {}
        if path.startswith("/enroll/wallet/challenge?"):
            return {"message": self.challenge_message, "nonce": "1" * 64, "expires_at": (NOW + 300) * 1000}, {}
        if path == "/enroll/wallet":
            return {"key": SECRET, "model": MODEL, "remaining_quota": self.quota, "expires_at": (NOW + 3600) * 1000}, {}
        if path == "/keys/me":
            if self.read_error:
                raise ChatError("GATEWAY_UNREACHABLE", 502)
            return {"remaining_quota": self.quota, "expires_at": (NOW + 86400) * 1000}, {}
        if path == "/keys/me/receipts":
            return {"receipts": list(self.receipts.values())}, {}
        if path.startswith("/keys/me/receipts/"):
            ident = path.rsplit("/", 1)[-1]
            if ident not in self.receipts:
                raise ChatError("receipt_not_found", 404)
            return self.receipts[ident], {}
        if path == "/chat/completions":
            if self.on_chat:
                self.on_chat(request_id)
            if self.mode == "timeout":
                raise ChatError("GATEWAY_UNREACHABLE", 502)
            if self.mode == "429":
                self.receipts[request_id] = receipt(request_id, "released", 429)
                raise ChatError("overloaded", 429, "gateway channel pool is full", 1)
            self.receipts[request_id] = receipt(request_id, "estimated" if self.mode == "pending" else "settled")
            return {"choices": [{"message": {"content": "A devnet is a test network."}, "finish_reason": "stop"}],
                    "model": MODEL, "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}}, {}
        raise AssertionError(path)

class ChatTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ledger.json"
        self.gateway = FakeGateway()
        self.chat = Chat(self.path, self.gateway, expected_did=IDENTITY["did"], clock=lambda: NOW)

    def connect(self, wrapped=False):
        self.chat.new_challenge({"address": IDENTITY["address"], "did": IDENTITY["did"]})
        message = self.gateway.challenge_message.encode()
        if wrapped:
            message = b"<Bytes>" + message + b"</Bytes>"
        signature = "0x" + KEY.sign(message).hex()
        return self.chat.enroll({"signature": signature})

    def body(self, suffix="a"):
        return {"request_id": "chat-" + suffix * 32, "model": MODEL,
                "messages": [{"role": "user", "content": "Hello fixture"}], "max_tokens": 48, "max_cost_flop": "0.9"}

    def assertCode(self, code, fn):
        with self.assertRaises(ChatError) as error:
            fn()
        self.assertEqual(error.exception.code, code)

    def count_paid(self):
        return len([c for c in self.gateway.calls if c[0] == "/chat/completions"])

    def test_public_rfc_identity_and_ss58(self):
        self.assertEqual(parse_identity(IDENTITY["address"], IDENTITY["did"]), IDENTITY)
        public = bytes.fromhex(IDENTITY["public_key"][2:])
        prefix = b"\x00"
        payload = prefix + public
        other = b58encode(payload + hashlib.blake2b(b"SS58PRE" + payload, digest_size=64).digest()[:2])
        self.assertEqual(parse_identity(other), IDENTITY)

    def test_did_and_checksum_mismatch(self):
        self.assertCode("DID_MISMATCH", lambda: parse_identity(IDENTITY["address"], "did:key:z6MkWrong"))
        altered = IDENTITY["address"][:-1] + ("1" if IDENTITY["address"][-1] != "1" else "2")
        self.assertCode("IDENTITY_INVALID", lambda: parse_identity(altered))

    def test_signature_raw_and_talisman_bytes_wrapper(self):
        self.assertTrue(self.connect(wrapped=True)["connected"])
        self.assertNotIn(SECRET, json.dumps(self.chat.snapshot()))
        self.assertEqual(self.chat.auth["expires_at"], (NOW + 3600) * 1000)

    def test_signature_wrong_key_rejected_before_enrollment(self):
        self.chat.new_challenge({"address": IDENTITY["address"]})
        wrong = Ed25519PrivateKey.from_private_bytes(bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb"))
        self.assertCode("SIGNATURE_INVALID", lambda: self.chat.enroll({"signature": "0x" + wrong.sign(self.gateway.challenge_message.encode()).hex()}))
        self.assertFalse(any(c[0] == "/enroll/wallet" for c in self.gateway.calls))

    def test_sr25519_signature_type_rejected_before_enrollment(self):
        self.chat.new_challenge({"address": IDENTITY["address"]})
        signature = "0x01" + KEY.sign(self.gateway.challenge_message.encode()).hex()
        self.assertCode("ED25519_REQUIRED", lambda: self.chat.enroll({"signature": signature}))
        self.assertFalse(any(c[0] == "/enroll/wallet" for c in self.gateway.calls))

    def test_other_wallet_and_genesis_blocked(self):
        other = identity(bytes.fromhex("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c"))
        self.assertCode("EXPECTED_DID_MISMATCH", lambda: self.chat.new_challenge({"address": other["address"]}))
        self.gateway.challenge_message = self.gateway.challenge_message.replace(GENESIS, "0x" + "0" * 64)
        self.assertCode("CHALLENGE_INVALID", lambda: self.chat.new_challenge({"address": IDENTITY["address"]}))

    def test_used_challenge_not_replayed(self):
        self.connect()
        self.assertCode("CHALLENGE_EXPIRED", lambda: self.chat.enroll({"signature": "0x" + "00" * 64}))

    def test_success_two_turns_receipts_and_exact_budget(self):
        self.connect()
        first = self.chat.chat(self.body())
        self.assertEqual(first["completion"]["usage"]["total_tokens"], 18)
        self.assertEqual(first["request"]["settled_spend_raw"], "250000000000000000")
        second = self.body("b"); second["max_cost_flop"] = "0.5"
        second["messages"] = [{"role": "user", "content": "Hello fixture"}, {"role": "assistant", "content": first["completion"]["text"]}, {"role": "user", "content": "Thanks"}]
        self.chat.chat(second)
        self.assertEqual(self.count_paid(), 2)
        self.assertEqual(self.chat.session_commitment(), Decimal("0.5"))

    def test_duplicate_click_and_conflicting_payload(self):
        self.connect()
        self.chat.chat(self.body())
        self.assertTrue(self.chat.chat(self.body())["duplicate"])
        changed = self.body(); changed["messages"][0]["content"] = "Different"
        self.assertCode("REQUEST_ID_CONFLICT", lambda: self.chat.chat(changed))
        self.assertEqual(self.count_paid(), 1)

    def test_429_release_not_counted_as_spend_no_retry(self):
        self.connect(); self.gateway.mode = "429"
        result = self.chat.chat(self.body())
        self.assertEqual(result["request"]["state"], "released")
        self.assertIsNone(result["request"]["settled_spend"])
        self.assertEqual(self.chat.session_commitment(), 0)
        self.assertEqual(self.count_paid(), 1)
        self.assertCode("COOLDOWN", lambda: self.chat.chat(self.body("b")))

    def test_cooldown_survives_server_restart(self):
        self.connect(); self.gateway.mode = "429"
        self.chat.chat(self.body())
        restarted = Chat(self.path, self.gateway, clock=lambda: NOW)
        restarted.new_challenge({"address": IDENTITY["address"]})
        restarted.enroll({"signature": "0x" + KEY.sign(self.gateway.challenge_message.encode()).hex()})
        self.assertCode("COOLDOWN", lambda: restarted.chat(self.body("b")))
        self.assertEqual(self.count_paid(), 1)

    def test_timeout_404_remains_locked_after_restart(self):
        self.connect(); self.gateway.mode = "timeout"
        result = self.chat.chat(self.body())
        self.assertEqual(result["request"]["state"], "unknown")
        self.assertEqual(self.count_paid(), 1)
        restarted = Chat(self.path, self.gateway, clock=lambda: NOW)
        restarted.new_challenge({"address": IDENTITY["address"]})
        restarted.enroll({"signature": "0x" + KEY.sign(self.gateway.challenge_message.encode()).hex()})
        self.assertCode("RECONCILE_REQUIRED", lambda: restarted.chat(self.body("b")))
        self.assertEqual(self.count_paid(), 1)

    def test_pending_settlement_blocks_second_send(self):
        self.connect(); self.gateway.mode = "pending"
        self.chat.chat(self.body())
        self.assertCode("RECONCILE_REQUIRED", lambda: self.chat.chat(self.body("b")))
        self.gateway.receipts[self.body()["request_id"]] = receipt(self.body()["request_id"])
        self.chat.refresh()
        self.assertFalse(self.chat.unresolved())

    def test_session_budget_and_explicit_change(self):
        self.connect(); self.chat.chat(self.body())
        self.assertCode("SESSION_LIMIT", lambda: self.chat.chat(self.body("b")))
        self.chat.update_limits({"session_cap": "2"})
        self.assertEqual(self.chat.session_cap, 2)
        self.chat.chat(self.body("b"))
        self.assertCode("LIMIT_INVALID", lambda: self.chat.update_limits({"session_cap": "0"}))

    def test_user_chosen_caps_above_previous_hard_limits(self):
        self.connect()
        self.assertEqual(self.chat.snapshot()["limits"]["request_cap"], "0.9")
        self.assertEqual(self.chat.session_cap, Decimal("0.9"))
        snapshot = self.chat.update_limits({"request_cap": "2.5", "session_cap": "10"})
        self.assertEqual(snapshot["limits"]["request_cap"], "2.5")
        self.assertEqual(self.chat.session_cap, Decimal("10"))
        self.assertEqual(self.count_paid(), 0)
        body = self.body(); body["max_cost_flop"] = "2.5"
        self.chat.chat(body)
        paid = [call for call in self.gateway.calls if call[0] == "/chat/completions"]
        self.assertEqual(paid[0][1]["max_cost_flop"], 2.5)
        body = self.body("b"); body["max_cost_flop"] = "2.51"
        self.assertCode("LIMIT_INVALID", lambda: self.chat.chat(body))
        self.assertEqual(self.count_paid(), 1)
        self.chat.update_limits({"session_cap": "999"})
        self.assertEqual(self.chat.session_cap, Decimal("999"))

    def test_invalid_limit_settings_are_atomic_and_do_not_spend(self):
        self.connect()
        self.chat.update_limits({"request_cap": "2.5", "session_cap": "10"})
        for body, code in [({"request_cap": "Infinity", "session_cap": "20"}, "AMOUNT_INVALID"),
                           ({"request_cap": "0", "session_cap": "20"}, "LIMIT_INVALID"),
                           ({"request_cap": "1e999", "session_cap": "20"}, "LIMIT_INVALID"),
                           ({"request_cap": "1e-999", "session_cap": "20"}, "LIMIT_INVALID"),
                           ({"request_cap": "3", "session_cap": "NaN"}, "AMOUNT_INVALID"),
                           ({"request_cap": "3", "session_cap": "2"}, "REQUEST_CAP_EXCEEDS_SESSION")]:
            self.assertCode(code, lambda: self.chat.update_limits(body))
            self.assertEqual(self.chat.request_cap, Decimal("2.5"))
            self.assertEqual(self.chat.session_cap, Decimal("10"))
        self.assertEqual(self.count_paid(), 0)

    def test_limits_model_and_payload_before_network(self):
        self.connect()
        for field, value, code in [("model", "other/not-allowed", "MODEL_NOT_AUTHORIZED"),
                                    ("max_tokens", 1025, "LIMIT_INVALID"), ("max_cost_flop", "1", "LIMIT_INVALID"),
                                    ("max_cost_flop", "NaN", "AMOUNT_INVALID"),
                                    ("messages", [{"role": "tool", "content": "run"}], "MESSAGES_INVALID")]:
            body = self.body(); body[field] = value
            self.assertCode(code, lambda: self.chat.chat(body))
        self.assertEqual(self.count_paid(), 0)

    def test_large_context_and_unadvertised_token_limit(self):
        self.connect()
        body = self.body(); body["messages"] = [{"role": "user", "content": "x" * 30001}]
        self.assertCode("MESSAGES_INVALID", lambda: self.chat.chat(body))
        self.chat.models[0]["max_completion_tokens"] = 16
        self.assertCode("LIMIT_INVALID", lambda: self.chat.chat(self.body()))

    def test_introspection_failure_does_not_allow_chat(self):
        self.gateway.read_error = True
        with self.assertRaises(ChatError):
            self.connect()
        self.assertFalse(self.chat.connected())
        self.assertCode("CONNECT_REQUIRED", lambda: self.chat.chat(self.body()))
        self.assertEqual(self.count_paid(), 0)

    def test_ledger_persists_intent_before_post_without_prompt_or_key(self):
        self.connect()
        def check(_):
            text = self.path.read_text()
            self.assertIn(self.body()["request_id"], text)
            self.assertNotIn("Hello fixture", text)
            self.assertNotIn(SECRET, text)
            self.assertEqual(json.loads(text)["requests"][self.body()["request_id"]]["local_state"], "sending")
        self.gateway.on_chat = check
        self.chat.chat(self.body())

    def test_concurrent_requests_do_not_duplicate_paid_calls(self):
        self.connect()
        entered, release = threading.Event(), threading.Event()
        def pause(_): entered.set(); release.wait(timeout=5)
        self.gateway.on_chat = pause
        thread = threading.Thread(target=lambda: self.chat.chat(self.body()))
        thread.start(); self.assertTrue(entered.wait(2))
        self.assertCode("RECONCILE_REQUIRED", lambda: self.chat.chat(self.body("b")))
        release.set(); thread.join(3)
        self.assertFalse(thread.is_alive()); self.assertEqual(self.count_paid(), 1)

    def test_missing_previous_receipt_blocks_submission(self):
        self.chat.reconcile_request = "previous-personal-request"
        state = self.connect()
        self.assertIn("previous-personal-request", state["unresolved"])
        self.assertCode("RECONCILE_REQUIRED", lambda: self.chat.chat(self.body()))

    def test_terminal_unknown_settlement_never_displayed_as_zero(self):
        self.connect(); self.gateway.mode = "pending"
        self.chat.chat(self.body())
        row = receipt(self.body()["request_id"]); row["settled_spend"] = None; row["settled_spend_raw"] = None
        self.gateway.receipts[row["request_id"]] = row
        self.chat.refresh()
        self.assertEqual(self.chat.session_commitment(), Decimal("0.9"))
        self.assertIsNone(self.chat.snapshot()["requests"][0]["settled_spend"])

class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.chat = Chat(Path(self.tmp.name) / "ledger.json", FakeGateway(), clock=lambda: NOW)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.chat))
        self.server.local_host = "127.0.0.1:" + str(self.server.server_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True); self.thread.start()
        self.url = "http://" + self.server.local_host
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def request(self, path, data=None, origin=None, csrf=None, host=None):
        headers = {}
        if data is not None: headers["Content-Type"] = "application/json"
        if origin: headers["Origin"] = origin
        if csrf: headers["X-Chat-Local"] = csrf
        if host: headers["Host"] = host
        req = urllib.request.Request(self.url + path, data=None if data is None else json.dumps(data).encode(), headers=headers)
        try:
            return self.opener.open(req, timeout=5)
        except urllib.error.HTTPError as error:
            return error

    def test_local_csrf_origin_and_host_guards(self):
        self.assertEqual(self.request("/api/models", {}).status, 403)
        self.assertEqual(self.request("/api/models", {}, "https://evil.test", self.chat.bootstrap_token).status, 403)
        self.assertEqual(self.request("/api/state", host="evil.test").status, 403)
        self.assertEqual(self.request("/api/models", {}, self.url, self.chat.bootstrap_token).status, 200)
        self.assertEqual(self.chat.gateway.calls[-1][0], "/models")

    def test_only_public_assets_are_served(self):
        for path in ["/flop_chat.py", "/.local/ledger.json", "/../README.md", "/web/../flop_chat.py"]:
            self.assertEqual(self.request(path).status, 404)
        response = self.request("/")
        self.assertEqual(response.status, 200)
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])
        self.assertIn(self.chat.bootstrap_token, response.read().decode())

    def test_browser_never_receives_bearer(self):
        self.chat.account = IDENTITY
        self.chat.key = SECRET
        self.chat.auth = {"verified": True, "reconciled": True, "model": MODEL, "expires_at": (NOW + 3600) * 1000, "remaining_quota": 20000}
        self.assertNotIn(SECRET, self.request("/api/state").read().decode())

if __name__ == "__main__":
    unittest.main()
