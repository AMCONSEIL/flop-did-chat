"""Local bridge to a pinned FLOP SDK. All state changes use the chat's lock."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
from urllib.parse import urlsplit

BASE = Path(__file__).resolve().parent
MODEL = "qwen/qwen2.5-0.5b-instruct"
ESCROW = 200_000_000_000_000_000
FEE_CAP = 20_000_000_000_000_000
RAW = 10**18
HASH = re.compile(r"0x[0-9a-f]{64}")
ANTJU = {
    "name": "AntJu",
    "address": "5Hb9YKuWTejdAXrtzP1a91me3AzmNFmWQ1q5k6PdGn1chTNf",
    "endpoint": "https://fuzzy-compound-shark-click.trycloudflare.com",
}
NURSERYPOOL = {
    "name": "NurseryPool",
    "address": "5DkyfWjukrF6RJ8ZSii1eAQ8A7AAxZsHwdoJ1CHmAWY6NzqU",
    "endpoint": "https://flop.nurserypool.com",
}


def configured_miners(path, parse_identity, error):
    miners = [ANTJU, NURSERYPOOL]
    if path.exists():
        try:
            if path.stat().st_size > 16_384:
                return miners
            entries = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(entries, list) or len(entries) > 20:
                return miners
            for entry in entries:
                if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str)
                                                          for k in ("name", "address", "endpoint")):
                    continue
                endpoint = urlsplit(entry["endpoint"])
                if (endpoint.scheme != "https" or not endpoint.hostname
                        or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,}", endpoint.netloc)
                        or endpoint.path not in ("", "/") or endpoint.query or endpoint.fragment
                        or not entry["name"].strip() or len(entry["name"]) > 80):
                    continue
                try:
                    address = parse_identity(entry["address"])["address"]
                except (ValueError, error):
                    continue
                origin = "https://" + endpoint.netloc.lower()
                if address == ANTJU["address"] and miners[0] == ANTJU:
                    miners[0] = {**ANTJU, "endpoint": origin}
                elif address not in {miner["address"] for miner in miners}:
                    miners.append({"name": entry["name"], "address": address, "endpoint": origin})
        except (ValueError, OSError):
            pass
    return miners


class Direct:
    def __init__(self, chat, error, parse_identity):
        self.chat, self.error = chat, error
        self.miners = configured_miners(chat.ledger.path.with_name("direct-miners.json"), parse_identity, error)
        self.node = shutil.which("node")
        self.available = bool(self.node and (BASE / "node_modules/@flop-labs/sdk/package.json").is_file())
        self.job = None

    def active(self):
        return bool(self.job and self.job["phase"] in {"checking", "review", "signing", "submitted", "opened", "verified"})

    def snapshot(self):
        return {"available": self.available, "miners": self.miners,
                "job": {k: v for k, v in self.job.items() if k not in {"process", "payload", "row"}}
                if self.job and self.job["address"] == (self.chat.account or {}).get("address") else None}

    def prepare(self, body):
        c = self.chat
        with c.lock:
            source = c.direct_candidate
            if not self.available:
                raise self.error("DIRECT_UNAVAILABLE", 503)
            if not source or body.get("request_id") != source["id"] or not c.direct_allowed(source):
                raise self.error("DIRECT_NOT_ALLOWED", 409)
            miner = next((m for m in self.miners if m["address"] == body.get("miner")), None)
            address = c.account["address"]
            if not miner or miner["address"] == address:
                raise self.error("DIRECT_MINER_INVALID")
            charge = c.decimal_cost(ESCROW + FEE_CAP)
            if charge > source["cap"] or charge > c.request_cap or c.session_commitment() + charge > c.session_cap:
                raise self.error("SESSION_LIMIT", 403)
            self.job = job = {"id": "direct-" + source["id"][5:], "source_id": source["id"],
                              "address": address, "miner": miner, "phase": "checking"}
            worker_input = {"address": address, "miner": miner["address"], "endpoint": miner["endpoint"],
                            "model": MODEL, "messages": source["messages"], "maxTokens": min(source["tokens"], 48),
                            "escrow": str(ESCROW), "fee_cap": str(FEE_CAP)}
            threading.Thread(target=self.run, args=(job, worker_input), daemon=True).start()
            return c.snapshot()

    def sign(self, body):
        with self.chat.lock:
            job = self.current(body, "review")
            job["phase"] = "signing"
            return {"payload": job["payload"], "preview": job["preview"]}

    def current(self, body, phase):
        job = self.job
        if (not job or job["id"] != body.get("id") or job["phase"] != phase
                or job["address"] != (self.chat.account or {}).get("address")
                or job["preview"]["expires_at"] <= time.time() * 1000):
            raise self.error("DIRECT_PREVIEW_EXPIRED", 409)
        return job

    def submit(self, body):
        c = self.chat
        with c.lock:
            job = self.current(body, "signing")
            signature = body.get("signature")
            if not isinstance(signature, str) or not re.fullmatch(r"0x(?:00)?[0-9a-fA-F]{128}", signature):
                raise self.error("SIGNATURE_INVALID")
            if job["id"] in c.ledger.rows or c.unresolved():
                raise self.error("RECONCILE_REQUIRED", 409)
            preview = job["preview"]
            row = {"request_id": job["id"], "gateway_request_id": job["source_id"], "route": "direct",
                   "address": job["address"], "model": MODEL, "miner": job["miner"]["address"],
                   "channel_id": preview["channel_id"], "scan_from": preview["scan_from"],
                   "created_at": int(c.clock() * 1000), "state": "unknown", "local_state": "sending",
                   "response_received": False, "reserved_spend": float(c.decimal_cost(ESCROW)),
                   "settled_spend": None, "settled_spend_raw": None, "terminal_event": None,
                   "max_cost_flop": str(c.decimal_cost(ESCROW + FEE_CAP)), "max_tokens": preview["max_tokens"],
                   "opening_fee_estimate_raw": preview["fee"], "opening_fee_cap_raw": str(FEE_CAP)}
            c.ledger.rows[job["id"]] = row
            try:
                c.ledger.save()  # Required before the worker can broadcast.
            except OSError:
                c.ledger.rows.pop(job["id"])
                raise
            job.update(row=row, phase="submitted")
            job["process"].stdin.write(json.dumps({"signature": signature}) + "\n")
            job["process"].stdin.flush()
            return c.snapshot()

    def cancel(self, body):
        with self.chat.lock:
            job = self.job
            if (job and job["id"] == body.get("id") and job["phase"] in {"checking", "review", "signing"}
                    and job["address"] == (self.chat.account or {}).get("address")):
                job["phase"] = "cancelled"
                if job.get("process"):
                    job["process"].terminate()
            return self.chat.snapshot()

    def start_process(self):
        # The wallet's long-lived key and the gateway bearer never reach this child.
        names = ("SYSTEMROOT", "WINDIR", "PATH", "TEMP", "TMP", "LANG")
        env = {name: os.environ[name] for name in names if name in os.environ}
        return subprocess.Popen([self.node, str(BASE / "direct_worker.mjs")], cwd=BASE, env=env,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, encoding="utf-8", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def run(self, job, worker_input):
        process = None
        timer = None
        try:
            process = self.start_process()
            with self.chat.lock:
                if self.job is not job or job["phase"] == "cancelled":
                    return
                job["process"] = process
            process.stdin.write(json.dumps(worker_input) + "\n")
            process.stdin.flush()
            for line in process.stdout:
                event = json.loads(line)
                with self.chat.lock:
                    if job["phase"] == "cancelled":
                        break
                    phase = event["phase"]
                    if phase == "review":
                        job.update(phase=phase, preview=event["preview"], payload=event["payload"])
                        timer = threading.Timer(65, self.expire, args=(job,))
                        timer.daemon = True
                        timer.start()
                    elif phase == "opened":
                        job.update(phase=phase, opening_tx=event["tx"])
                        job["row"]["opening_tx"] = event["tx"]
                        self.chat.ledger.save()
                    elif phase == "verified":
                        job.update(phase=phase, reply=event["reply"])
                        job["row"]["response_received"] = True
                        self.chat.ledger.save()
                    elif phase == "settled":
                        self.apply_final(job["row"], event)
                        job["phase"] = phase
                    elif phase == "not_submitted":
                        code = event.get("error_code")
                        if code in {"DIRECT_RUNTIME_UNSUPPORTED", "DIRECT_NETWORK_MISMATCH"}:
                            job["error_code"] = code
                            runtime = event.get("runtime")
                            if type(runtime) is int and 0 <= runtime <= 2**32 - 1:
                                job["runtime"] = runtime
                        if job.get("row"):
                            job["row"].update(state="released", local_state="not_submitted")
                            self.chat.ledger.save()
                        job["phase"] = "stopped"
        except (OSError, ValueError, KeyError):
            pass
        finally:
            if timer:
                timer.cancel()
            if process:
                if process.poll() is None:
                    process.kill()
                process.wait()
                process.stdin.close()
                process.stdout.close()
            with self.chat.lock:
                if job["phase"] not in {"settled", "cancelled", "stopped"}:
                    row = job.get("row")
                    job["phase"] = "reconcile" if row else "stopped"
                    if row:
                        row["local_state"] = "needs_receipt"
                        self.chat.ledger.save()
                job.pop("payload", None)
                job.pop("process", None)

    def expire(self, job):
        with self.chat.lock:
            if job["phase"] in {"review", "signing"}:
                job["process"].terminate()

    def apply_final(self, row, event):
        phase, tx = event["phase"], event["tx"]
        if not isinstance(tx, str) or not HASH.fullmatch(tx):
            raise ValueError("invalid finalized transaction")
        update = {"state": phase, "local_state": "reconciled", "terminal_event": tx}
        if phase == "settled":
            paid, burned = int(event["miner_paid_raw"]), int(event["burned_raw"])
            if not 0 <= paid <= ESCROW or not 0 <= burned <= ESCROW - paid:
                raise ValueError("invalid finalized payment")
            update.update(settled_spend_raw=str(paid + burned), miner_paid_raw=str(paid),
                          burned_raw=str(burned))
        row.update(update)
        self.chat.ledger.save()

    def reconcile(self, body):
        c = self.chat
        with c.lock:
            ident = body.get("id")
            if not isinstance(ident, str):
                raise self.error("DIRECT_NOT_ALLOWED", 409)
            row = c.ledger.rows.get(ident)
            if (not self.available or self.active() or not row or row.get("route") != "direct"
                    or row["address"] != (c.account or {}).get("address")):
                raise self.error("DIRECT_NOT_ALLOWED", 409)
            if row["state"] in {"settled", "released"}:
                return c.snapshot()
            if not isinstance(row.get("channel_id"), str) or not HASH.fullmatch(row["channel_id"]):
                raise self.error("RECONCILE_REQUIRED", 409)
            job = {"action": "reconcile", **{k: row[k] for k in ("address", "miner", "channel_id", "scan_from")}}
            try:
                with self.start_process() as process:
                    try:
                        output, _ = process.communicate(json.dumps(job) + "\n", timeout=35)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.communicate()
                        raise
                event = json.loads(output)
                if event["phase"] in {"settled", "released"}:
                    self.apply_final(row, event)
                    if self.job and self.job["id"] == ident:
                        self.job["phase"] = event["phase"]
                elif event["phase"] == "pending":
                    row.update(chain_state=event["chain_state"], scan_from=event.get("scan_from", row["scan_from"]))
                    c.ledger.save()
                else:
                    raise ValueError
            except (OSError, ValueError, KeyError, subprocess.TimeoutExpired):
                raise self.error("RECONCILE_REQUIRED", 409) from None
            return c.snapshot()
