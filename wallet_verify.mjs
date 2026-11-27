// Verify public wallet data only; the wallet never exports a signing key.
import { cryptoWaitReady, sr25519Verify, ed25519Verify } from "@polkadot/util-crypto";
import { hexToU8a, u8aWrapBytes } from "@polkadot/util";
import { readFileSync } from "node:fs";

export function walletSignature(type, publicKey, payload, signature, wrap = false) {
  if (!["ed25519", "sr25519"].includes(type) || !/^0x(?:[0-9a-f]{2}){64,65}$/i.test(signature)) return false;
  const raw = hexToU8a(signature);
  const prefix = type === "ed25519" ? 0 : 1;
  if (raw.length === 65 && raw[0] !== prefix) return false;
  const check = prefix ? sr25519Verify : ed25519Verify;
  try { return check(wrap ? u8aWrapBytes(payload) : payload, raw.slice(-64), publicKey); }
  catch { return false; }
}
if (process.argv[2] === "--verify") {
  await cryptoWaitReady();
  const { type, publicKey, message, signature, wrappedOnly } = JSON.parse(readFileSync(0, "utf8"));
  const payload = new TextEncoder().encode(message);
  process.exitCode = (walletSignature(type, publicKey, payload, signature, true)
    || (!wrappedOnly && walletSignature(type, publicKey, payload, signature))) ? 0 : 1;
}
