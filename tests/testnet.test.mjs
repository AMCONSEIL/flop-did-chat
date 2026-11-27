import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import { encodeAddress, ed25519PairFromSeed, ed25519Sign } from "@polkadot/util-crypto";
import { hexToU8a, u8aToHex, u8aWrapBytes } from "@polkadot/util";
import { ready, SessionKey } from "../node_modules/@flop-labs/sdk/dist/compute-channel/crypto.js";
import { signSessionInfo } from "../node_modules/@flop-labs/sdk/dist/miner-admission.js";
import { runDirectSession } from "../node_modules/@flop-labs/sdk/dist/compute-channel/direct-session.js";
import { TESTNET_GENESIS } from "../direct_runtime.mjs";
import { provenModel } from "../miner_proof.mjs";
import { minerOrigin, minerFetch, publicIP } from "../miner_transport.mjs";
import { walletSignature } from "../wallet_verify.mjs";
import { canSend } from "../web/core.js";

await ready();
const bytes = n => new Uint8Array(32).fill(n);
const model = "qwen/qwen3-8b";
const modelIdentity = {requestedSlug:model, registryModel:"Qwen/Qwen3-8B", registryVersion:"1",
  backendModelName:"Qwen/Qwen3-8B", precision:1, modelHash:bytes(4), measuredRoot:bytes(5), decodePolicyHash:bytes(6)};
