"""The fallback, signature handoff and budget use offline fixtures only."""
import json
import io
from unittest.mock import MagicMock
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from direct_chat import configured_miners
from flop_chat import Chat, ChatError, identity, parse_identity
from test_chat import FakeGateway, IDENTITY, KEY, MODEL, NOW, receipt

MINER = {"name": "Offline miner", "address": identity(bytes(range(32)))["address"], "endpoint": "https://miner.example.org"}
REQUEST = "chat-" + "a" * 32
CHANNEL = "0x" + "b" * 64
TX = "0x" + "c" * 64


class DirectTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / "ledger.json"
        self.gateway = FakeGateway()
        self.chat = Chat(self.path, self.gateway, expected_did=IDENTITY["did"], clock=lambda: NOW)
        self.direct = self.chat.direct
        self.direct.available = True
        self.assertEqual(self.direct.miners, [])
        self.direct.miners = [MINER]
        self.body = {"request_id": REQUEST, "model": MODEL, "messages": [{"role": "user", "content": "Fixture"}]}
        self.choice = {"request_id": REQUEST, "miner": MINER["address"]}
        self.sign()

    def sign(self):
        challenge = self.chat.new_challenge({"address": IDENTITY["address"]})
        self.chat.enroll({"signature": "0x" + KEY.sign(challenge["message"].encode()).hex()})

    def paid_calls(self):
        return [call for call in self.gateway.calls if call[0] == "/chat/completions"]

    def test_only_explicit_https_miners_are_available(self):
        path = self.path.with_name("direct-miners.json")
        rows = [{**MINER, "endpoint": url} for url in ("http://miner.example.org", "https://127.0.0.1", "https://x.local", "https://[::1]", "https://user@miner.example.org")]
        path.write_text(json.dumps(rows))
        self.assertEqual(configured_miners(path, parse_identity, ChatError), [])
        path.write_text(json.dumps(rows + [MINER, MINER]))
        self.assertEqual(configured_miners(path, parse_identity, ChatError), [MINER])

    def test_manual_direct_quote_uses_requested_escrow_and_token_cap(self):
        body = {**self.body, "route":"direct", "max_tokens":1024}
        self.assertTrue(self.chat.chat(body)["direct_offer"])
        with patch("direct_chat.threading.Thread") as worker:
            self.direct.prepare({**self.choice, "escrow":"0.072"})
        params = worker.call_args.kwargs["args"][1]
        self.assertEqual((params["escrow"], params["duration"], params["maxTokens"]),
                         ("72000000000000000", 1200, 1024))
        self.assertEqual(self.paid_calls(), [])

    def test_bad_direct_slug_does_not_fall_through_to_gateway(self):
        with self.assertRaisesRegex(ChatError, "DIRECT_NOT_ALLOWED"):
            self.chat.chat({**self.body, "route":"direct", "model":MODEL.upper()})
        self.assertEqual(self.paid_calls(), [])

    def test_gateway_success_does_not_offer_direct(self):
        result = self.chat.chat(self.body)
        self.assertTrue(result["completion"]["text"])
        self.assertIsNone(result["state"]["direct"]["request_id"])
        with self.assertRaisesRegex(ChatError, "DIRECT_NOT_ALLOWED"):
            self.direct.prepare(self.choice)

    def test_429_with_released_receipt_offers_same_message_only(self):
        self.gateway.mode = "429"
        result = self.chat.chat(self.body)
        self.assertEqual(result["state"]["direct"]["request_id"], REQUEST)
        self.assertEqual(len(self.paid_calls()), 1)
        with self.assertRaisesRegex(ChatError, "DIRECT_NOT_ALLOWED"):
            self.direct.prepare({**self.choice, "request_id": "chat-" + "e" * 32})
        with self.assertRaisesRegex(ChatError, "DIRECT_MINER_INVALID"):
            self.direct.prepare({**self.choice, "miner": IDENTITY["address"]})
        with patch("direct_chat.threading.Thread") as worker:
            snapshot = self.direct.prepare(self.choice)
            worker.return_value.start.assert_called_once()
            self.assertEqual(worker.call_args.kwargs["args"][1]["messages"], self.body["messages"])
        self.assertEqual(snapshot["direct"]["job"]["phase"], "checking")
        self.assertNotIn("Fixture", json.dumps(snapshot))

    def test_runtime_rejection_stops_before_signature_and_redacts_raw_errors(self):
        self.chat.auth["expires_at"] = NOW * 1000
        self.chat.chat(self.body)
        with patch("direct_chat.threading.Thread"):
            self.direct.prepare(self.choice)
        process = MagicMock()
        process.stdout = io.StringIO(json.dumps({"phase": "not_submitted",
            "error_code": "DIRECT_RUNTIME_UNSUPPORTED", "runtime": 1014015,
            "message": "private RPC details"}) + "\n")
        process.poll.return_value = 0
        with patch.object(self.direct, "start_process", return_value=process):
            self.direct.run(self.direct.job, {"fixture": True})
        job = self.direct.snapshot()["job"]
        self.assertEqual(job["phase"], "stopped")
        self.assertEqual(job["error_code"], "DIRECT_RUNTIME_UNSUPPORTED")
        self.assertEqual(job["runtime"], 1014015)
        self.assertNotIn("private RPC", json.dumps(job))
        self.assertNotIn("payload", job)
        self.assertNotIn(self.direct.job["id"], self.chat.ledger.rows)
        self.assertEqual(self.paid_calls(), [])

    def test_timeout_and_nonterminal_receipt_block_fallback(self):
        self.gateway.mode = "timeout"
        self.gateway.receipts[REQUEST] = receipt(REQUEST, "reserved", 429)
        result = self.chat.chat(self.body)
        self.assertIn(REQUEST, result["state"]["unresolved"])
        self.assertIsNone(result["state"]["direct"]["request_id"])
        with self.assertRaisesRegex(ChatError, "DIRECT_NOT_ALLOWED"):
            self.direct.prepare(self.choice)

    def test_expired_gateway_does_not_submit_or_bypass_external_receipt(self):
        self.chat.auth["expires_at"] = NOW * 1000
        self.assertEqual(self.chat.chat(self.body)["state"]["direct"]["request_id"], REQUEST)
        self.assertEqual(self.paid_calls(), [])
        self.chat.reconcile_request = "chat-" + "f" * 32
        self.assertIsNone(self.chat.snapshot()["direct"]["request_id"])
        with self.assertRaisesRegex(ChatError, "DIRECT_NOT_ALLOWED"):
            self.direct.prepare(self.choice)

    def test_offline_gateway_login_uses_separate_signed_challenge(self):
        original = self.gateway.request

        def unavailable(path, *args):
            if path.startswith("/enroll/wallet/challenge?"):
                raise ChatError("GATEWAY_UNREACHABLE", 502)
            return original(path, *args)

        with patch.object(self.gateway, "request", side_effect=unavailable):
            self.chat.disconnect()
            self.sign()
        self.assertEqual(self.chat.account, IDENTITY)
        self.assertFalse(self.chat.connected())
        self.assertEqual(self.chat.chat(self.body)["state"]["direct"]["request_id"], REQUEST)
        self.assertEqual(self.paid_calls(), [])

    def test_enrollment_expiry_offers_direct_after_same_wallet_login(self):
        original = self.gateway.request

        def expired(path, *args):
            if path == "/enroll/wallet":
                raise ChatError("devnet_enrollment_expired", 403, "This devnet allowance expired.")
            return original(path, *args)

        self.chat.disconnect()
        with patch.object(self.gateway, "request", side_effect=expired):
            self.sign()

        self.assertEqual(self.chat.account, IDENTITY)
        self.assertEqual(self.chat.snapshot()["gateway_block"], "devnet_enrollment_expired")
        self.assertFalse(self.chat.connected())
        self.assertIsNone(self.chat.key)
        self.assertEqual(self.chat.chat(self.body)["state"]["direct"]["request_id"], REQUEST)
        self.assertEqual(self.paid_calls(), [])

    def test_durable_intent_precedes_signature_handoff_and_blocks_replay(self):
        self.gateway.mode = "429"
        self.chat.chat(self.body)
        with patch("direct_chat.threading.Thread"):
            self.direct.prepare(self.choice)
        job = self.direct.job
        job.update(phase="review", payload={"fixture": "public"}, preview={"expires_at": 4e12,
                   "channel_id": CHANNEL, "scan_from": 42, "max_tokens": 48, "fee": "5000000000000000"})
        self.assertEqual(self.direct.sign({"id": job["id"]})["payload"], {"fixture": "public"})
        self.assertFalse(any(r.get("route") == "direct" for r in self.chat.ledger.rows.values()))
        signature = "0x" + "12" * 64

        def write(line):
            journal = json.loads(self.path.read_text(encoding="utf-8"))
            row = journal["requests"][job["id"]]
            self.assertEqual(row["channel_id"], CHANNEL)
            self.assertEqual(row["state"], "unknown")
            self.assertNotIn(signature, json.dumps(journal))
            self.assertEqual(json.loads(line)["signature"], signature)

        job["process"] = SimpleNamespace(stdin=SimpleNamespace(write=write, flush=lambda: None))
        snapshot = self.direct.submit({"id": job["id"], "signature": signature})
        self.assertIn(job["id"], snapshot["unresolved"])
        self.assertIsNone(snapshot["direct"]["request_id"])
        self.assertNotIn(signature, json.dumps(snapshot))
        with self.assertRaisesRegex(ChatError, "DIRECT_PREVIEW_EXPIRED"):
            self.direct.submit({"id": job["id"], "signature": signature})
        job["phase"] = "reconcile"
        self.direct.apply_final(job["row"], {"phase": "settled", "tx": TX,
                                            "miner_paid_raw": "48000000000000000",
                                            "aggregate_gn": "27", "burned_raw": "2000000000000000"})
        self.assertEqual(self.chat.ledger.rows[job["id"]]["terminal_event"], TX)
        self.assertEqual(str(self.chat.session_commitment()), "0.07")
        self.assertIsNone(self.chat.snapshot()["direct"]["request_id"])
