"""Local browser acceptance fixture. Public RFC key only. NEVER connects to FLOP."""
from pathlib import Path
import json
import sys
import argparse
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from flop_chat import Chat, make_handler, ThreadingHTTPServer
import test_chat, time
test_chat.NOW = int(time.time())
from test_chat import FakeGateway, KEY, IDENTITY, NOW, SEED

base = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--port", type=int, default=50511)
parser.add_argument("--ledger", type=Path, default=base / "validation.local" / "fixture-ledger.json")
parser.add_argument("--gateway-404", action="store_true")
parser.add_argument("--faucet-open", action="store_true")
args = parser.parse_args()
chat = Chat(args.ledger, FakeGateway(), clock=lambda: NOW)
if args.gateway_404:
    original_request = chat.gateway.request
    def gateway_request(path, *params):
        if path.startswith("/enroll/wallet/challenge?"):
            raise test_chat.ChatError("GATEWAY_HTTP", 404)
        return original_request(path, *params)
    chat.gateway.request = gateway_request

def fixture_faucet(url, payload=None):
    if url.endswith("/chain"):
        return 200, {"network":"testnet", "genesisHash":test_chat.GENESIS}
    if url.endswith("/limits"):
        return 200, {"network":"testnet","stale":False,"faucet":{"status":"open" if args.faucet_open else "daily_cap_reached","agent":{"grantFlop":10,
                    "claimPath":"/v1/testnet/agent-claims"},"dailyCap":{"remainingFlop":10 if args.faucet_open else 0}}}
    if args.faucet_open and url.endswith("/v1/testnet/agent-claims"):
        return 200, {"success":True, "amount":10, "txHash":"0x"+"aa"*32, "status":"included"}
    if payload and payload.get("method") in {"state_getStorage","chain_getFinalizedHead","chain_getBlockHash"}:
        return 200, {"result": None if payload["method"] == "state_getStorage" else test_chat.GENESIS}
    raise AssertionError("Unexpected offline request")
chat.faucet.request = fixture_faucet
chat.direct.available = False  # Offline fixture must never start the real SDK worker.
real_handler = make_handler(chat)
wallet_script = """
window.injectedWeb3 = { talisman: { enable: async () => ({
 accounts: {get: async () => [ACCOUNT]},
 signer: {signRaw: async ({data}) => {
  const keyBytes = Uint8Array.from(PKCS8.match(/../g), x => parseInt(x,16));
  const key = await crypto.subtle.importKey('pkcs8',keyBytes,{name:'Ed25519'},false,['sign']);
  const messageBytes = Uint8Array.from(data.slice(2).match(/../g),x=>parseInt(x,16));
  const wrapped = new Uint8Array(7+messageBytes.length+8);
  wrapped.set(new TextEncoder().encode('<Bytes>'));
  wrapped.set(messageBytes,7);
  wrapped.set(new TextEncoder().encode('</Bytes>'),7+messageBytes.length);
  const signature = new Uint8Array(await crypto.subtle.sign('Ed25519',key,wrapped));
  return {signature:'0x'+Array.from(signature,x=>x.toString(16).padStart(2,'0')).join('')};
 }}
})}};
document.addEventListener('DOMContentLoaded',()=>{
 document.title='OFFLINE FIXTURE â€” FLOP DID Chat';
 document.querySelector('.network-note').textContent='OFFLINE TEST Â· public RFC8032 identity Â· no FLOP connection or real funds';
 const control=document.createElement('button');control.id='fixture-429';
 control.textContent='Offline fixture: next request 429';
 control.className='button';
 control.addEventListener('click',()=>fetch('/fixture/429',{method:'POST'}));
 document.querySelector('.network-note').append(control);
});
""".replace("ACCOUNT", json.dumps({"address": IDENTITY["address"], "name": "RFC8032 PUBLIC TEST ACCOUNT", "type": "ed25519"})).replace("PKCS8", json.dumps("302e020100300506032b657004220420" + SEED.hex()))

class Fixture(real_handler):
    def do_GET(self):
        if self.path == "/test-wallet.js":
            return self.send(200, wallet_script.encode(), "text/javascript; charset=utf-8")
        if self.path == "/":
            raw=(base/"web"/"index.html").read_bytes().replace(b"__CSRF__", chat.bootstrap_token.encode())
            raw=raw.replace(b"</head>", b'<script src="/test-wallet.js"></script></head>')
            return self.send(200,raw,"text/html; charset=utf-8")
        return super().do_GET()
    def do_POST(self):
        if self.path == "/fixture/429":
            chat.gateway.mode="429"
            return self.send(200,{"fixture":True})
        return super().do_POST()

server=ThreadingHTTPServer(("127.0.0.1",args.port),Fixture)
server.local_host=f"127.0.0.1:{server.server_port}"
print("OFFLINE fixture http://" + server.local_host,flush=True)
try: server.serve_forever()
except KeyboardInterrupt: pass
finally: server.server_close()
