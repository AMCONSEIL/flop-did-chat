# Validation · Testnet 0.3.0

## Public observations on November 27, 2026 (UTC)

| Check | Observation |
| --- | --- |
| Gateway catalogue, 12:33 | HTTP 200 with eight text models, including qwen/qwen3-4b, qwen/qwen3-8b and qwen/qwen3-14b. |
| Wallet enrollment challenge, 12:33 | HTTP 404. The application also exercised its actual catalogue parser and prepared a local login challenge for a synthetic public address. |
| Native RPC, 12:43 | Block-zero hash 0x918abd58fb16306b30ef3886514cfaebffecb4de43e82b6f8ec4795c43cfd800, runtime 1014039, SS58 42, 18 decimals and FLOP. A finalized system.account lookup for the synthetic address returned zero. |
| Faucet, 12:43 | /chain identified the same genesis. /limits reported daily_cap_reached, remainingFlop 0, agent grant 10, cooldown 86400 seconds and rolloverRequiresSpend true. |
| Opening quote, read-only | The live metadata exposed the nine computeChannel.forceOpen arguments. An unsigned synthetic call decoded through the registry and paymentInfo returned 8436141525000000 raw units. This estimate applies to the fixture at the time of the query. |

[Gateway catalogue](https://gateway.testnet.flop.network/v1/models) · [RPC](https://testnet.flop.network/) · [Faucet limits](https://faucet.flop.network/limits) · [Faucet chain](https://faucet.flop.network/chain)

## Reproduce the offline checks

Use Node.js 24.22.3 and Python with the dependencies installed.

~~~sh
npm ci --ignore-scripts --no-audit --no-fund
python3 -m unittest discover -s tests -v
node --test tests/*.test.mjs
git diff --check
~~~

Tests cover local HTTP boundaries, both signature schemes, challenge reuse and address locks, grant outcomes and durable timeout handling, gateway fallback, canonical models, output and spending limits, SSRF checks, signed model proofs, runtime compatibility, the real SDK forceOpen handoff, receipt reconciliation and EN/FR labels. All signing fixtures use synthetic keys or the published RFC8032 test vector.

SDK 0.13.1 exposes computeChannel.runDirectSession and its supported runtime lists at the package root. Its assertSupportedSpecVersion function lives in dist/runtime-compatibility.js. The integration uses modules in this exact locked distribution. Recheck the imports and protocol whenever updating the SDK. The real SDK builds its ephemeral key and forceOpen SLA; the external wallet's signPayload authorizes the opening. The SDK verifies the answer and cooperative settlement against finalized events. [Published SDK](https://www.npmjs.com/package/@flop-labs/sdk/v/0.13.1) · [Official upgrade guide](https://docs.flop.network/docs/upgrade)

The local run passed 44 Python and 18 Node tests. Two offline Chromium flows used a simulated Talisman account. One connected, read the closed faucet, changed language and received a mock gateway response. The other connected through the 404 fallback, signed a mock grant and verified the explorer link and duplicate-submission guard. Neither browser flow contacted a live miner. Read-only finalized storage at block 246599 also confirmed the miner activity, calibration and model registry fields used by preflight.

## User acceptance still required

1. On Windows, run the installer and launcher. Connect the intended Talisman account and compare the public DID/address and signature scheme. Repeat with the other scheme. Check EN and FR.
2. When the faucet is open and the account eligible, review one grant challenge. Compare the resulting transaction and finalized balance. A returned included status alone does not prove finality.
3. Configure an operator-confirmed miner. Select its exact served model and review the quote for 1200 seconds, 0.05 FLOP escrow and 256 output tokens. Reject the first quote to confirm cancellation; then approve one bounded session if intended.
4. Verify the reply, channel ID, settled Gn, amount and transaction hash against the explorer. Verify gateway enrollment and one gateway receipt when the public service enables enrollment.

Public observations and offline results establish neither a completed Talisman session nor a Windows installation or live gateway enrollment.
