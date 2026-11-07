// Keep direct writes inside the pinned SDK's explicit compatibility list.
import { assertSupportedSpecVersion } from "./node_modules/@flop-labs/sdk/dist/runtime-compatibility.js";
export const DEVNET_GENESIS = "0x99c172c095340ace980631f9123544c6bebd4839f3437e463533422d8be2d631";
export function checkDirectNetwork(api) {
  if (api.genesisHash.toHex() !== DEVNET_GENESIS || api.registry.chainDecimals[0] !== 18) {
    throw Object.assign(new Error("Unexpected network"), { code: "DIRECT_NETWORK_MISMATCH" });
  }
  const runtime = Number(api.runtimeVersion.specVersion.toString());
  try { assertSupportedSpecVersion(runtime); }
  catch (error) {
    if (error.code !== "RUNTIME_INCOMPATIBLE") throw error;
    throw Object.assign(new Error("Direct runtime unsupported"), { code: "DIRECT_RUNTIME_UNSUPPORTED", runtime });
  }
}
export function directDiagnostic(error) {
  if (error?.code === "DIRECT_NETWORK_MISMATCH") return { error_code: error.code };
  if (error?.code === "DIRECT_RUNTIME_UNSUPPORTED" && Number.isSafeInteger(error.runtime) && error.runtime >= 0) {
    return { error_code: error.code, runtime: error.runtime };
  }
  return {}; // Raw RPC/miner errors may include credentials, signatures or prompts.
}
