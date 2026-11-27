# Security · FLOP Testnet 0.3.0

## Identity and network

The Python server binds to 127.0.0.1. It checks Host for reads and requires the exact local Origin and a per-process CSRF token for mutations. Talisman grants access to the selected public account. The server checks its SS58 checksum, DID multicodec and signature scheme. Use the optional --expected-did and --expected-address locks for a personal installation. Gateway credentials stay in process memory.

The gateway, faucet and chain RPC use fixed origins. The HTTP clients refuse redirects. Direct miners must be explicitly listed in the local configuration. Confirm the miner account and HTTPS origin independently with its operator. The transport resolves the hostname, rejects non-public or mixed DNS answers, connects to one approved IP and verifies TLS for the original hostname. All miner requests stay under /session/ on that origin. The browser renders network text without interpreting HTML.

## Wallet approvals

- Login and faucet use separate messages. The faucet signature covers the domain tag, Testnet genesis, address and nonce wrapped by Talisman as Substrate bytes. Signing does not submit a wallet extrinsic. Before sending the grant request, the server persists an atomic per-address pending record. An ambiguous outcome blocks new claims across restarts. Keep the local journal when investigating a lost response.
- Direct mode checks a fresh enclave-signed ready proof, worker version, account, genesis, model identity and finalized model registry. Configuring the operator's optional enclaveKey pin authenticates that session key before opening. Without a pin, the operator-confirmed TLS endpoint supplies the initial key. After opening, the SDK verifies it against the acknowledged channel before sending the conversation.
- The wallet approves one decoded forceOpen extrinsic after the quote. The server verifies the wallet signature, account nonce, network, model fields, reserve, ephemeral agent key, one-turn SLA, zero tip and fee estimate before broadcast. Fees can change between estimation and inclusion. Caps are application limits. Channel escrow can remain locked during disputes or delayed finality.
- The SDK generates an ephemeral session key in the worker process for turn and settlement evidence. The miner submits cooperative settlement. The client records chain receipt metadata and protects unresolved channels against replay. A restarted worker cannot reconstruct a lost ephemeral secret. Use the receipt check to find finalized settlement or refund events. Additional recovery transactions require a separate operator decision.

## Local records

.local/ holds the miner list, server lock, Testnet request ledger and faucet state. Protect this directory with your OS account permissions and exclude it from version control and public bug reports. Only opt in to browser history on a trusted computer. It stores chat text in the browser. The selected service receives the conversation context when you send it.

Report suspected problems with the application version, failure stage and a redacted error. Exclude wallet backups, signatures, prompts, access tokens and private service endpoints.
