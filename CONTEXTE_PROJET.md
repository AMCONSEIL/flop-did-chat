# Project context

## Goal and scope

Personal community chat for existing Ed25519 DID owners using the FLOP devnet gateway first and an explicitly approved direct session as a fallback. User-requested features: Talisman connection, model selection, chat history and usage tracking. English/French UI. Author attribution only through the personal public DID:
did:key:z6Mkt3DNtpGBNh1KHYwLQEk6QtCcJ7vVaRPze1SU7MyhFMVD

The professional miner project, its account, funds, signer, VM and automation are strictly out of scope. Do not reuse them for this client.

## Layout

- flop_chat.py: localhost-only HTTP server, DID/SS58 and Ed25519 validation, gateway adapter, per-request identity ledger, budgets and receipt reconciliation.
- web/: vanilla HTML/CSS/JS; no third-party frontend scripts, fonts or analytics.
- tests/: offline public cryptographic fixtures and a separately labelled browser fixture.
- .local/: ignored, persistent public request metadata and process lock; never private keys or bearer credentials.
- validation.local/: ignored test reports and screenshots.
- README.fr.md / README.md / SECURITY.md / VALIDATION.md: usage, boundaries, actual validation.

No wallet files, seed inputs, EVM linking, miner registration, faucet requests, remote deployments or new identity generation.

## Current delivery

Version 0.2.0 local test. Node.js 22+ and the pinned npm dependencies enable direct mode. Generic launchers use port50510. The private launch for this user adds --expected-did with the existing personal DID and --reconcile-request for the latest failed personal request. Those flags contain only public values. No browser bearer, no imported PEM.

Defaults: 48 output tokens, 0.9 FLOP per request, 0.9 FLOP local process budget. Users explicitly choose positive finite per-request and total caps; no arbitrary 0.9/5 maximum remains. Both default to0.9, settings changes are atomic and server-enforced, and no implicit budget increase occurs. The per-request cap must fit the chosen total; output cap1024 remains subject to the catalog. The original server allowance and expiry remain authoritative and are never extended by re-enrollment.

Never retry inference automatically. Persist request_id and fingerprint before sending. Unknown outcomes and missing receipts block later sends; preserve the same original identity when reconciling. Local ledgers are not independent chain-finality proofs. Unknown values must never silently become zero.

## Rollback and release

This is a new isolated directory; previous tools remain unchanged. Stop only this local chat process to roll back. Preserve .local/ledger.json while outcomes are unresolved; do not delete a journal or lock to force a second owner.

The original gateway validation passed 34 automated tests and encountered an upstream 429. The direct path through NurseryPool subsequently passed a live Talisman and settlement test. See VALIDATION.md for the independent scope of each check. The user explicitly authorized public experimental sharing with disclosure. No signed source manifest exists. Do not imply the previous importer's signature covers this version.

## UI revision — 3 November 2026

User requested a much plainer UI: neutral colors, short FR/EN copy, no welcome slogans or suggestion cards. Local budget counter moved into Settings with explicit explanation; backend limits remain unchanged. Wallet errors now distinguish no shared accounts from shared accounts filtered for a non-Ed25519 type. Authorization retry resets stale account/challenge UI. No inference or wallet signing during this UI revision.

Language default: English on first visit (independent of browser language); FR toggle available. Explicit language preference remains saved locally. Invalid or unavailable storage falls back to English.

## Talisman account discovery fix

Talisman dev core/domains/accounts/helpers.ts getInjectedAccountType maps all SS58 accounts to sr25519 metadata, including imported Ed25519 keys. Do not filter candidates solely by injected type. Discover SS58 candidates, then retain strict server checksum, expected-DID and actual Ed25519 signature checks. Never infer the signing curve from SS58 alone. The offline browser fixture now emits sr25519 metadata with the public Ed25519 fixture key to reproduce this case.

## Direct fallback — 6 November 2026

Use the same Talisman identity. A proven gateway refusal with a released receipt or a blockage before submission can offer a local configured miner. Direct spends the Devnet wallet balance, with a separate signed opening, a 0.2 FLOP reserve and a 0.02 FLOP ceiling on the opening fee estimate. Journal the channel candidate before sending the signature to the SDK worker. Keep unknown channels locked across restarts. Check their finalized terminal event without triggering a write. Use the existing opt-in policy for storing message history. AntJu and NurseryPool are selectable miners. AntJu's public tunnel is temporary and can be replaced via the local miner configuration while retaining its public SS58 address. The client uses the signed wallet identity as the caller, and each miner is a separate provider.

## Historical gateway acceptance status

Personal Talisman login verified; first real manually sent chat prompt failed with upstream 429 overloaded/channel pool full. Receipt refreshed: released reservation 0.306 FLOP, settled amount null, no unresolved request. Exact request ID and public receipt are in ignored validation.local/personal-live-chat-receipt.public.json. No automatic retry. Public experimental publication is now authorized, with the observed failure disclosed. Do not reuse the earlier one-shot test lock or the professional miner account to retry.

## Runtime compatibility diagnostic — 7 November 2026

Direct preparation now uses the pinned SDK explicit supported-spec list instead of a single hardcoded 1014003. Live Devnet reports 1014014, absent from published SDK 0.4.0: direct operations remain blocked before miner contact or signature. A compatible official release is required; do not patch the SDK list to bypass this gate. Only allowlisted runtime/network diagnostics reach the browser, never raw RPC errors. Existing budgets, ledger, receipts and signature guards are preserved.
