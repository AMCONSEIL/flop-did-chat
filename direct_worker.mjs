// One invocation, one named miner and one Talisman-funded devnet channel.
import { createInterface } from "node:readline";
import { ApiPromise, WsProvider } from "@polkadot/api";
import { decodeAddress, ed25519Verify, blake2AsU8a } from "@polkadot/util-crypto";
import { u8aEq, u8aToHex, hexToU8a } from "@polkadot/util";
// The public SDK pins runDirectSession; these companion modules are pinned by package-lock.json.
import { runDirectSession } from "./node_modules/@flop-labs/sdk/dist/compute-channel/direct-session.js";
import { createDirectSessionRuntime } from "./node_modules/@flop-labs/sdk/dist/compute-channel/direct-session-chain.js";
import { ChannelSession } from "./node_modules/@flop-labs/sdk/dist/compute-channel/session.js";
import { channelIdV1 } from "./node_modules/@flop-labs/sdk/dist/compute-channel/transcript.js";
import { decodeTextTurnOutput } from "./node_modules/@flop-labs/sdk/dist/compute-channel/transport-http.js";

const genesis = "0x99c172c095340ace980631f9123544c6bebd4839f3437e463533422d8be2d631";
const amount = value => BigInt(value.toString());
const send = event => process.stdout.write(JSON.stringify(event, (_, v) => typeof v === "bigint" ? String(v) : v) + "\n");
const sameAccount = (a, b) => u8aEq(decodeAddress(a), decodeAddress(b));
const input = createInterface({ input: process.stdin, crlfDelay: Infinity })[Symbol.asyncIterator]();
const read = async () => {
  const line = await input.next();
  if (line.done) throw Error("Input closed");
  return JSON.parse(line.value);
};
let broadcastAuthorized = false;
const provider = new WsProvider("wss://rpc.devnet.flop.network", false);
const deadline = setTimeout(() => process.exit(1), 290_000);

async function finalized(api) {
  const hash = await api.rpc.chain.getFinalizedHead();
  const [at, header] = await Promise.all([api.at(hash), api.rpc.chain.getHeader(hash)]);
  return { at, block: Number(header.number.toString()) };
}

async function reconcile(api, job) {
  const { at, block } = await finalized(api);
  const stored = await at.query.computeChannel.channels(job.channel_id);
  if (!stored.isSome) return send({ phase: "pending", chain_state: "not_found" });
  const channel = stored.unwrap();
  if (!sameAccount(channel.miner.toString(), job.miner) || !sameAccount(channel.agent.toString(), job.address)) {
    throw Error("Finalized channel identity mismatch");
  }
  if (channel.state.type !== "Closed") return send({ phase: "pending", chain_state: channel.state.type });
  const start = Number(job.scan_from);
  const end = Math.min(start + 63, block);
  for (let height = start; height <= end;) {
    const heights = [];
    while (height <= end && heights.length < 8) heights.push(height++);
    const pages = await Promise.all(heights.map(async n => {
      const hash = await api.rpc.chain.getBlockHash(n);
      return { hash, records: await (await api.at(hash)).query.system.events() };
    }));
    for (const { hash, records } of pages) {
      for (const { phase, event } of records) {
        if (!phase.isApplyExtrinsic || event.section !== "computeChannel" ||
            !["Settled", "TimedOutRefunded", "ForceOpenExpired"].includes(event.method) ||
            event.data[0]?.toHex() !== job.channel_id) continue;
        const signedBlock = await api.rpc.chain.getBlock(hash);
        const tx = signedBlock.block.extrinsics[phase.asApplyExtrinsic.toNumber()].hash.toHex();
        return send(event.method === "Settled"
          ? { phase: "settled", tx, miner_paid_raw: amount(event.data[1]), burned_raw: amount(event.data[2]) }
          : { phase: "released", tx });
      }
    }
  }
  send({ phase: "pending", chain_state: "Closed", scan_from: end + 1 });
}

