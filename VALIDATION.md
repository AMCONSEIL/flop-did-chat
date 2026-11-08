# Validation — 0.1.0

Checked locally on Windows, Python 3.11 / cryptography 48.0.0 / Node 24.

## Automated checks

- Initial checks: 23 Python tests passed: RFC8032 Ed25519 signatures and Talisman Bytes wrapping, DID/account checks, wrong identity and genesis rejection, single-use challenges, two-turn chat, exact raw settlement accounting, duplicate/id-conflict rejection, 429/released handling, cooldown persistence, timeout/404 recovery across restart, pending settlement locking, spend caps, explicit limits, scope/model checks, context bounds, failed introspection, pre-submit intent persistence, concurrency, previous receipt reconciliation, unknown settlement, CSRF/Origin/Host checks, static-file isolation and credential redaction.
- Initial checks: 6 JavaScript core tests passed: unknown versus zero cost, exact raw formatting, reservations versus settled usage, successful context only, send gating and the browser-history whitelist.
- Python and JavaScript syntax checks passed.
- Pinned isolated Python environment installed with hashes; pip check passed.

## Browser acceptance

The real local app loaded the live public model catalog with only Qwen2.5-0.5B advertised. FR and EN screens were checked, with no browser warnings/errors. The desktop layout was corrected so the composer remains inside the viewport.

A separate local server on port 50511 used only a public RFC8032 test identity and a fake gateway. Browser checks covered:
- account selection and display of the challenge before signing;
- locally verified wrapped Ed25519 fixture signature;
- unauthorized model disabled after enrollment;
- explicit local budget change;
- two successful simulated turns, 36 reported fixture tokens, 0.5 fixture FLOP settled;
- prompt HTML displayed literally, no injected image elements;
- third simulated request refused with 429 and released reservation, unknown settlement preserved, no additional settled cost, send disabled during cooldown.

These are **offline simulation results, not live FLOP payments**. The fixture explicitly labels its page OFFLINE TEST. No real wallet was connected and no inference was submitted while developing this app.

The browser viewport override did not apply in this environment; mobile styles exist, but mobile acceptance is not confirmed. Desktop viewport verified at 1280 × 720 without page overflow.

## Remaining real acceptance

Personal Talisman connection has since been verified (see the real test below). A successful live model reply remains unverified; before stable release, verify the reply, original request ID, usage and subsequent receipt, then a second turn preserving context within user-selected caps.

A working interface does not resolve the upstream 429 incident. Enrollment rotates a bearer without renewing the existing account allowance or expiry.

## Scope and release

Only the new flop-did-chat directory was created. The original personal one-shot tool and did-to-talisman were preserved and checked. No miner infrastructure was accessed or modified during this implementation.

Author attribution is DID metadata only. There is no signed manifest for this version. Repository: https://github.com/AMCONSEIL/flop-did-chat. Git history identifies the exact source revision; no signed source manifest is claimed.

## Plain UI revision — 3 November 2026

23 Python tests and 6 JavaScript tests passed again; JavaScript syntax checked. The live local UI was checked in French and English at 1280 x 720, with no horizontal overflow. Settings opens/closes with an explicit used-or-pending limit counter and explanation; it is hidden by default. Wallet dialog wording is shorter and retry distinguishes no shared accounts from non-Ed25519 accounts. No authenticated inference, budget increase or wallet signature occurred during this revision. Actual Talisman sharing remains unverified.

## Talisman candidate regression — 3 November 2026

24 Python tests and 8 JavaScript tests passed. Added coverage for SS58 candidates injected with sr25519 metadata, malformed/EVM filtering and duplicate addresses, plus rejection of a sr25519 signature-type prefix before upstream enrollment. Browser simulation on isolated port 50511 now injects the public RFC8032 Ed25519 account with sr25519 metadata, mirroring Talisman getInjectedAccountType. Account selection, challenge display and wrapped Ed25519 login all succeeded. No browser errors. No real user signature or gateway inference submitted; actual personal wallet acceptance remains pending.

Reference: https://github.com/TalismanSociety/talisman/blob/dev/apps/extension/src/core/domains/accounts/helpers.ts (getInjectedAccountType). Only client discovery changed; actual Ed25519, expected DID, genesis and account checks remain mandatory on the server.

## First real personal chat request — 3 November 2026 (UTC-4)

The user connected the existing personal Talisman account and manually sent a prompt. The server confirmed the expected personal DID and connected state. The UI displayed the upstream error BrokerOverloadedError: gateway channel pool is full. The exact original request ID is retained only in ignored local acceptance evidence, not required in the generic release.

The receipt was independently refreshed on 4 November at 00:00:42 UTC: response_status 429, state released, reserved_spend 0.306, settled_spend and settled_spend_raw null, channel_id and terminal_event null. No unresolved request remained. This proves a released reservation and no reported settled amount in the observed receipt; unknown settlement is not represented as a proven zero. No successful inference or LLM answer was obtained. The verification submitted no new inference.

Real Talisman authentication is now verified for this account. Successful live inference acceptance remains blocked by the gateway response; the user subsequently authorized publication as an experimental community test, with this failure disclosed. No professional account or infrastructure was accessed.

## User-selected spending caps — 3 November 2026 (UTC-4)

