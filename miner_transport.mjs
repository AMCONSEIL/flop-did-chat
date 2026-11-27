// Resolve once, preserve the original TLS hostname and connect to the approved address.
import { lookup } from "node:dns/promises";
import https from "node:https";
import { isIP } from "node:net";
import ipaddr from "ipaddr.js";

export function minerOrigin(endpoint) {
  const url = new URL(endpoint);
  const dnsName = /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/;
  const localName = /(?:^|\.)(?:localhost|local|internal|home|lan|test|invalid)$/;
  if (url.protocol !== "https:" || url.port || url.username || url.password || url.search || url.hash ||
      url.pathname !== "/" || isIP(url.hostname) || !dnsName.test(url.hostname) || localName.test(url.hostname) ||
      ![url.origin, url.origin + "/"].includes(endpoint)) {
    throw Error("Invalid miner HTTPS origin");
  }
  return url.origin;
}

export function publicIP(address) {
  if (!ipaddr.isValid(address)) return false;
  const ip = ipaddr.parse(address);
  if (ip.range() !== "unicast") return false;
  if (ip.kind() === "ipv6") {
    return ip.match(ipaddr.parse("2000::"), 3) &&
      !ip.match(ipaddr.parse("2001::"), 23) && !ip.match(ipaddr.parse("3fff::"), 20);
  }
  return !ip.match(ipaddr.parse("192.0.0.0"), 24) && !ip.match(ipaddr.parse("192.88.99.0"), 24);
}

export async function minerFetch(endpoint, resolve = lookup) {
  const origin = minerOrigin(endpoint);
  const addresses = await resolve(new URL(origin).hostname, { all: true, verbatim: true });
  if (!addresses.length || !addresses.every(row => publicIP(row.address))) throw Error("Miner DNS is not public");
  const pin = addresses.find(row => row.family === 4) || addresses[0];
  return async (target, init = {}) => {
    const url = new URL(target);
    if (url.origin !== origin || url.username || url.password || !url.pathname.startsWith("/session/")) {
      throw Error("Unexpected miner URL");
    }
    return new Promise((resolveResponse, reject) => {
      const req = https.request(url, {
        method: init.method || "GET", headers: Object.fromEntries(new Headers(init.headers)),
        agent: false, family: pin.family, autoSelectFamily: false,
        lookup: (_host, _opts, callback) => callback(null, pin.address, pin.family),
        signal: init.signal || AbortSignal.timeout(120_000),
      }, res => {
        if (res.statusCode >= 300 && res.statusCode < 400) {
          res.destroy();
          reject(Error("Miner redirect refused"));
          return;
        }
        const chunks = [];
        let size = 0;
        res.on("data", chunk => {
          size += chunk.length;
          if (size > 4_000_000) res.destroy(Error("Miner reply too large"));
          else chunks.push(chunk);
        });
        res.on("error", reject);
        res.on("end", () => {
          const body = [204, 205].includes(res.statusCode) ? null : Buffer.concat(chunks);
          resolveResponse(new Response(body, { status: res.statusCode, headers: res.headers }));
        });
      });
      req.on("error", reject);
      req.end(init.body);
    });
  };
}