async function session(api, job) {
  const { address, miner, endpoint, model, messages, maxTokens } = job;
  if (sameAccount(address, miner)) throw Error("Client and miner accounts must differ");
  const escrow = amount(job.escrow);
  const feeCap = amount(job.fee_cap);
  const { at, block } = await finalized(api);
  const [minerRow, calibration, balance] = await Promise.all([
    at.query.minerStaking.miners(miner), at.query.hwCalibration.benchmarkBurstCaps(miner), at.query.system.account(address),
  ]);
  if (!minerRow.isSome || !minerRow.unwrap().isActive.isTrue || !calibration.isSome ||
      BigInt(block) >= amount(calibration.unwrap().acceptedAt) + amount(at.consts.hwCalibration.calibrationLeaseBlocks)) {
    throw Error("Miner inactive or calibration expired");
  }
  if (amount(balance.data.free) < escrow + feeCap) throw Error("Insufficient devnet wallet balance");

  const fetchMiner = globalThis.fetch;
  globalThis.fetch = (url, options) => {
    if (new URL(url).origin !== endpoint) throw Error("Unapproved miner origin");
    return fetchMiner(url, { ...options, redirect: "error" });
  };
  // The public probe is read-only and must advertise channel-key authentication.
  const probe = await fetch(endpoint + "/session/info", { signal: AbortSignal.timeout(10_000) });
  const challenge = probe.headers.get("x-flop-session-challenge");
  await probe.body?.cancel();
  if (!challenge) throw Error("Miner does not advertise direct session authentication");

  let candidate, signing = false, verified = false;
  const signer = { address, signer: { async signPayload(payload) {
    if (signing || !sameAccount(payload.address, address) || payload.genesisHash !== genesis ||
        amount(payload.tip ?? 0) !== 0n) throw Error("Unexpected signer, network or tip");
    signing = true;
    const call = api.registry.createType("Call", payload.method);
    if (call.section !== "computeChannel" || call.method !== "forceOpen") throw Error("Opening call expected");
    const [target, modelHash, root, policy, precision, , sla, reserve, nonce] = call.args;
    if (!sameAccount(target.toString(), miner) || amount(reserve) !== escrow ||
        !u8aEq(modelHash.toU8a(), identity.modelHash) || !u8aEq(root.toU8a(), identity.measuredRoot) ||
        !u8aEq(policy.toU8a(), identity.decodePolicyHash) || precision.index !== identity.precision ||
        amount(sla.maxTurns) !== 1n || amount(sla.maxDuration) !== runtime.maxDuration ||
        amount(sla.reattestEvery) !== 1n) throw Error("Unexpected miner, model, reserve or SLA");
    const fee = amount((await api.tx(call).paymentInfo(address)).partialFee);
    if (fee > feeCap) throw Error("Opening fee exceeds the local cap");
    candidate = u8aToHex(channelIdV1(hexToU8a(genesis), decodeAddress(address), decodeAddress(miner), amount(nonce)));
    const preview = { escrow, fee, fee_cap: feeCap, total: escrow + fee, channel_id: candidate,
      scan_from: block, model, precision: precision.toString(), max_tokens: maxTokens, expires_at: Date.now() + 60_000 };
    send({ phase: "review", preview, payload });
    const { signature } = await read();
    if (Date.now() >= preview.expires_at || !/^0x(?:00)?[0-9a-f]{128}$/i.test(signature)) throw Error("Invalid or expired signature");
    const encoded = api.registry.createType("ExtrinsicPayload", payload, { version: payload.version }).toU8a({ method: true });
    const bytes = encoded.length > 256 ? blake2AsU8a(encoded) : encoded;
    if (!ed25519Verify(bytes, hexToU8a(signature).slice(-64), decodeAddress(address))) throw Error("Ed25519 signature mismatch");
    const [currentNonce, currentFee] = await Promise.all([
      api.rpc.system.accountNextIndex(address), api.tx(call).paymentInfo(address),
    ]);
    if (amount(currentNonce) !== amount(payload.nonce) || amount(currentFee.partialFee) > feeCap ||
        amount(api.runtimeVersion.specVersion) !== amount(payload.specVersion) ||
        Date.now() >= preview.expires_at) throw Error("Account, runtime or quote changed");
    // The parent persists the channel candidate before it supplies this signature.
    broadcastAuthorized = true;
    return { id: 1, signature: signature.length === 130 ? "0x00" + signature.slice(2) : signature };
  } } };

  const options = { api, signer, miner, endpoint, model, messages, maxTokens, maxFlop: escrow, via: "force" };
  const runtime = await createDirectSessionRuntime(options);
  const identity = await runtime.resolveIdentity();
  runtime.resolveIdentity = async () => identity;
  const originalOpen = runtime.chain.forceOpen.bind(runtime.chain);
  runtime.chain.forceOpen = async params => {
    const opened = await originalOpen(params);
    if (u8aToHex(opened.channelId) !== candidate) throw Error("Opening event differs from signed channel");
    send({ phase: "opened", tx: opened.txHash });
    return opened;
  };
  const needsReview = () => { throw Error("Review the channel at finality before taking another action"); };
  runtime.chain.forceSettle = needsReview;
  runtime.chain.expireForceOpen = needsReview;
  runtime.chain.timeout = needsReview;
  // Capture only the SDK-verified reply, before the acknowledgement/settlement can fail.
  const originalTurn = ChannelSession.prototype.chatTurn;
  ChannelSession.prototype.chatTurn = function (request, check) {
    return originalTurn.call(this, request, check, receipt => {
      const reply = new TextDecoder("utf-8", { fatal: true }).decode(decodeTextTurnOutput(receipt.output));
      if (reply.length > 100_000) throw Error("Reply exceeds the local size limit");
      verified = true;
      send({ phase: "verified", reply });
    });
  };
  try {
    const result = await runDirectSession(options, runtime);
    if (!verified || !result.settlement.cooperative || u8aToHex(result.channelId) !== candidate) {
      throw Error("Unexpected settlement");
    }
    send({ phase: "settled", tx: result.settleTx, miner_paid_raw: result.settlement.minerPaid,
      burned_raw: result.settlement.burned });
  } finally {
    ChannelSession.prototype.chatTurn = originalTurn;
  }
}

try {
  const job = await read();
  await provider.connect();
  const api = await ApiPromise.create({ provider, throwOnConnect: true, throwOnUnknown: true, noInitWarn: true });
  if (api.genesisHash.toHex() !== genesis || api.runtimeVersion.specVersion.toString() !== "1014003" ||
      api.registry.chainDecimals[0] !== 18) throw Error("Unexpected devnet genesis, runtime or denomination");
  if (job.action === "reconcile") await reconcile(api, job);
  else await session(api, job);
} catch {
  // Never print raw RPC errors, wallet signatures, credentials or prompts.
  send({ phase: broadcastAuthorized ? "error" : "not_submitted" });
} finally {
  await provider.disconnect();
  clearTimeout(deadline);
  process.stdin.destroy();
}
