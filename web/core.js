export function short(value, start = 7, end = 6) {
  return typeof value === "string" && value.length > start + end + 3
    ? value.slice(0, start) + "…" + value.slice(-end) : value || "";
}
export function rawFlop(raw) {
  if (typeof raw !== "string" || !/^\d+$/.test(raw)) return null;
  const number = BigInt(raw);
  const whole = number / 10n ** 18n;
  const fraction = (number % (10n ** 18n)).toString().padStart(18, "0").replace(/0+$/, "");
  return whole.toString() + (fraction ? "." + fraction : "");
}
export function amount(value, language = "fr", maximum = 6) {
  if (value === null || value === undefined || value === "" || !Number.isFinite(Number(value))) return "—";
  return new Intl.NumberFormat(language, { maximumFractionDigits: maximum }).format(Number(value));
}
export function metrics(rows) {
  let settledRaw = 0n, legacy = 0, settledKnown = 0, unknownSettled = 0;
  let reserved = 0, reservationKnown = 0, reservationUnknown = 0, tokens = 0, tokensKnown = 0;
  for (const row of rows) {
    if (row.state === "settled") {
      if (typeof row.settled_spend_raw === "string" && /^\d+$/.test(row.settled_spend_raw)) {
        settledRaw += BigInt(row.settled_spend_raw); settledKnown++;
      } else if (typeof row.settled_spend === "number" && Number.isFinite(row.settled_spend) && row.settled_spend >= 0) {
        legacy += row.settled_spend; settledKnown++;
      } else unknownSettled++;
    } else if (row.response_received && row.settled_spend === null) unknownSettled++;
    if (!["settled", "released"].includes(row.state)) {
      if (typeof row.reserved_spend === "number" && Number.isFinite(row.reserved_spend) && row.reserved_spend >= 0) {
        reserved += row.reserved_spend; reservationKnown++;
      } else reservationUnknown++;
    }
    if (Number.isInteger(row.usage?.total_tokens) && row.usage.total_tokens >= 0) {
      tokens += row.usage.total_tokens; tokensKnown++;
    }
  }
  return { settled: settledKnown ? Number(rawFlop(settledRaw.toString())) + legacy : null,
    settledExactRaw: legacy === 0 && settledKnown ? settledRaw.toString() : null, unknownSettled,
    reserved: reservationKnown ? reserved : reservationUnknown ? null : rows.length ? 0 : null,
    reservationUnknown, tokens: tokensKnown ? tokens : null };
}
export function contextFor(conversation, prompt) {
  const messages = [];
  for (const turn of conversation.turns) {
    if (typeof turn.answer === "string" && turn.state === "answered") {
      messages.push({ role: "user", content: turn.prompt }, { role: "assistant", content: turn.answer });
    }
  }
  messages.push({ role: "user", content: prompt });
  return messages;
}
export function canSend(state, busy, text, model, now = Date.now() / 1000, route = "gateway") {
  if (state?.direct?.available && (state.gateway_block || route === "direct") && state.account &&
      /^[a-z0-9][a-z0-9._-]*\/[a-z0-9][a-z0-9._-]*$/.test(model)) {
    return Boolean(!busy && text.trim() && !state.unresolved?.length
      && Number(state.limits?.session_committed) < Number(state.limits?.session_cap));
  }
  return Boolean(state?.connected && !busy && text.trim() && model === state.auth?.model
    && !state.unresolved?.length && !(state.cooldown_until > now)
    && Number(state.limits?.session_committed) < Number(state.limits?.session_cap)
    && state.auth?.expires_at > now * 1000);
}
export function safeConversationStore(conversations) {
  return conversations.map(c => ({
    id: c.id, title: c.title, account: c.account || null,
    turns: c.turns.map(t => {
      const turn = { id: t.id, prompt: t.prompt, state: t.state };
      if (typeof t.id === "string") turn.id = t.id;
      if (t.route === "direct") turn.route = "direct";
      if (typeof t.answer === "string") turn.answer = t.answer;
      if (typeof t.error === "string") turn.error = t.error;
      if (t.usage) turn.usage = { prompt_tokens: t.usage.prompt_tokens,
        completion_tokens: t.usage.completion_tokens, total_tokens: t.usage.total_tokens };
      return turn;
    })
  }));
}

// Talisman labels SS58 accounts sr25519 even when the underlying key is Ed25519.
// These are candidates only: the server checks SS58 checksum, expected DID and
// the actual wallet signature before enrollment. Metadata is not key proof.
export function substrateCandidates(available) {
  if (!Array.isArray(available)) return [];
  const seen = new Set();
  return available.filter(account => {
    if (!account || typeof account.address !== "string" || account.type === "ethereum"
        || !/^[1-9A-HJ-NP-Za-km-z]{32,64}$/.test(account.address)
        || seen.has(account.address)) return false;
    seen.add(account.address);
    return true;
  });
}
