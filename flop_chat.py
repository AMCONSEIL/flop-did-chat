"""Local FLOP chat. No private-key access; bearer credentials stay in memory."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import signal
import subprocess
import threading
import time
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.parse
import urllib.request

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from direct_chat import Direct, model_slug, RAW
from faucet import Faucet

VERSION = "0.3.0"
AUTHOR_DID = "did:key:z6Mkt3DNtpGBNh1KHYwLQEk6QtCcJ7vVaRPze1SU7MyhFMVD"
API = "https://gateway.testnet.flop.network/v1"
GENESIS = "0x918abd58fb16306b30ef3886514cfaebffecb4de43e82b6f8ec4795c43cfd800"
BASE = Path(__file__).resolve().parent
B58 = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
MAX_BODY = 100_000
MAX_REPLY = 4_000_000
DEFAULT_REQUEST_CAP = Decimal("0.9")
TOKEN_CAP = 1024
GATEWAY_EXPIRY_CODES = {"api_key_expired", "devnet_enrollment_expired"}
TERMINAL = {"released", "settled"}


class ChatError(Exception):
    def __init__(self, code, status=400, detail="", retry_after=None):
        self.code, self.status, self.detail = code, status, detail
        self.retry_after = retry_after
        super().__init__(code)

    def public(self):
        return {"error": self.code, "detail": self.detail,
                "retry_after": self.retry_after}


def b58encode(raw):
    number = int.from_bytes(raw, "big")
    result = ""
    while number:
        number, digit = divmod(number, 58)
        result = B58[digit] + result
    return "1" * (len(raw) - len(raw.lstrip(b"\0"))) + result


def b58decode(text):
    if not isinstance(text, str) or not 1 <= len(text) <= 100:
        raise ChatError("IDENTITY_INVALID")
    try:
        number = 0
        for char in text:
            number = number * 58 + B58.index(char)
        raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
        raw = b"\0" * (len(text) - len(text.lstrip("1"))) + raw
    except (ValueError, OverflowError):
        raise ChatError("IDENTITY_INVALID") from None
    if b58encode(raw) != text:
        raise ChatError("IDENTITY_INVALID")
    return raw


def identity(public, key_type="ed25519"):
    if key_type not in ("ed25519", "sr25519"):
        raise ChatError("IDENTITY_INVALID")
    codec = b"\xed\x01" if key_type == "ed25519" else b"\xef\x01"
    payload = b"\x2a" + public
    checksum = hashlib.blake2b(b"SS58PRE" + payload, digest_size=64).digest()[:2]
    return {"type": key_type, "did": "did:key:z" + b58encode(codec + public),
            "address": b58encode(payload + checksum), "public_key": "0x" + public.hex()}


def parse_identity(address, did=None, key_type="ed25519"):
    raw = b58decode(address)
    if raw[0] & 0x80:
        raise ChatError("IDENTITY_INVALID")
    prefix = 2 if raw[0] & 0x40 else 1
    if len(raw) != prefix + 34:
        raise ChatError("IDENTITY_INVALID")
    checksum = hashlib.blake2b(b"SS58PRE" + raw[:-2], digest_size=64).digest()[:2]
    if not secrets.compare_digest(checksum, raw[-2:]):
        raise ChatError("IDENTITY_INVALID")
    result = identity(raw[prefix:-2], key_type)
    if did and did != result["did"]:
        raise ChatError("DID_MISMATCH")
    return result


def decimal(value):
    try:
        if isinstance(value, bool):
            raise InvalidOperation
        number = Decimal(str(value))
        if not number.is_finite() or number < 0:
            raise InvalidOperation
        return number
    except (InvalidOperation, ValueError):
        raise ChatError("AMOUNT_INVALID") from None


def positive_limit(value):
    number = decimal(value)
    # The upstream JSON number must remain finite and positive too.
    if number <= 0 or not math.isfinite(float(number)) or float(number) <= 0:
        raise ChatError("LIMIT_INVALID")
    return number


def verify_signature(public_hex, message, signature, key_type="ed25519", wrapped_only=False):
    if not isinstance(signature, str) or not re.fullmatch(r"0x[0-9a-fA-F]{128}(?:[0-9a-fA-F]{2})?", signature):
        raise ChatError("SIGNATURE_INVALID")
    if key_type == "sr25519":
        try:
            result = subprocess.run(["node", str(BASE / "wallet_verify.mjs"), "--verify"],
                    input=json.dumps(dict(type=key_type, publicKey=public_hex, message=message,
                                          signature=signature, wrappedOnly=wrapped_only)),
                    text=True, capture_output=True, timeout=12)
        except (OSError, subprocess.TimeoutExpired):
            raise ChatError("WALLET_VERIFIER_UNAVAILABLE", 503) from None
        if result.returncode:
            raise ChatError("SIGNATURE_INVALID")
        return
    raw = bytes.fromhex(signature[2:])
    if len(raw) == 65:
        if raw[0] != 0:
            raise ChatError("ED25519_REQUIRED")
        raw = raw[1:]
    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_hex[2:]))
    for payload in ([message.encode()] if not wrapped_only else []) + [b"<Bytes>" + message.encode() + b"</Bytes>"]:
        try:
            key.verify(raw, payload)
            return
        except InvalidSignature:
            pass
    raise ChatError("SIGNATURE_INVALID")


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ChatError("GATEWAY_REDIRECT_REFUSED", 502)


class Gateway:
    """Fixed HTTPS origin, no redirects, no retries, bounded responses."""
    def __init__(self):
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())

    def request(self, path, payload=None, key=None, request_id=None):
        headers = {"Accept": "application/json", "User-Agent": "FLOP-DID-Chat/" + VERSION}
        if key:
            headers["Authorization"] = "Bearer " + key
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if request_id:
            headers.update({"X-Request-ID": request_id, "Idempotency-Key": request_id})
        request = urllib.request.Request(API + path, headers=headers,
                data=None if payload is None else json.dumps(payload).encode())
        try:
            with self.opener.open(request, timeout=75 if path == "/chat/completions" else 20) as response:
                raw = response.read(MAX_REPLY + 1)
                response_headers = response.headers
        except urllib.error.HTTPError as error:
            raw = error.read(16_384).decode("utf-8", errors="replace")
            if key:
                raw = raw.replace(key, "[redacted]")
            try:
                data = json.loads(raw)
                upstream = data.get("error", {})
                code = upstream.get("code", "GATEWAY_HTTP") if isinstance(upstream, dict) else str(upstream)
                detail = upstream.get("message", "") if isinstance(upstream, dict) else data.get("message", "")
                if not isinstance(detail, str):
                    detail = ""
            except (ValueError, AttributeError):
                code, detail = "GATEWAY_HTTP", ""
            retry = error.headers.get("Retry-After")
            retry = min(3600, int(retry)) if retry and retry.isdigit() else None
            raise ChatError(str(code)[:100], error.code, detail[:600], retry) from None
        except (TimeoutError, OSError, urllib.error.URLError):
            raise ChatError("GATEWAY_UNREACHABLE", 502) from None
        if len(raw) > MAX_REPLY:
            raise ChatError("GATEWAY_RESPONSE_INVALID", 502)
        try:
            result = json.loads(raw)
        except (ValueError, UnicodeError):
            raise ChatError("GATEWAY_RESPONSE_INVALID", 502) from None
        if not isinstance(result, dict):
            raise ChatError("GATEWAY_RESPONSE_INVALID", 502)
        return result, dict(response_headers)


class Ledger:
    """Only request identities, public receipt fields and counters; no prompts or keys."""
    def __init__(self, path):
        self.path = Path(path)
        self.rows = {}
        if self.path.exists():
            if self.path.is_symlink() or self.path.stat().st_size > 4_000_000:
                raise ChatError("LEDGER_INVALID", 500)
            try:
                document = json.loads(self.path.read_text(encoding="utf-8"))
                if document.get("schema") != "flop-did-chat-ledger-v1" or not isinstance(document["requests"], dict):
                    raise ValueError
                self.rows = document["requests"]
            except (ValueError, KeyError):
                raise ChatError("LEDGER_INVALID", 500) from None

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        raw = json.dumps({"schema": "flop-did-chat-ledger-v1", "requests": self.rows},
                         ensure_ascii=True, indent=2)
        with temporary.open("w", encoding="utf-8") as out:
            out.write(raw)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, self.path)

    def for_address(self, address):
        return [r for r in self.rows.values() if r["address"] == address]


class Chat:
    def __init__(self, ledger, gateway=None, expected_did=None, reconcile_request=None,
                 session_cap=Decimal("0.9"), clock=None, expected_address=None):
        self.ledger = Ledger(ledger)
        self.gateway = gateway or Gateway()
        self.expected_did = expected_did
        self.expected_address = parse_identity(expected_address)["address"] if expected_address else None
        self.faucet = Faucet(Path(ledger).with_name("faucet-testnet.json"), GENESIS, ChatError, verify_signature)
        self.reconcile_request = reconcile_request
        self.session_cap = positive_limit(session_cap)
        self.request_cap = DEFAULT_REQUEST_CAP
        self.clock = clock or time.time
        self.lock = threading.RLock()
        self.key = None
        self.account = None
        self.auth = None
        self.challenge = None
        self.models = []
        self.models_at = 0
        self.external = []
        self.cooldown_until = 0
        self.last_error = None
        self.baseline_ids = set(self.ledger.rows)
        self.bootstrap_token = secrets.token_urlsafe(32)
        self.gateway_block = None
        self.direct_candidate = None
        self.direct = Direct(self, ChatError, parse_identity)

    def remote(self, path, payload=None, authenticated=False, request_id=None):
        if authenticated and not self.key:
            raise ChatError("CONNECT_REQUIRED", 401)
        return self.gateway.request(path, payload, self.key if authenticated else None, request_id)[0]

    def catalog(self):
        data = self.remote("/models")
        models = data.get("data")
        if not isinstance(models, list) or len(models) > 1000:
            raise ChatError("CATALOG_INVALID", 502)
        safe = []
        for model in models:
            if not isinstance(model, dict) or not isinstance(model.get("id"), str):
                continue
            modalities = model.get("architecture", {})
            if "text" not in modalities.get("input_modalities", ["text"]) or "text" not in modalities.get("output_modalities", ["text"]):
                continue
            safe.append({"id": model["id"][:200], "name": str(model.get("name", model["id"]))[:180],
                         "context_length": model.get("context_length"),
                         "max_completion_tokens": model.get("top_provider", {}).get("max_completion_tokens"),
                         "supported_parameters": model.get("supported_parameters", []),
                         "price_source": "gateway_catalog"})
        with self.lock:
            self.models, self.models_at = safe, self.clock()
        return self.snapshot()

    def new_challenge(self, body):
        did = body.get("did") or self.expected_did
        key_type = body.get("type", "ed25519")
        if did and parse_identity(body.get("address"))["did"] == did:
            key_type = "ed25519"
        account = parse_identity(body.get("address"), key_type=key_type)
        if self.expected_address and self.expected_address != account["address"]:
            raise ChatError("EXPECTED_ADDRESS_MISMATCH")
        if self.expected_did and account["did"] != self.expected_did:
            raise ChatError("EXPECTED_DID_MISMATCH")
        if did and account["did"] != did:
            raise ChatError("DID_MISMATCH")
        with self.lock:
            if self.direct.active() or any(r.get("local_state") == "sending" and r.get("route") != "direct"
                                           for r in self.ledger.rows.values()):
                raise ChatError("REQUEST_PENDING", 409)
            if self.account and self.account["address"] != account["address"] and self.unresolved():
                raise ChatError("RECONCILE_REQUIRED", 409)
            old = self.challenge
            if old and old["account"] == account and not old["submitted"] and old["expires_at"] > self.clock() * 1000:
                return self.public_challenge(old)
            try:
                if self.models_at < self.clock() - 120:
                    self.catalog()
                if not self.models:
                    raise ChatError("NO_MODELS_AVAILABLE", 503)
                challenge = self.remote("/enroll/wallet/challenge?" + urllib.parse.urlencode({"address": account["address"]}))
            except ChatError as error:
                if error.status == 404:
                    error = ChatError("ENROLLMENT_UNAVAILABLE", 404)
                if error.status != 404 and (not self.direct.available or (error.status != 503 and error.code not in
                        GATEWAY_EXPIRY_CODES | {"GATEWAY_UNREACHABLE"})):
                    raise
                expiry = int((self.clock() + 120) * 1000)
                message = "\n".join(["FLOP DID Chat local connection — no blockchain transaction",
                                      "Genesis: " + GENESIS, "DID: " + account["did"],
                                      "Address: " + account["address"], "Nonce: " + secrets.token_hex(32),
                                      "Expires At: " + str(expiry)])
                self.challenge = {"account": account, "message": message, "expires_at": expiry,
                                  "submitted": False, "local_reason": error.code}
                return self.public_challenge(self.challenge)
            message, nonce, expiry = challenge.get("message"), challenge.get("nonce"), challenge.get("expires_at")
            if (not isinstance(message, str) or len(message) > 3500
                    or not isinstance(nonce, str) or not re.fullmatch(r"[0-9a-f]{64}", nonce)
                    or not isinstance(expiry, int) or not self.clock() * 1000 < expiry <= (self.clock() + 360) * 1000
                    or "Action: flop-testnet-enroll/v1" not in message.splitlines()
                    or not {"Address: " + account["address"], "Genesis: " + GENESIS, "Nonce: " + nonce, "Domain: https://gateway.testnet.flop.network"}.issubset(message.splitlines())):
                raise ChatError("CHALLENGE_INVALID", 502)
            self.challenge = {"account": account, "message": message, "expires_at": expiry,
                              "submitted": False}
            return self.public_challenge(self.challenge)

    @staticmethod
    def public_challenge(challenge):
        return {"account": challenge["account"], "message": challenge["message"],
                "expires_at": challenge["expires_at"]}

    def enroll(self, body):
        with self.lock:
            c = self.challenge
            if not c or c["submitted"] or c["expires_at"] <= self.clock() * 1000:
                raise ChatError("CHALLENGE_EXPIRED", 409)
            verify_signature(c["account"]["public_key"], c["message"], body.get("signature"), c["account"]["type"])
            c["submitted"] = True
            if c.get("local_reason"):
                return self.local_connection(c, c["local_reason"])
            try:
                result = self.remote("/enroll/wallet", {
                    "address": c["account"]["address"], "message": c["message"],
                    "signature": body["signature"]})
            except ChatError as error:
                if error.status == 404:
                    return self.local_connection(c, "ENROLLMENT_UNAVAILABLE")
                if not self.direct.available or (error.code not in GATEWAY_EXPIRY_CODES | {"devnet_allowance_exhausted",
                        "wallet_unfunded", "GATEWAY_UNREACHABLE"} and error.status != 503):
                    raise
                return self.local_connection(c, error.code)
            if (self.direct.available and isinstance(result.get("expires_at"), int)
                    and result["expires_at"] <= self.clock() * 1000):
                # Keep an issued credential in memory for receipt reconciliation only.
                self.local_connection(c, "api_key_expired")
                if isinstance(result.get("key"), str) and isinstance(result.get("model"), str):
                    self.key = result["key"] or None
                    self.auth = {k: result.get(k) for k in ("expires_at", "remaining_quota", "model")}
                    self.auth.update(verified=False, reconciled=False)
                return self.snapshot()
            if (not isinstance(result.get("key"), str) or not result["key"]
                    or not isinstance(result.get("expires_at"), int)
                    or result["expires_at"] <= self.clock() * 1000
                    or not isinstance(result.get("model"), str)):
                raise ChatError("ENROLLMENT_INVALID", 502)
            # Store only in memory even if catalogue validation/introspection fails.
            if self.account != c["account"]:
                self.external = []
            self.key = result["key"]
            self.account = c["account"]
            self.gateway_block = None
            self.direct_candidate = None
            self.cooldown_until = max([r.get("retry_not_before", 0) for r in self.ledger.for_address(self.account["address"])] + [0])
            self.auth = {k: result.get(k) for k in ["model", "remaining_quota", "expires_at"]}
            self.auth["verified"] = False
            self.auth["reconciled"] = False
            self.catalog()
            if self.auth["model"] not in {m["id"] for m in self.models}:
                raise ChatError("MODEL_NOT_AVAILABLE", 503)
            self.auth["verified"] = True
            self.refresh()
            return self.snapshot()

    def local_connection(self, challenge, reason):
        if self.account != challenge["account"]:
            self.external = []
            self.key = self.auth = None
        self.account = challenge["account"]
        if self.auth:
            self.auth["verified"] = False
        self.gateway_block = reason
        self.direct_candidate = None
        return self.snapshot()

    def direct_gateway_block(self):
        if self.gateway_block:
            return self.gateway_block
        if self.auth and self.auth["expires_at"] <= self.clock() * 1000:
            return "api_key_expired"
        if self.connected() and decimal(self.auth["remaining_quota"]) == 0:
            return "QUOTA_EXHAUSTED"
        return None

    def direct_allowed(self, source):
        if (not self.account or source["address"] != self.account["address"] or self.unresolved()
                or self.direct.active() or "direct-" + source["id"][5:] in self.ledger.rows
                or not model_slug(source["model"])):
            return False
        if self.reconcile_request and not any(r["request_id"] == self.reconcile_request and r.get("state") in TERMINAL
                for r in self.ledger.for_address(self.account["address"]) + self.external):
            return False
        row = self.ledger.rows.get(source["id"])
        if row:
            return (row["address"] == source["address"] and row["state"] == "released"
                    and not row["response_received"] and row["response_status"] == source["status"]
                    and row["response_status"] in {429, 503}
                    and row.get("settled_spend_raw") in (None, "0", 0) and row.get("settled_spend") in (None, 0))
        return source["status"] == "catalog" or bool(self.direct_gateway_block())

    @staticmethod
    def decimal_cost(raw):
        return Decimal(raw) / RAW

    def fallback(self, request_id, payload, cap, status=None):
        self.direct_candidate = {"id": request_id, "address": self.account["address"], "model": payload["model"],
                                 "messages": payload["messages"], "tokens": payload["max_tokens"],
                                 "cap": cap, "status": status}

    def connected(self):
        return bool(self.key and self.auth and self.auth.get("verified") and self.auth.get("reconciled")
                    and self.auth["expires_at"] > self.clock() * 1000)

    def unresolved(self):
        own = self.ledger.for_address(self.account["address"]) if self.account else []
        external = self.external
        return [r for r in own + external if r.get("state") not in TERMINAL]

    def session_commitment(self):
        total = Decimal(0)
        if not self.account:
            return total
        for row in self.ledger.for_address(self.account["address"]):
            if row["request_id"] in self.baseline_ids:
                continue
            if row.get("route") == "direct" and row.get("state") in TERMINAL:
                if row.get("local_state") != "not_submitted":
                    total += self.decimal_cost(int(row["opening_fee_cap_raw"]) + int(row.get("settled_spend_raw") or "0"))
                continue
            if row.get("state") == "released":
                continue
            if row.get("state") == "settled" and row.get("settled_spend_raw") is not None:
                total += Decimal(row["settled_spend_raw"]) / 10**18
            elif row.get("state") == "settled" and row.get("settled_spend") is not None:
                total += decimal(row["settled_spend"])
            else:
                total += decimal(row.get("max_cost_flop", DEFAULT_REQUEST_CAP))
        return total

    def snapshot(self):
        with self.lock:
            rows = self.ledger.for_address(self.account["address"]) if self.account else []
            rows = [{k: v for k, v in r.items() if k not in {"fingerprint", "address"}} for r in rows]
            return {"version": VERSION, "author_did": AUTHOR_DID, "expected_did": self.expected_did,
                    "account": self.account, "connected": self.connected(), "auth": self.auth,
                    "models": self.models, "models_checked_at": self.models_at,
                    "requests": rows[-200:], "recent_receipts": self.external,
                    "limits": {"request_cap": str(self.request_cap), "max_tokens": TOKEN_CAP,
                               "session_cap": str(self.session_cap),
                               "session_committed": str(self.session_commitment())},
                    "unresolved": [r["request_id"] for r in self.unresolved()],
                    "cooldown_until": self.cooldown_until,
                    "last_error": self.last_error, "gateway_block": self.direct_gateway_block(),
                    "direct": {**self.direct.snapshot(),
                               "request_id": self.direct_candidate["id"] if self.direct.available and
                               self.direct_candidate and self.direct_allowed(self.direct_candidate) else None}}

    def faucet_action(self, action, body):
        with self.lock:
            if not self.account:
                raise ChatError("CONNECT_REQUIRED", 401)
            return getattr(self.faucet, action)(self.account, body)

    def refresh(self):
        with self.lock:
            if not self.key:
                return self.snapshot()
            self.auth["reconciled"] = False
            current = self.remote("/keys/me", authenticated=True)
            if not isinstance(current.get("remaining_quota"), (int, float)):
                raise ChatError("QUOTA_INVALID", 502)
            if self.auth:
                self.auth["remaining_quota"] = current["remaining_quota"]
                # Never extend the original enrollment window.
                if isinstance(current.get("expires_at"), int):
                    self.auth["expires_at"] = min(self.auth["expires_at"], current["expires_at"])
            recent = self.remote("/keys/me/receipts", authenticated=True)
            records = recent.get("receipts", recent.get("data"))
            if not isinstance(records, list) or len(records) > 200:
                raise ChatError("RECEIPTS_INVALID", 502)
            clean = [self.sanitize_receipt(r) for r in records]
            self.external = [r for r in clean if r["request_id"] not in self.ledger.rows]
            ids = {r["request_id"] for r in self.ledger.for_address(self.account["address"]) if r.get("route") != "direct"}
            if self.reconcile_request:
                ids.add(self.reconcile_request)
            observed = {r["request_id"]: r for r in clean}
            for request_id in ids:
                if request_id not in observed or observed[request_id]["state"] not in TERMINAL:
                    try:
                        observed[request_id] = self.read_receipt(request_id)
                    except ChatError as error:
                        if request_id in self.ledger.rows:
                            self.ledger.rows[request_id]["receipt_error"] = error.code
                        elif request_id == self.reconcile_request:
                            self.external.append({"request_id": request_id, "state": "unknown",
                                                  "receipt_error": error.code})
                        continue
                self.apply_receipt(observed[request_id])
            if self.reconcile_request and self.reconcile_request in observed and self.reconcile_request not in self.ledger.rows:
                self.external = [r for r in self.external if r["request_id"] != self.reconcile_request]
                self.external.append(observed[self.reconcile_request])
            self.ledger.save()
            self.auth["reconciled"] = True
            return self.snapshot()

    @staticmethod
    def sanitize_receipt(value):
        if not isinstance(value, dict):
            raise ChatError("RECEIPT_INVALID", 502)
        keys = ["request_id", "correlation_id", "model", "reserved_spend", "settled_spend",
                "settled_spend_raw", "terminal_event", "channel_id", "created_at", "state", "response_status"]
        receipt = {k: value.get(k) for k in keys}
        if (not isinstance(receipt["request_id"], str) or not 1 <= len(receipt["request_id"]) <= 128
                or receipt["state"] not in {"reserved", "estimated", "settled", "released"}):
            raise ChatError("RECEIPT_INVALID", 502)
        for key in ["reserved_spend", "settled_spend"]:
            if receipt[key] is not None:
                decimal(receipt[key])
        if receipt["settled_spend_raw"] is not None and not re.fullmatch(r"[0-9]+", str(receipt["settled_spend_raw"])):
            raise ChatError("RECEIPT_INVALID", 502)
        return receipt

    def read_receipt(self, request_id):
        data = self.remote("/keys/me/receipts/" + urllib.parse.quote(request_id, safe=""), authenticated=True)
        result = self.sanitize_receipt(data)
        if result["request_id"] != request_id:
            raise ChatError("RECEIPT_ID_MISMATCH", 502)
        return result

    def apply_receipt(self, receipt):
        request_id = receipt["request_id"]
        row = self.ledger.rows.get(request_id)
        if row and row.get("route") != "direct" and self.account and row["address"] == self.account["address"]:
            row.update(receipt)
            row.pop("receipt_error", None)
            row["local_state"] = "complete" if row.get("response_received") else "reconciled"
            self.ledger.save()

    def chat(self, body):
        with self.lock:
            if not self.account or (not self.connected() and not (self.direct.available and self.direct_gateway_block())):
                raise ChatError("CONNECT_REQUIRED", 401)
            if self.direct.active():
                raise ChatError("REQUEST_PENDING", 409)
            request_id = body.get("request_id")
            if not isinstance(request_id, str) or not re.fullmatch(r"chat-[0-9a-f]{32}", request_id):
                raise ChatError("REQUEST_ID_INVALID")
            model, messages = body.get("model"), body.get("messages")
            tokens = body.get("max_tokens", 256)
            cap = positive_limit(body.get("max_cost_flop", str(self.request_cap)))
            if cap > self.request_cap or type(tokens) is not int or not 1 <= tokens <= TOKEN_CAP:
                raise ChatError("LIMIT_INVALID")
            if (not isinstance(messages, list) or not 1 <= len(messages) <= 40
                    or any(not isinstance(m, dict) or set(m) != {"role", "content"}
                           or m["role"] not in {"user", "assistant"} or not isinstance(m["content"], str)
                           or not m["content"].strip() or len(m["content"]) > 12_000 for m in messages)
                    or messages[-1]["role"] != "user"
                    or sum(len(m["content"]) for m in messages) > 30_000):
                raise ChatError("MESSAGES_INVALID")
            payload = {"model": model, "messages": messages, "max_tokens": tokens,
                       "max_cost_flop": float(cap), "max_wait_ms": 60000, "stream": False}
            fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            prior = self.ledger.rows.get(request_id)
            if prior:
                if prior["address"] != self.account["address"] or prior["fingerprint"] != fingerprint:
                    raise ChatError("REQUEST_ID_CONFLICT", 409)
                # Never replay the network call, even after a restart or browser double-click.
                return {"request": self.public_row(prior), "state": self.snapshot(), "duplicate": True}
            if self.unresolved():
                raise ChatError("RECONCILE_REQUIRED", 409)
            if "direct-" + request_id[5:] in self.ledger.rows:
                raise ChatError("REQUEST_ID_CONFLICT", 409)
            block = self.direct_gateway_block()
            if body.get("route") == "direct" and (not self.direct.available or not model_slug(model)):
                raise ChatError("DIRECT_NOT_ALLOWED", 409)
            if (block or body.get("route") == "direct") and self.direct.available and model_slug(model):
                self.fallback(request_id, payload, cap, status="catalog" if not block else None)
                return {"direct_offer": True, "state": self.snapshot()} if body.get("route") == "direct" else {
                    "error": ChatError(block, 403).public(), "state": self.snapshot()}
            if not self.connected():
                raise ChatError("CONNECT_REQUIRED", 401)
            if self.cooldown_until > self.clock():
                raise ChatError("COOLDOWN", 429, retry_after=math.ceil(self.cooldown_until - self.clock()))
            if self.auth["model"] != model or model not in {m["id"] for m in self.models}:
                raise ChatError("MODEL_NOT_AUTHORIZED", 403)
            if self.models_at < self.clock() - 120:
                try:
                    self.catalog()
                    if model not in {m["id"] for m in self.models}:
                        raise ChatError("MODEL_NOT_AVAILABLE", 503)
                except ChatError as error:
                    if (not self.direct.available or not model_slug(model)
                            or (error.status != 503 and error.code != "GATEWAY_UNREACHABLE")):
                        raise
                    self.fallback(request_id, payload, cap, "catalog")
                    return {"error": error.public(), "state": self.snapshot()}
            advertised = next(m for m in self.models if m["id"] == model)
            live_cap = advertised.get("max_completion_tokens")
            if "max_tokens" not in advertised.get("supported_parameters", []) or (isinstance(live_cap, int) and tokens > live_cap):
                raise ChatError("LIMIT_INVALID")
            if self.session_commitment() + cap > self.session_cap:
                raise ChatError("SESSION_LIMIT", 403)
            if decimal(self.auth["remaining_quota"]) == 0:
                raise ChatError("QUOTA_EXHAUSTED", 403)
            row = {"request_id": request_id, "address": self.account["address"], "model": model,
                   "fingerprint": fingerprint, "created_at": int(self.clock() * 1000),
                   "max_cost_flop": str(cap), "max_tokens": tokens,
                   "state": "unknown", "local_state": "sending", "response_received": False,
                   "reserved_spend": None, "settled_spend": None, "settled_spend_raw": None,
                   "channel_id": None, "terminal_event": None}
            self.direct_candidate = None
            self.ledger.rows[request_id] = row
            self.ledger.save()  # Persist original identity BEFORE submitting.
        completion, error, status = None, None, None
        try:
            result = self.remote("/chat/completions", payload, authenticated=True, request_id=request_id)
            choices = result.get("choices", [])
            content = choices[0].get("message", {}).get("content") if choices and isinstance(choices[0], dict) else None
            if not isinstance(content, str):
                raise ChatError("COMPLETION_INVALID", 502)
            usage = {k: result.get("usage", {}).get(k) for k in ["prompt_tokens", "completion_tokens", "total_tokens", "cost_flop"]}
            completion = {"text": content, "usage": usage,
                          "finish_reason": choices[0].get("finish_reason"), "model": result.get("model")}
            with self.lock:
                row.update(response_received=True, local_state="received", usage=usage)
                self.ledger.save()
        except ChatError as caught:
            error, status = caught.public(), caught.status
            with self.lock:
                row.update(error=error, local_state="needs_receipt")
                # Capacity and rate-limit errors never trigger retry.
                if caught.status in {429, 503}:
                    self.cooldown_until = self.clock() + max(60, caught.retry_after or 600)
                    row["retry_not_before"] = self.cooldown_until
                self.last_error = error
                self.ledger.save()
        except Exception:
            error = ChatError("OUTCOME_UNKNOWN", 502).public()
            with self.lock:
                row.update(error=error, local_state="needs_receipt")
                self.ledger.save()
        with self.lock:
            try:
                self.apply_receipt(self.read_receipt(request_id))
            except ChatError as caught:
                row["receipt_error"] = caught.code
                self.ledger.save()
            try:
                self.refresh()
            except ChatError:
                pass
            if status in {429, 503} and completion is None:
                self.fallback(request_id, payload, cap, status)
            return {"request": self.public_row(row), "completion": completion,
                    "error": error, "state": self.snapshot()}

    @staticmethod
    def public_row(row):
        return {k: v for k, v in row.items() if k not in {"address", "fingerprint"}}

    def update_limits(self, body):
        with self.lock:
            cap = positive_limit(body.get("session_cap", str(self.session_cap)))
            request_cap = positive_limit(body.get("request_cap", str(self.request_cap)))
            if cap < self.session_commitment():
                raise ChatError("LIMIT_INVALID")
            if request_cap > cap:
                raise ChatError("REQUEST_CAP_EXCEEDS_SESSION")
            if self.unresolved():
                raise ChatError("RECONCILE_REQUIRED", 409)
            if self.direct.active():
                raise ChatError("REQUEST_PENDING", 409)
            # Validate both values before changing either. Settings do not spend.
            self.session_cap, self.request_cap = cap, request_cap
            return self.snapshot()

    def disconnect(self):
        with self.lock:
            if self.unresolved() or self.direct.active():
                raise ChatError("RECONCILE_REQUIRED", 409)
            self.key = self.auth = self.account = self.challenge = None
            self.gateway_block = self.direct_candidate = None
            self.external = []
        return self.snapshot()


def make_handler(chat):
    assets = {"/": ("index.html", "text/html; charset=utf-8"),
              "/app.js": ("app.js", "text/javascript; charset=utf-8"),
              "/core.js": ("core.js", "text/javascript; charset=utf-8"),
              "/style.css": ("style.css", "text/css; charset=utf-8"),
              "/icon.svg": ("icon.svg", "image/svg+xml")}
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, status, data, content_type="application/json; charset=utf-8"):
            raw = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=True).encode()
            self.send_response(status)
            for name, value in {
                "Content-Type": content_type, "Content-Length": str(len(raw)),
                "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer", "X-Frame-Options": "DENY",
                "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; "
                   "connect-src 'self'; img-src 'self' data:; font-src 'self'; frame-ancestors 'none'; "
                   "base-uri 'none'; form-action 'none'; object-src 'none'",
            }.items():
                self.send_header(name, value)
            self.end_headers()
            try:
                self.wfile.write(raw)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def host_ok(self):
            return self.headers.get("Host") == self.server.local_host

        def do_GET(self):
            if not self.host_ok():
                return self.send(403, {"error": "LOCAL_ORIGIN_REQUIRED"})
            if self.path == "/api/state":
                return self.send(200, chat.snapshot())
            if self.path not in assets:
                return self.send(404, {"error": "NOT_FOUND"})
            name, content_type = assets[self.path]
            raw = (BASE / "web" / name).read_bytes()
            if name == "index.html":
                raw = raw.replace(b"__CSRF__", chat.bootstrap_token.encode())
            self.send(200, raw, content_type)

        def do_POST(self):
            if (not self.host_ok() or self.headers.get("Origin") != "http://" + self.server.local_host
                    or not secrets.compare_digest(self.headers.get("X-Chat-Local", ""), chat.bootstrap_token)):
                return self.send(403, {"error": "LOCAL_ORIGIN_REQUIRED"})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= MAX_BODY:
                    raise ChatError("BODY_INVALID", 413)
                if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                    raise ChatError("CONTENT_TYPE_INVALID", 415)
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    raise ChatError("BODY_INVALID")
                routes = {"/api/limits": lambda: chat.update_limits(body), "/api/models": lambda: chat.catalog(), "/api/challenge": lambda: chat.new_challenge(body),
                          "/api/enroll": lambda: chat.enroll(body), "/api/refresh": lambda: chat.refresh(),
                          "/api/chat": lambda: chat.chat(body), "/api/disconnect": lambda: chat.disconnect(),
                          "/api/faucet/status": lambda: chat.faucet_action("status", body),
                          "/api/faucet/prepare": lambda: chat.faucet_action("prepare", body),
                          "/api/faucet/submit": lambda: chat.faucet_action("submit", body),
                          "/api/direct/prepare": lambda: chat.direct.prepare(body),
                          "/api/direct/sign": lambda: chat.direct.sign(body),
                          "/api/direct/submit": lambda: chat.direct.submit(body),
                          "/api/direct/cancel": lambda: chat.direct.cancel(body),
                          "/api/direct/reconcile": lambda: chat.direct.reconcile(body)}
                if self.path not in routes:
                    raise ChatError("NOT_FOUND", 404)
                self.send(200, routes[self.path]())
            except ChatError as error:
                self.send(error.status if 400 <= error.status < 600 else 500, error.public())
            except (ValueError, UnicodeError):
                self.send(400, {"error": "BODY_INVALID"})
            except Exception:
                self.send(500, {"error": "LOCAL_ERROR"})
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=50510)
    parser.add_argument("--open-browser", action="store_true")
    parser.add_argument("--expected-address", help="Lock this installation to a public SS58 address.")
    parser.add_argument("--expected-did", help="Optional public DID lock for your personal installation.")
    parser.add_argument("--reconcile-request", help="Existing public receipt ID to reconcile after enrollment.")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Use a local unprivileged port.")
    local = BASE / ".local"
    local.mkdir(exist_ok=True)
    lock_path = local / "server.lock"
    try:
        lock_fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit("Another chat may be running. Check its window/process before removing .local/server.lock.")
    os.write(lock_fd, str(os.getpid()).encode())
    os.close(lock_fd)
    server = None
    try:
        chat = Chat(local / "ledger-testnet.json", expected_did=args.expected_did, expected_address=args.expected_address,
                    reconcile_request=args.reconcile_request)
        server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(chat))
        server.daemon_threads = True
        server.local_host = "127.0.0.1:" + str(args.port)
        print("FLOP DID Chat " + VERSION + " — http://" + server.local_host + "/", flush=True)
        print("Talisman signs locally. No inference before an explicit Send.", flush=True)
        if args.open_browser:
            import webbrowser
            webbrowser.open("http://" + server.local_host + "/")
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if server:
            server.server_close()
        lock_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
