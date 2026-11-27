# FLOP DID Chat 0.3.0 · Testnet

Chat with a Testnet model through the public gateway or a miner you choose. Talisman holds your sr25519 or Ed25519 wallet key. The English/French interface runs on your own computer. This version has been tested offline and against public read endpoints. A real Talisman grant and settled Testnet chat still require user validation. [Validation](VALIDATION.md) · [Français](README.fr.md) · [Author DID](IDENTITY.md)

## Start

Install Python 3.11 or later, Node.js 24 with npm, and the Talisman browser extension. On Windows run **INSTALLER_WINDOWS.cmd**, then **LANCER.cmd**. On Linux or macOS run the following in the project directory.

~~~sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements.lock.txt
npm ci --ignore-scripts --no-audit --no-fund
python flop_chat.py --open-browser
~~~

Open the printed loopback URL in the browser with Talisman. Choose **Connect Talisman**, select your account and signature scheme, then review and sign the login message. For an imported historical DID, select Ed25519 if the extension reports the wrong scheme. You can lock your installation with either or both of `--expected-address <SS58>` and `--expected-did <did:key:…>`. [Existing DID import guide](https://github.com/AMCONSEIL/did-to-talisman)

## Get test FLOP

Use **Check balance and faucet** to read the finalized free balance, remaining grant budget and spend requirement. When the faucet is open, **Claim +10 FLOP** asks Talisman to sign a grant request. An accepted request shows its transaction link and reported status. An HTTP 429 displays the supplied delay. If the faucet reports `agent_spend_missing`, one settled spend is required for the next grant. A timeout after submission leaves a durable pending record. Check the transfer in the explorer before attempting recovery. [Testnet explorer](https://testnet.flopscan.io)

## Send a message

**Gateway.** The model menu loads the live text catalogue. Gateway enrollment was returning HTTP 404 on November 27. You can still connect locally, use the faucet and choose Direct. When wallet enrollment becomes available, the chat checks the signed challenge, authorized model, quota and receipts before sending. The model catalogue alone does not establish a miner's admission. [Live catalogue](https://gateway.testnet.flop.network/v1/models)

**Direct.** Obtain the miner's Testnet address and HTTPS origin from its operator. Create `.local/direct-miners.json` and restart the chat. The file takes an array. Replace the placeholders with the operator's public values.

~~~json
[{"name":"My miner","address":"REPLACE_WITH_TESTNET_SS58","endpoint":"https://miner.example.org"}]
~~~

You may add `enclaveKey` with the operator-confirmed session key (64 lowercase hexadecimal characters). In **Settings**, select **Direct**, select a catalogue model or enter its exact lowercase slug, for example `qwen/qwen3-8b`. Send the message, choose your miner, set escrow and review costs. The preflight verifies a fresh signed ready proof, worker build and finalized registry identity before the opening signature. Review the origin, model, channel ID and fee estimate in the quote. Escrow defaults to 0.05 FLOP, output to 256 tokens (maximum 1024), and channel duration to 1200 seconds. The 0.02 FLOP local opening-fee ceiling and your total spending caps also apply.

Talisman signs the one-turn `computeChannel.forceOpen`. The SDK uses a separate ephemeral key for the session; the miner submits cooperative settlement. **Check receipts** reconciles a pending channel at finality. Direct receipts show the channel ID, settlement transaction, paid and burned amounts, and settled Gn. A verified reply can precede final settlement. Gateway receipts report gateway accounting. [Security and recovery](SECURITY.md)
