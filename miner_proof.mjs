import { randomBytes } from "node:crypto";
import { cryptoWaitReady, decodeAddress } from "@polkadot/util-crypto";
import { hexToU8a, u8aEq } from "@polkadot/util";
import { fetchSessionInfoProof, verifySessionInfoProof, modelIdentityHash } from "./node_modules/@flop-labs/sdk/dist/miner-admission.js";
import { chainText } from "./node_modules/@flop-labs/sdk/dist/chain-text.js";
import { TESTNET_GENESIS } from "./direct_runtime.mjs";

const bareHash = /^[0-9a-f]{64}$/;
const slug = /^[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._-]*$/;
const precisions = ["FP32", "FP16", "BF16", "INT8", "INT4", "Mixed"];
const bytes = hex => hexToU8a("0x" + hex);

export async function provenModel({ endpoint, miner, model, enclaveKey }, registry, fetchImpl) {
  await cryptoWaitReady();
  const challenge = randomBytes(32);
  const proof = await fetchSessionInfoProof(endpoint, challenge, fetchImpl);
  const wire = proof.model_identity;
  if (!slug.test(model) || wire?.requested_slug !== model || !bareHash.test(proof.enclave_key) ||
      (enclaveKey && enclaveKey !== proof.enclave_key) ||
      ![wire.model_hash, wire.measured_root, wire.decode_policy_hash].every(hash => bareHash.test(hash))) {
    throw Error("Unexpected miner identity");
  }

  const identity = {
    requestedSlug: model, registryModel: wire.registry_model, registryVersion: wire.registry_version,
    backendModelName: wire.backend_model_name, precision: wire.precision, modelHash: bytes(wire.model_hash),
    measuredRoot: bytes(wire.measured_root), decodePolicyHash: bytes(wire.decode_policy_hash),
  };
  const sessionKey = bytes(proof.enclave_key);
  const result = verifySessionInfoProof(proof, {
    challenge, genesisHash: hexToU8a(TESTNET_GENESIS), account: decodeAddress(miner),
    enclaveKey: sessionKey, modelIdentityHash: modelIdentityHash(identity),
  });
  if (!result || !/^v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?$/.test(result.image.version)) {
    throw Error("Miner not ready or invalid signed worker build");
  }
  const precision = precisions[identity.precision];
  if (!precision) throw Error("Unsupported precision");
  const [registered, policies, root] = await Promise.all([
    registry.models(identity.modelHash), registry.allowedDecodePolicies(identity.modelHash),
    registry.measuredRoots(identity.modelHash, precision),
  ]);
  const row = registered.unwrap();
  if (row.status.toString() !== "Verified" ||
      chainText(row.get?.("modelName") ?? row.modelName) !== identity.registryModel ||
      chainText(row.get?.("version") ?? row.version) !== identity.registryVersion ||
      !row.supportedPrecisions.some(value => value.toString() === precision) ||
      !policies.unwrap().some(policy => u8aEq(policy.toU8a(true), identity.decodePolicyHash)) ||
      !u8aEq(root.unwrap().toU8a(true), identity.measuredRoot)) {
    throw Error("Miner model does not match finalized registry");
  }
  return { identity, sessionKey, workerVersion: result.image.version };
}
