// Keep direct writes inside the pinned SDK's explicit compatibility list.
import { assertSupportedSpecVersion } from "./node_modules/@flop-labs/sdk/dist/runtime-compatibility.js";
export const TESTNET_GENESIS = "0x918abd58fb16306b30ef3886514cfaebffecb4de43e82b6f8ec4795c43cfd800";
export function checkDirectNetwork(api) {
  if (api.genesisHash.toHex() !== TESTNET_GENESIS || api.registry.chainSS58 !== 42 || api.registry.chainDecimals[0] !== 18 || api.registry.chainTokens[0] !== "FLOP") {
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
