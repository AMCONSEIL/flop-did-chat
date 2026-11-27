"""Browser-approved Testnet grants. Persist uncertainty before the single network POST."""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request

FAUCET = "https://faucet.flop.network"
CLAIM = "/v1/testnet/agent-claims"
RPC = "https://testnet.flop.network/"
ACCOUNT = "26aa394eea5630e07c48ae0c9558cef7b99d880ec681799c0cf30e8886371da9"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Faucet:
    def __init__(self, path, genesis, error, verify):
        self.path, self.genesis, self.error, self.verify = path, genesis, error, verify
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        self.challenges = {}

    def request(self, url, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json",
                                    "User-Agent": "FLOP-DID-Chat/0.3.0", "Accept": "application/json", "Cache-Control": "no-cache"})
        try:
            try:
                response = self.opener.open(req, timeout=30)
            except urllib.error.HTTPError as exc:
                response = exc
            with response:
                raw = response.read(262145)
                if len(raw) > 262144:
                    raise ValueError
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError
                return response.status, result
        except (OSError, ValueError, TimeoutError):
            raise self.error("FAUCET_UNAVAILABLE", 502) from None

    def budget(self):
        code, chain = self.request(FAUCET + "/chain")
        if code != 200 or chain.get("genesisHash") != self.genesis or chain.get("network") != "testnet":
            raise self.error("FAUCET_NETWORK_INVALID", 502)
        code, limits = self.request(FAUCET + "/limits")
        f = limits.get("faucet", {})
        agent = f.get("agent", {})
        remaining = str(f.get("dailyCap", {}).get("remainingFlop", ""))
        if (code != 200 or limits.get("network") != "testnet" or limits.get("stale") is not False
                or agent.get("claimPath") not in (None, CLAIM) or str(agent.get("grantFlop")) != "10"
                or not remaining.isascii() or not remaining.isdigit()):
            raise self.error("FAUCET_NETWORK_INVALID", 502)
        return {"status": f.get("status"), "remainingFlop": remaining,
                "open": agent.get("claimPath") == CLAIM and f.get("status") == "open" and int(remaining) >= 10,
                "rolloverRequiresSpend": agent.get("rolloverRequiresSpend")}

    def balance(self, account):
        def rpc(method, params):
            code, data = self.request(RPC, dict(jsonrpc="2.0", id=1, method=method, params=params))
            if code != 200 or "result" not in data:
                raise self.error("BALANCE_UNAVAILABLE", 502)
            return data["result"]
        if rpc("chain_getBlockHash", [0]) != self.genesis:
            raise self.error("FAUCET_NETWORK_INVALID", 502)
        head = rpc("chain_getFinalizedHead", [])
        if not isinstance(head, str) or not re.fullmatch(r"0x[0-9a-f]{64}", head):
            raise self.error("BALANCE_UNAVAILABLE", 502)
        public = bytes.fromhex(account["public_key"][2:])
        key = "0x" + ACCOUNT + hashlib.blake2b(public, digest_size=16).hexdigest() + public.hex()
        value = rpc("state_getStorage", [key, head])
        if value is None:
            return "0"
        if not isinstance(value, str) or not re.fullmatch(r"0x[0-9a-f]{160}", value):
            raise self.error("BALANCE_UNAVAILABLE", 502)
        return str(int.from_bytes(bytes.fromhex(value[2:])[16:32], "little"))

    def records(self):
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else {}

    def save(self, records):
        tmp = self.path.with_suffix(".tmp")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w", encoding="utf-8") as f:
            json.dump(records, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
        if os.name == "posix":
            fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(fd)
            finally:
                os.close(fd)

    def status(self, account, body):
        result = self.budget()
        result["claim"] = self.records().get(account["address"])
        try:
            result["free_raw"] = self.balance(account)
        except self.error:
            result["free_raw"] = None
        return result

    def prepare(self, account, body):
        address = account["address"]
        record = self.records().get(address, {})
        if record.get("status") == "unknown":
            raise self.error("FAUCET_UNKNOWN", 409)
        if record.get("retry_at", 0) > time.time():
            raise self.error("FAUCET_WAIT", 429, retry_after=int(record["retry_at"] - time.time()) + 1)
        if not self.budget()["open"]:
            raise self.error("FAUCET_CLOSED", 429)
        nonce = str(time.time_ns() // 1_000_000)
        challenge = {"address": address, "nonce": nonce, "expires_at": int(time.time()) + 120,
                     "message": "|".join(("flop-faucet-agent/v1", self.genesis, address, nonce))}
        self.challenges[address] = challenge
        return challenge

    def submit(self, account, body):
        address = account["address"]
        records = self.records()
        old = records.get(address, {})
        if old.get("nonce") == body.get("nonce") and old:
            return old
        challenge = self.challenges.get(address)
        if (old.get("status") == "unknown" or not challenge or body.get("nonce") != challenge["nonce"]
                or time.time() >= challenge["expires_at"]):
            raise self.error("FAUCET_CHALLENGE_EXPIRED", 409)
        signature = body.get("signature")
        self.verify(account["public_key"], challenge["message"], signature, account["type"], wrapped_only=True)
        if not self.budget()["open"]:
            raise self.error("FAUCET_CLOSED", 429)
        record = {"status": "unknown", "nonce": challenge["nonce"]}
        records[address] = record
        self.save(records)
        del self.challenges[address]
        try:
            code, reply = self.request(FAUCET + CLAIM, {"address": address, "nonce": record["nonce"],
                                      "signature": "0x" + signature[-128:]})
        except self.error:
            return record
        if code == 200 and reply.get("success") is True and str(reply.get("amount")) == "10" and re.fullmatch(r"0x[0-9a-fA-F]{64}", str(reply.get("txHash"))):
            record.update(status="accepted", txHash=reply["txHash"], finality=reply.get("status"), retry_at=time.time()+86400)
        elif 400 <= code < 500 and code != 408 and reply.get("success") is False:
            retry = reply.get("retryAfterSeconds")
            retry = retry if type(retry) is int and retry >= 0 else 0
            record.update(status="refused", http=code, reason=str(reply.get("reason", ""))[:80],
                          retryAfterSeconds=retry, retry_at=time.time()+retry)
        self.save(records)
        return record
