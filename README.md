# FLOP DID Chat

**Local test version 0.2.2 · English / Français · Talisman · Ed25519**

Local chat for FLOP Devnet. The gateway is tried first, with a direct session to a selected miner offered when a confirmed block prevents completion.

**Current compatibility (November 8, 2026).** Version `0.2.2` pins the official npm SDK `0.5.1`, whose unmodified compatibility list explicitly accepts the live Devnet runtime `1014014`. Unsupported versions, the network identity and denomination remain checked. Offline and read-only checks do not validate a paid session: a new bounded Talisman user test is still required. The successful NurseryPool test below is historical. A separate Standard-channel experiment does not validate this chat's existing force-open path. See the [official upgrade guide](https://docs.flop.network/docs/upgrade).

> **Devnet validation.** The v0.1.0 gateway route returned HTTP 429 and a released receipt. With the gateway allowance expired, FLOP DID Chat v0.2.0 received a verified direct reply from NurseryPool. The [finalized transaction](https://explorer.devnet.flop.network/transactions/0x510061602e7524880913177efe61a2cb48171117058c00904db708a0494ee0b6) records 0.198 Devnet FLOP paid to the miner. This integration remains experimental. See [validation details](VALIDATION.md) and the [gateway incident](https://github.com/flop-labs/network/issues/31).
>
> Community feedback is welcome. A real user test is still required before relying on this experimental client.

Author DID: **did:key:z6Mkt3DNtpGBNh1KHYwLQEk6QtCcJ7vVaRPze1SU7MyhFMVD**

[Full French guide](README.fr.md) · [Attribution](IDENTITY.md) · [Security](SECURITY.md)

## Before you start: your DID in Talisman

**You need a Talisman account using the same Ed25519 key as your existing `did:key` identity.** Installing Talisman or creating a new wallet does not automatically connect it to an existing DID.

To prepare that account, follow our previous project: **[did-to-talisman — import your existing DID into Talisman](https://github.com/AMCONSEIL/did-to-talisman)**. It includes the French/English tutorial and local conversion tool for a compatible encrypted PEM backup. If that account is already imported, use it directly.

Each user connects **their own DID and wallet**. The author DID shown in this repository identifies the contribution; it is not the account other users should connect.

## Start on Windows

1. Install Python 3.11+ and Talisman from its official website.
2. Run **INSTALLER_WINDOWS.cmd**, then **LANCER.cmd**.
3. Open **http://127.0.0.1:50510/** in the browser with Talisman.
4. Connect an existing **Ed25519** account, review the official challenge, then sign in the extension.
5. Choose an authorized model and send a message. Connecting does not submit inference.

Use the FR / EN button to switch languages. To prepare an existing DID in Talisman, see [did-to-talisman](https://github.com/AMCONSEIL/did-to-talisman). A public DID cannot recover its private key. This app never asks for a seed, wallet file or password.

## Direct miner fallback

Direct mode requires **Node.js 22+**. In the chat directory, install the pinned dependencies with `npm ci --ignore-scripts --no-audit --no-fund`, then restart the server. Gateway mode also works with the Python installation alone.

The chat tries the gateway when access is available. If access is blocked before submission, or an HTTP 429/503 refusal has a released receipt with no payment or reply, the chat offers a miner for that message. An uncertain outcome requires receipt reconciliation. The chat displays the miner, model, 0.2 devnet FLOP escrow and estimated opening fee before Talisman signs. Direct sessions use the wallet's devnet balance. Opening fees can remain payable if escrow is refunded. The local budget accounts for up to 0.02 FLOP in estimated opening fees per channel.

Direct mode is limited to Qwen2.5-0.5B and 48 output tokens. The selected miner receives the conversation context. AntJu and NurseryPool are listed. AntJu uses a temporary HTTPS tunnel. If the operator rotates it, supply the new HTTPS endpoint locally with the same AntJu address. To add an opted-in miner, create `.local/direct-miners.json` with a list of objects shaped like `{"name":"Name", "address":"MINER_SS58", "endpoint":"https://miner.example"}`. Confirm the HTTPS origin and SS58 address with the operator before adding it. Restart the server to load the list.

An uncertain channel blocks further sends. **Check receipts** reads finalized state and scans for settlement or refund events in batches of 64 blocks. A missing channel or event still needs reconciliation. Recovery actions that write to the chain are separate and manual.

## Spending and model access

Models come from the live gateway catalog and must also be allowed by your credential. Unauthorized models stay disabled. The initial catalog check on November 3, 2026 listed Qwen2.5-0.5B only.

Default: **48 output tokens, at most 0.9 FLOP per request, local process budget 0.9 FLOP**. Users choose the per-request and total chat caps in Settings, without an arbitrary app maximum. Values must be positive and finite; the per-request cap must fit within the total cap. The server enforces the selected values. Output supports up to 1,024 tokens within the advertised model limit. Settings never issue or renew server credits. Successful conversation history is sent as context and contributes to usage.

The API quota is the server-reported value, not your native wallet balance. Settled, reserved, reported token usage and local budget commitment are separate. Unknown values stay unknown. Exact raw amounts are preserved; legacy floating-point amounts are gateway observations. A released reservation is not a confirmed zero settlement. Gateway receipts are not independent on-chain finality proofs; a pooled terminal event is not a separate transaction for every request.

## Recovery and privacy

Every send persists a request ID and content fingerprint before submission. Duplicate clicks cannot replay paid work. Unknown, missing, reserved or estimated receipts block further sends until reconciled. Receipt refreshes are read-only. No automatic inference retries. A 429/503 enforces a local cooldown.

Re-enrolling the same account rotates access only; it never renews allowance, spend limits or expiry. Never create another wallet or claim another faucet grant to bypass a limit.

Private keys stay in Talisman, and API credentials stay in server memory. History is in browser memory by default. Opting into local history stores prompts and answers in clear text in that browser, without credentials. Clearing conversations does not erase remote work or receipts.

**.local/** stores only public identities, request IDs, content fingerprints, limits, counters and receipts. No prompts, outputs, private keys or login signatures. Content fingerprints are not guaranteed anonymization for predictable prompts. Preserve this journal across restarts; do not delete it to bypass recovery locks. The local process budget resets when the server restarts; server allowance does not.

The server binds to **127.0.0.1** only. Never expose it to the Internet. An optional **--expected-did YOUR_PUBLIC_DID** flag locks the local instance to your personal identity; **--reconcile-request PUBLIC_REQUEST_ID** checks an existing receipt before permitting new work.

## Test status

Offline tests: **python -m unittest discover -s tests -v** and **node --test tests/core.test.mjs**. Only public RFC8032 cryptographic fixtures are used.

**The signed direct path through NurseryPool has been verified on Devnet.** Live gateway completion and multi-turn validation remain open. This project version has no signed authorship manifest yet; the author DID is metadata, not a signed release claim.

Independent community application. Devnet has no monetary value, rewards or airdrop weight.

The local limit counter and caps are under **Settings**, below the message box. The initial 0.9 FLOP limit is an app precaution for the first test, not a FLOP requirement.