const endpoint = "https://miner.example.org";
const enclave = SessionKey.fromSeed(bytes(1));
const miner = encodeAddress(bytes(2));
const codec = value => ({toU8a:()=>value});
const some = value => ({unwrap:()=>value});
const registry = {
  models: async()=>some({status:"Verified",supportedPrecisions:["FP16"],modelName:modelIdentity.registryModel,version:"1"}),
  allowedDecodePolicies: async()=>some([codec(bytes(6))]), measuredRoots: async()=>some(codec(bytes(5)))
};
function responder(modify = () => {}) {
  return async (url, opts) => {
    assert.equal(url,endpoint+"/session/info-proof");
    const {challenge} = JSON.parse(opts.body);
    const proof = signSessionInfo(enclave, hexToU8a("0x"+challenge), {genesisHash:hexToU8a(TESTNET_GENESIS),
      account:bytes(2), modelIdentity, ready:true, image:{version:"0.1.520",revision:"test"}});
    modify(proof);
    return Response.json(proof);
  };
}
test("SDK signed info-proof binds readiness, fresh challenge, chain, account, model and registry", async () => {
  const job = {endpoint,miner,model};
  const result = await provenModel(job,registry,responder());
  assert.equal(result.workerVersion,"0.1.520");
  assert.deepEqual(result.sessionKey,enclave.publicKey);
  for (const mutate of [p=>p.ready=false, p=>p.genesis_hash="11".repeat(32), p=>p.model_identity.requested_slug=model.toUpperCase(),
    p=>p.image.version="9.9.9", p=>p.account_id="12".repeat(32)]) {
    await assert.rejects(provenModel(job,registry,responder(mutate)));
  }
  await assert.rejects(provenModel({...job,enclaveKey:"aa".repeat(32)},registry,responder()));
  await assert.rejects(provenModel(job,{...registry,measuredRoots:async()=>some(codec(bytes(9)))},responder()));
  let cached;
  await provenModel(job,registry,async (...args)=>{ cached = await (await responder()(...args)).json(); return Response.json(cached); });
  await assert.rejects(provenModel(job,registry,async()=>Response.json(cached)));
});
test("only public HTTPS miner destinations, including every DNS answer and subsequent URLs", async () => {
  assert.equal(minerOrigin(endpoint),endpoint);
  for (const url of ["https://x.localhost", "https://127.0.0.1", "https://[::1]", endpoint+"/path", "http://miner.example.org", endpoint+"?q", "https://x:y@miner.example.org"]) assert.throws(()=>minerOrigin(url));
  for (const ip of ["10.0.0.1","127.0.0.1","169.254.169.254","192.168.1.1","100.64.0.2","::1","::ffff:127.0.0.1","fe80::1","fc00::1","2001:db8::1"]) assert.equal(publicIP(ip),false,ip);
  assert.equal(publicIP("1.1.1.1"),true);
  await assert.rejects(minerFetch(endpoint,async()=>[{family:4,address:"1.1.1.1"},{family:4,address:"127.0.0.1"}]));
  const pinned = await minerFetch(endpoint,async()=>[{family:4,address:"1.1.1.1"}]);
  await assert.rejects(pinned("https://other.example.org/session/open"));
  await assert.rejects(pinned(endpoint+"/admin"));
});
test("sr25519 and Ed25519 wallet verification distinguishes signRaw from signPayload and checks type prefixes", () => {
  const data = new TextEncoder().encode("offline fixture");
  const ed = ed25519PairFromSeed(bytes(7));
  for (const [scheme, pub, sign, prefix] of [["sr25519",enclave.publicKey,b=>enclave.sign(b),"01"],["ed25519",ed.publicKey,b=>ed25519Sign(b,ed),"00"]]) {
    const raw = u8aToHex(sign(u8aWrapBytes(data)));
    assert.ok(walletSignature(scheme,pub,data,"0x"+prefix+raw.slice(2),true));
    assert.ok(!walletSignature(scheme,pub,data,raw));
    assert.ok(!walletSignature(scheme,pub,data,"0x"+(prefix==="01"?"00":"01")+raw.slice(2),true));
    assert.ok(walletSignature(scheme,pub,data,u8aToHex(sign(data))));
  }
});
test("real SDK hands forceOpen one ephemeral key, chosen miner, escrow and one-turn SLA", async () => {
  let opening;
  const rt = {genesisHash:hexToU8a(TESTNET_GENESIS),agentAddress:encodeAddress(bytes(3)),maxDuration:400n,
    resolveIdentity:async()=>modelIdentity,minerCalibrated:async()=>true,
    chain:{forceOpen:async params=>{opening=params; throw Error("offline stop before transaction");}}};
  await assert.rejects(runDirectSession({miner,model,via:"force",messages:[{role:"user",content:"fixture"}],
    maxTokens:256,maxFlop:5n*10n**16n,maxDurationSeconds:1200},rt),/open submission outcome unknown/);
  assert.equal(opening.miner,miner); assert.equal(opening.maxDuration,400n); assert.equal(opening.maxTurns,1);
  assert.equal(opening.reattestEvery,1); assert.equal(opening.escrow,5n*10n**16n);
  assert.equal(opening.agentKey.length,32); assert.notDeepEqual(opening.agentKey,bytes(3)); assert.ok(typeof opening.nonce==="bigint");
});
test("direct selection accepts canonical Testnet models independent of gateway enrollment", () => {
  const s={direct:{available:true},account:{},gateway_block:"ENROLLMENT_UNAVAILABLE",limits:{session_committed:"0",session_cap:"1"}};
  for (const id of ["qwen/qwen3-8b","qwen/qwen3-14b","qwen/qwen3-4b"]) assert.ok(canSend(s,false,"test",id));
  assert.equal(canSend(s,false,"test","Qwen/Qwen3-8B"),false);
});
test("every translated HTML label has French and English text", () => {
  const html=readFileSync(new URL("../web/index.html",import.meta.url),"utf8");
  const source=readFileSync(new URL("../web/app.js",import.meta.url),"utf8");
  const dictionary = Function("return ("+source.split("const TEXT = ")[1].split(";\nconst ERRORS")[0]+")")();
  for(const [,key] of html.matchAll(/data-(?:i18n|placeholder)="([^"]+)"/g)){
    assert.equal(dictionary[key]?.length,2,key); assert.ok(dictionary[key].every(value=>value.trim()));
  }
});
