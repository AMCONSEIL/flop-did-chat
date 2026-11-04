import test from "node:test";
import assert from "node:assert/strict";
import { metrics, rawFlop, contextFor, canSend, safeConversationStore, substrateCandidates } from "../web/core.js";

test("unknown cost stays unknown; release is not a settled zero", () => {
 const m = metrics([{state:"released", settled_spend:null, settled_spend_raw:null}]);
 assert.equal(m.settled, null); assert.equal(m.tokens, null);
});
test("exact raw FLOP and explicit zero", () => {
 assert.equal(rawFlop("390000000000000001"), "0.390000000000000001");
 assert.equal(rawFlop("0"),"0");
 const m = metrics([{state:"settled",settled_spend_raw:"0"}]);
 assert.equal(m.settled,0); assert.equal(m.settledExactRaw,"0");
});
test("pending quota stays separate from settled usage", () => {
 const m = metrics([{state:"estimated",reserved_spend:0.39,settled_spend:null,response_received:true,usage:{total_tokens:18}}]);
 assert.equal(m.reserved,0.39); assert.equal(m.settled,null); assert.equal(m.unknownSettled,1); assert.equal(m.tokens,18);
});
test("conversation context excludes errors and includes successful multi-turn history", () => {
 const c={turns:[{prompt:"first",answer:"answer",state:"answered"},{prompt:"failed",state:"failed",error:"429"}]};
 assert.deepEqual(contextFor(c,"next"),[{role:"user",content:"first"},{role:"assistant",content:"answer"},{role:"user",content:"next"}]);
});
test("send blocked by pending requests, expiry and spend cap", () => {
 const s={connected:true,auth:{model:"q",expires_at:200000},unresolved:[],limits:{session_committed:"0",session_cap:"0.9"}};
 assert.equal(canSend(s,false,"hello","q",100),true);
 for(const change of [{unresolved:["pending"]},{cooldown_until:101},{auth:{model:"q",expires_at:1}},{limits:{session_committed:"0.9",session_cap:"0.9"}}]) assert.equal(canSend({...s,...change},false,"hello","q",100),false);
 assert.equal(canSend(s,true,"hello","q",100),false);
 assert.equal(canSend(s,false,"hello","other",100),false);
});
test("browser history whitelist drops bearer and signature fields", () => {
 const safe=safeConversationStore([{id:"c",title:"title",key:"secret",signature:"signature",turns:[{id:"r",prompt:"hello",answer:"ok",state:"answered",key:"secret"}]}]);
 assert.equal(JSON.stringify(safe).includes("secret"),false);
 assert.equal(JSON.stringify(safe).includes("signature"),false);
});


test("Talisman sr25519 metadata must not hide an Ed25519 SS58 candidate", () => {
 const address="5Gw54ghuAHodDGAS91DUxqvKa6PeT9bhDdns3ztBupY8pSyn";
 for (const type of ["sr25519","ed25519",undefined]) {
  const candidate={address,name:"Public RFC8032 fixture",...(type?{type}:{})};
  assert.deepEqual(substrateCandidates([candidate]),[candidate]);
 }
});

test("wallet candidates reject EVM/malformed entries and deduplicate addresses", () => {
 const address="5Gw54ghuAHodDGAS91DUxqvKa6PeT9bhDdns3ztBupY8pSyn";
 assert.deepEqual(substrateCandidates(null),[]);
 assert.deepEqual(substrateCandidates([null,{}, {address:42}, {address:"0x"+"12".repeat(20),type:"ethereum"}, {address,type:"ethereum"}, {address:"not an address"}]),[]);
 const candidate={address,type:"sr25519"};
 assert.deepEqual(substrateCandidates([candidate,{...candidate,type:"ed25519"}]),[candidate]);
});
