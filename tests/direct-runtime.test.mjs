import test from "node:test";
import assert from "node:assert/strict";
import { DEVNET_GENESIS, checkDirectNetwork, directDiagnostic } from "../direct_runtime.mjs";
const api = version => ({ genesisHash: {toHex: () => DEVNET_GENESIS}, registry: {chainDecimals: [18]}, runtimeVersion: {specVersion: version} });
test("published SDK accepts the live Devnet runtime and an earlier supported version", () => {
 for (const version of [1014014, 1014011]) checkDirectNetwork(api(version));
});
test("future runtime and a hole inside SDK range stay blocked", () => {
 for (const version of [1014015, 1014006]) {
  assert.throws(() => checkDirectNetwork(api(version)), e => e.code === "DIRECT_RUNTIME_UNSUPPORTED" && e.runtime === version);
 }
});
test("network and denomination must still match", () => {
 const wrong = api(1014011); wrong.genesisHash.toHex = () => "0x00";
 assert.throws(() => checkDirectNetwork(wrong), e => e.code === "DIRECT_NETWORK_MISMATCH");
 const denom = api(1014011); denom.registry.chainDecimals = [12];
 assert.throws(() => checkDirectNetwork(denom), e => e.code === "DIRECT_NETWORK_MISMATCH");
});
test("diagnostics cannot leak raw errors or private inputs", () => {
 assert.deepEqual(directDiagnostic(new Error("private inputs")), {});
 assert.deepEqual(directDiagnostic({code:"DIRECT_RUNTIME_UNSUPPORTED", runtime:1014014, message:"private"}),
  {error_code:"DIRECT_RUNTIME_UNSUPPORTED", runtime:1014014});
 assert.deepEqual(directDiagnostic({code:"DIRECT_RUNTIME_UNSUPPORTED", runtime:"private"}), {});
});
