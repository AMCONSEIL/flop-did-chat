"""Public RFC8032 fixture. No external requests."""
import json
import tempfile
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from faucet import CLAIM, FAUCET, Faucet
from flop_chat import Chat, ChatError, GENESIS, identity, verify_signature
from test_chat import FakeGateway, IDENTITY, KEY, NOW


class FaucetTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.path = Path(tmp.name) / "faucet-testnet.json"
        self.f = Faucet(self.path, GENESIS, ChatError, verify_signature)
        self.f.request = self.request
        self.open = True
        self.posts = []
        self.reply = (200, {"success": True, "amount": 10, "txHash": "0x" + "aa"*32, "status": "included"})

    def request(self, url, payload=None):
        if url.endswith("/chain"):
            return 200, {"genesisHash": GENESIS, "network": "testnet"}
        if url.endswith("/limits"):
            return 200, {"network":"testnet", "stale":False, "faucet":{
                "status":"open" if self.open else "daily_cap_reached",
                "agent":{"claimPath":CLAIM, "grantFlop":10,"rolloverRequiresSpend":True},
                "dailyCap":{"remainingFlop":100 if self.open else 0}}}
        self.assertEqual(url, FAUCET + CLAIM)
        self.assertEqual(self.f.records()[payload["address"]]["status"], "unknown")
        self.posts.append(payload)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply

    def signed(self):
        c = self.f.prepare(IDENTITY, {})
        canonical = "|".join(("flop-faucet-agent/v1", GENESIS, IDENTITY["address"], c["nonce"]))
        self.assertEqual(c["message"], canonical)
        signature = KEY.sign(b"<Bytes>" + canonical.encode() + b"</Bytes>")
        return {"nonce": c["nonce"], "signature": "0x00" + signature.hex()}

    def test_accepted_once_and_durable_cooldown(self):
        body = self.signed()
        r = self.f.submit(IDENTITY, body)
        self.assertEqual((r["status"],r["finality"]), ("accepted","included"))
        self.assertEqual(self.posts, [{"address":IDENTITY["address"],"nonce":body["nonce"],"signature":"0x"+body["signature"][4:]}])
        self.assertEqual(self.f.submit(IDENTITY, body), r)
        with self.assertRaisesRegex(ChatError, "FAUCET_WAIT"):
            self.f.prepare(IDENTITY, {})
        self.assertEqual(len(self.posts), 1)

    def test_ambiguous_response_blocks_after_restart(self):
        self.reply = ChatError("FAUCET_UNAVAILABLE", 502)
        body = self.signed()
        self.assertEqual(self.f.submit(IDENTITY, body)["status"], "unknown")
        restarted = Faucet(self.path, GENESIS, ChatError, verify_signature)
        with self.assertRaisesRegex(ChatError, "FAUCET_UNKNOWN"):
            restarted.prepare(IDENTITY,{})
        self.assertEqual(restarted.submit(IDENTITY, body)["status"], "unknown")
        self.assertEqual(len(self.posts), 1)
        self.assertNotIn(body["signature"], self.path.read_text())

    def test_429_and_spend_requirement(self):
        for code, reason, wait in [(429, "daily_cap", 3600), (403, "agent_spend_missing", 0)]:
            with self.subTest(reason=reason):
                self.reply = code, {"success":False, "reason":reason, "action":"retry_later","retryAfterSeconds":wait}
                body = self.signed()
                r = self.f.submit(IDENTITY, body)
                self.assertEqual((r["status"],r["http"],r["reason"],r["retryAfterSeconds"]), ("refused",code,reason,wait))
                if wait:
                    with self.assertRaisesRegex(ChatError, "FAUCET_WAIT"):
                        self.f.prepare(IDENTITY,{})
                self.path.unlink()

    def test_gate_checked_again_and_signature_required(self):
        body = self.signed()
        with self.assertRaisesRegex(ChatError,"SIGNATURE_INVALID"):
            self.f.submit(IDENTITY,{**body,"signature":"0x"+"ff"*64})
        self.open = False
        with self.assertRaisesRegex(ChatError,"FAUCET_CLOSED"):
            self.f.submit(IDENTITY,body)
        self.assertEqual(self.posts, [])

    def test_finalized_free_balance_uses_pinned_block(self):
        free = 9876543210000000001
        value = "0x" + (bytes(16)+free.to_bytes(16,"little")+bytes(48)).hex()
        with patch.object(self.f, "request", side_effect=[(200,{"result":x}) for x in [GENESIS,"0x"+"aa"*32,value]]) as rpc:
            self.assertEqual(self.f.balance(IDENTITY),str(free))
            key, block = rpc.call_args.args[1]["params"]
            self.assertTrue(key.endswith(IDENTITY["public_key"][2:]))
            self.assertEqual(block, "0x"+"aa"*32)

    def test_sr25519_login_and_wrapped_faucet_via_wallet_verifier(self):
        # Public deterministic test fixture. The production Python verifier receives only public data.
        js = """
import {SessionKey,ready} from './node_modules/@flop-labs/sdk/dist/compute-channel/crypto.js';
import {u8aToHex,u8aWrapBytes} from '@polkadot/util';
import {readFileSync} from 'node:fs';
await ready();
const key = SessionKey.fromSeed(new Uint8Array(32).fill(9));
const bytes = new TextEncoder().encode(readFileSync(0,'utf8'));
console.log(JSON.stringify({public:u8aToHex(key.publicKey), signature:'0x01'+u8aToHex(key.sign(u8aWrapBytes(bytes))).slice(2)}));
"""
        def sign(message):
            return json.loads(subprocess.run(["node", "--input-type=module", "-e", js], input=message,
                              capture_output=True, text=True, check=True, cwd=Path(__file__).resolve().parents[1]).stdout)
        account = identity(bytes.fromhex(sign("")["public"][2:]), "sr25519")
        chat = Chat(self.path.with_name("ledger.json"), FakeGateway(), expected_did=account["did"], clock=lambda:NOW)
        chat.catalog()
        with patch.object(chat,"remote", side_effect=ChatError("GATEWAY_HTTP",404)):
            c = chat.new_challenge({"address":account["address"], "type":"sr25519"})
            self.assertEqual(chat.enroll({"signature":sign(c["message"])["signature"]})["account"],account)
        chat.faucet.request = self.request
        c = chat.faucet_action("prepare", {})
        result = chat.faucet_action("submit", {"nonce":c["nonce"],"signature":sign(c["message"])["signature"]})
        self.assertEqual(result["status"], "accepted")
        self.assertEqual(self.posts[0]["address"], account["address"])

    def test_gateway_404_local_login_and_address_lock(self):
        chat = Chat(self.path.with_name("ledger.json"), FakeGateway(), expected_address=IDENTITY["address"],clock=lambda:NOW)
        with self.assertRaisesRegex(ChatError,"EXPECTED_ADDRESS_MISMATCH"):
            chat.new_challenge({"address":identity(bytes(32))["address"]})
        chat.catalog()
        with patch.object(chat,"remote", side_effect=ChatError("GATEWAY_HTTP",404)):
            c = chat.new_challenge({"address":IDENTITY["address"]})
            r = chat.enroll({"signature":"0x"+KEY.sign(c["message"].encode()).hex()})
        self.assertEqual(r["gateway_block"],"ENROLLMENT_UNAVAILABLE")
        self.assertEqual(r["account"],IDENTITY)
        self.assertFalse(r["connected"])
