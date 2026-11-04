# Security and boundaries

- Text-only chat on one fixed FLOP devnet HTTPS API origin. No arbitrary URL proxy, redirects, tools, uploads or shell execution.
- Server binds only to 127.0.0.1. Strict Host + Origin + unpredictable per-process CSRF token protect mutations. No CORS access.
- Private-key material is never requested or read. Ed25519 signatures are checked locally against the DID/account and original challenge; raw and Talisman Bytes wrappers are supported.
- API credentials exist only in server process memory. They never reach the browser, local history, ledger, logs or child processes.
- API responses and model output are treated as untrusted text. No HTML renderer, external images, remote scripts, fonts or analytics.
- Persistent request IDs and fingerprints prevent automatic duplicate submission. Unknown outcomes require receipt reconciliation. 404 is not evidence of non-execution.
- Spending is bounded locally and by the remote grant. Local process limits reset on server restart; the remote allowance does not. Do not treat a local guard as a replacement for a server-side spending cap.
- Journal files contain public identifiers and consumption metadata only. Clear-text conversation history is opt-in. Private directory permissions follow the user's machine configuration.
- This app reads only the gateway's retained credential ledger and cannot prove independently finalized settlement, recover an expired bearer, or guarantee access to lost records.
- Separate application and data directory from other identities/projects. This app does not operate miner infrastructure or request sponsorship/faucet grants.
- The generic product supports existing did:key Ed25519 accounts only. Non-Ed25519 or non-exportable identities require a separately reviewed adapter.
- Real wallet, browser and gateway user tests remain required. A malware-compromised host or browser extension is outside the guarantees of this local program.