26 Python and 8 JavaScript tests passed (34 total). Explicit request/total settings of 2.5/10 are accepted; defaults remain 0.9/0.9. Settings make no inference call. The chosen request cap is enforced server-side, and invalid, zero, non-finite, underflowed or inconsistent values are rejected atomically. Receipt locks, quota and total-budget checks remain. The artificial 0.9 per-request and 5 total maxima were removed from HTML, JavaScript and Python.

Offline browser fixture verified applying 2.5/10 and retaining those values after page reload, with no max attribute on either spending field. No real wallet connection or inference was made during this cap change. The actual personal chat was restarted only after checking no unresolved receipts and zero local commitment; its journal remained byte-for-byte identical. Actual settings remain 0.9/0.9 and the user must reconnect Talisman. The account allocation was not renewed.

## Public test publication

The user authorized sharing this experimental client despite the observed upstream 429. The English and French README disclose the successful personal wallet authentication and the missing successful live inference. Latest validation: 26 Python tests and 8 JavaScript tests, 34 total. This is a public test, not a stable or audited release. Authorship is personal DID metadata; no signed source manifest is claimed. Runtime journals, evidence, screenshots, environments and credentials are excluded from Git.

## 0.2.0 direct fallback

Offline coverage verifies gateway priority, confirmed release, ambiguous receipts, expired access, local signed login, durable intent before broadcast, duplicate protection and settled cost accounting. A read-only Devnet check produced a live unsigned NurseryPool quote and rediscovered the finalized settlement of the earlier standalone prototype. On November 6, 2026 (UTC−4), the user connected their existing account with Talisman. The gateway returned HTTP 403 \`devnet_enrollment_expired\`. In FLOP DID Chat v0.2.0, the user selected NurseryPool, reviewed the fees, and signed the opening of a direct channel for Qwen2.5-0.5B. The client verified and displayed a reply. Its wording was a generic refusal, so this test verifies the direct transport and settlement. Response quality was outside the test.

The [finalized settlement](https://explorer.devnet.flop.network/transactions/0x510061602e7524880913177efe61a2cb48171117058c00904db708a0494ee0b6) records 0.198 FLOP paid to NurseryPool from a 0.2 FLOP Devnet reserve. Opening fees were quoted separately. The client displayed \`Settled\` and cleared the pending receipt guard.

AntJu is listed separately. A read-only preparation checked the named miner and produced an unsigned fee quote through its temporary public tunnel. The integrated acceptance test above used NurseryPool.

## 0.2.1 runtime compatibility diagnostic — 7 November 2026

35 Python and 12 JavaScript tests pass (47 total). Coverage includes SDK-supported versions beyond the old 1014003 pin, a rejected hole inside the supported range, rejection of 1014014, genesis/denomination checks, safe error redaction and stopping before signature without a paid call or journal row. Syntax checks and `git diff --check` pass.

A read-only invocation of the actual Node worker against the public Devnet RPC returned `not_submitted`, `DIRECT_RUNTIME_UNSUPPORTED`, runtime `1014014`. The official npm `latest` tag still resolves to SDK `0.4.0`; its published explicit compatibility list ends at 1014011. No dependency or compatibility list was patched. No miner call, signature, inference or new settlement was performed in this release. A compatible official SDK and a bounded real-user acceptance test remain necessary.

The local chat journal was preserved byte-for-byte and remaining process caps retained. Local restart requires browser refresh and reconnecting the same Talisman account; it does not renew the expired gateway allowance. No AntJu VM service was modified or restarted.

## 0.2.2 official SDK update — 8 November 2026

Pinned the official npm `@flop-labs/sdk` 0.5.1 distribution, published at 2026-11-08T16:13:56.615Z. The downloaded archive's SHA-512 matches the npm registry and lockfile; archive SHA-256 is `edba52d4c3311b24365d3817ee85dcb0047493c38a3df18716d398195bde676f`. Its packaged changelog and unchanged explicit runtime list admit 1014014. The general upgrade guide still describes an older release; compatibility was checked in the actual published package rather than inferred from that guide or the version number. The lockfile changes only the root package and the required FLOP SDK/client/contracts packages. Installation used `npm ci --ignore-scripts --no-audit --no-fund`.

35 Python tests and 12 JavaScript tests pass (47 total). Python tests were rerun outside the Windows sandbox because its temporary-file permissions prevented the fixtures' atomic renames; no application change was made to bypass atomic persistence. JavaScript syntax checks pass. Coverage accepts supported 1014014/1014011 and rejects unsupported 1014015/1014006 through the installed SDK's unchanged gate, while preserving network, denomination and diagnostic-redaction checks.

A read-only smoke check of the installed package at 2026-11-08T23:03:30Z passed all five companion-module imports used by the direct worker, then the actual chat network gate against live Devnet: specVersion 1014014, 18 decimals, expected genesis, finalized block 3252662. No signer was created, no miner was contacted and no inference or transaction was submitted.

The existing force-open path and its SLA/signature guards remain unchanged. A successful Standard-channel standalone experiment does not qualify this chat's direct path. A bounded, explicitly signed real-user test is still necessary to validate a reply, usage and a matching finalized payment with this version. No new inference or payment is claimed by this release.

The original tracked source and Git history were backed up before installation. The local chat was already stopped with an orphaned server lock. Its journal and lock are preserved byte-for-byte, and the application is not automatically restarted; restarting must not renew a budget or unresolved operation. No personal allowance, receipt, standalone helper or professional AntJu service was changed by this SDK update.
