import { short, rawFlop, amount, metrics, contextFor, canSend, safeConversationStore, substrateCandidates } from "./core.js";
const $ = id => document.getElementById(id);
const TEXT = {
 close: ["Fermer", "Close"],
 directTitle: ["Session directe", "Direct session"],
 directInfo: ["Le gateway est bloqué pour ce message. Le direct utilise le solde de votre compte Devnet et transmet le contexte affiché au mineur choisi.", "The gateway is unavailable for this message. Direct uses your devnet wallet balance and shares the displayed conversation context with the selected miner."],
 directMiner: ["Mineur", "Miner"],
 directPrepare: ["Voir les coûts", "Review costs"],
 directChecking: ["Vérification du mineur et calcul des frais…", "Checking the miner and estimating fees…"],
 directReview: ["Vérifiez ces montants avant de signer l’ouverture.", "Review these amounts before signing the opening transaction."],
 directSigning: ["En attente de la signature Talisman…", "Waiting for your Talisman signature…"],
 directSubmitted: ["Ouverture du canal en cours…", "Opening the channel…"],
 directOpened: ["Canal soumis. En attente du mineur…", "Channel submitted. Waiting for the miner…"],
 directVerified: ["Réponse vérifiée. Règlement en cours…", "Reply verified. Waiting for settlement…"],
 directSettled: ["Règlement confirmé sur la chaîne.", "Settlement confirmed on-chain."],
 directReleased: ["Réserve remboursée sur la chaîne. Les frais d’ouverture restent dus.", "Escrow refunded on-chain. The opening fee still applies."],
 directReconcile: ["Vérifiez le canal avant un nouvel envoi.", "Check the channel before another send."],
 directStopped: ["Préparation interrompue avant envoi. Vérifiez la disponibilité du mineur, votre solde et les frais.", "Preparation stopped before submission. Check miner availability, your balance and fees."],
 directReserve: ["Réserve du canal", "Channel escrow"],
 directFee: ["Frais d’ouverture estimés", "Estimated opening fee"],
 directTotal: ["Total estimé", "Estimated total"],
 directFeeCap: ["Plafond accepté pour l’estimation des frais", "Accepted fee estimate ceiling"],
 directExplorer: ["Voir le règlement sur l’explorateur", "View settlement in the explorer"],
 directLocalLogin: ["Compte vérifié. Gateway indisponible. Le chat proposera une session directe à l’envoi.", "Account verified. Gateway unavailable. The chat will offer a direct session when you send."],
connectionHelp:["Sélectionnez le compte lié à votre DID. Le chat vérifie sa signature Ed25519 avant de valider la connexion.","Select the account linked to your DID. The chat verifies its Ed25519 signature before accepting the connection."],
settingsLabel:["Réglages","Settings"],
noCompatibleAccounts:["Aucun compte Substrate compatible partagé. Dans Talisman, autorisez le compte existant lié à votre DID.","No compatible Substrate account shared. In Talisman, allow the existing account linked to your DID."],
accountsEmpty:["Aucun compte chargé","No account loaded"],
selectAccount:["Compte","Account"],
applyLimits:["Appliquer","Apply"],
budgetInfo:["Réglage de cette application, pas une règle de FLOP. 0,9 FLOP est proposé pour le premier test ; vous pouvez ajuster ce plafond ci-dessous. Le compteur inclut les coûts connus et les appels en attente depuis le démarrage du serveur.","This is an app setting, not a FLOP rule. 0.9 FLOP is suggested for the first test; you can adjust this limit below. The counter includes known costs and pending calls since server startup."],
emptyReceipts:["Aucune requête.","No requests yet."],
reserved:["En réservation","Reserved"],
settled:["Coût confirmé (reçu)","Confirmed cost (receipt)"],
apiQuota:["Quota API restant","API quota remaining"],
historyPrivacy:["Messages enregistrés sur cet appareil uniquement.","Messages saved on this device only."],
newChat:["Nouvelle conversation","New conversation"],
conversations:["Conversations","Conversations"],
remember:["Conserver l’historique ici","Keep history on this device"],
clearHistory:["Effacer les conversations locales","Clear local conversations"],
author:["DID auteur","Author DID"],
model:["Modèle","Model"],
loadingModels:["Chargement du catalogue…","Loading model catalog…"],
connect:["Connecter Talisman","Connect Talisman"],
devnet:["Devnet · jetons de test sans valeur monétaire.","Devnet · test tokens with no monetary value."],
local:["Application locale","Local application"],
welcomeTitle:["FLOP Chat","FLOP Chat"],
welcomeCopy:["Connectez Talisman pour envoyer un message.","Connect Talisman to send a message."],
working:["Requête envoyée. En attente du réseau…","Request sent. Waiting for the network…"],
unresolved:["Une requête reste à réconcilier. Vérifiez son reçu avant tout nouvel envoi.","A request still needs reconciliation. Check its receipt before sending another."],
checkReceipt:["Vérifier les reçus","Check receipts"],
promptLabel:["Votre message","Your message"],
promptPlaceholder:["Écrivez votre message…","Write your message…"],
responseLength:["Tokens de sortie maximum","Maximum output tokens"],
requestLimit:["Votre plafond par envoi (FLOP)","Your per-request cap (FLOP)"],
sessionLimit:["Votre plafond pour ce chat (FLOP)","Your cap for this chat (FLOP)"],
sendHint:["Entrée pour envoyer · Maj + Entrée pour une nouvelle ligne","Enter to send · Shift + Enter for a new line"],
usageTitle:["Consommation","Usage"],
quotaUnits:["Fourni par FLOP. Ce n’est pas le solde du wallet.","Reported by FLOP. This is not your wallet balance."],
expires:["Expiration de l’accès","Access expires"],
tokens:["Tokens utilisés","Tokens used"],
usageScope:["Requêtes envoyées par ce chat uniquement. « — » : montant inconnu.","Requests sent by this chat only. “—”: unknown amount."],
sessionBudget:["Utilisé ou en attente / votre plafond","Used or pending / your cap"],
activity:["Reçus","Receipts"],
connectedIdentity:["Compte connecté","Connected account"],
notConnected:["Aucun compte connecté","No connected account"],
disconnect:["Déconnecter localement","Disconnect locally"],
needWallet:["Préparer mon DID dans Talisman","Prepare my DID for Talisman"],
yourIdentity:["Connexion Talisman","Connect Talisman"],
walletExplanation:["Autorisez votre compte existant, puis vérifiez le message avant de signer.","Allow your existing account, then review the message before signing."],
allowTalisman:["Autoriser Talisman","Authorize Talisman"],
didOptional:["DID à vérifier (facultatif)","DID to verify (optional)"],
reviewChallenge:["Afficher le message à signer","Review the signing message"],
challengeInfo:["Signature de connexion uniquement. Elle ne prolonge ni le quota ni sa durée.","Login signature only. It does not renew or extend the allowance."],
signChallenge:["Signer dans Talisman","Sign in Talisman"],
you:["Vous","You"],
assistant:["FLOP","FLOP"],
copy:["Copier","Copy"],
copied:["Copié","Copied"],
noCatalog:["Catalogue indisponible","Catalog unavailable"],
emptyCatalog:["Aucun modèle disponible","No available models"],
oneModel:["Votre accès autorise ce modèle uniquement.","Your access allows this model only."],
notAuthorized:["non autorisé","not authorized"],
signinFirst:["Connectez Talisman pour envoyer votre premier message.","Connect Talisman to send your first message."],
connected:["Compte vérifié. Vous pouvez envoyer un message.","Account verified. You can send a message."],
readinessError:["La connexion n’est pas encore prête. Actualisez le quota et les reçus.","The connection is not ready yet. Refresh quota and receipts."],
noTalisman:["Talisman n’est pas disponible dans ce navigateur. Ouvrez cette page dans le navigateur où l’extension est installée.","Talisman is unavailable in this browser. Open this page in the browser with the extension installed."],
noAccounts:["Aucun compte partagé. Dans Talisman, autorisez votre compte pour ce site, puis cliquez à nouveau sur « Autoriser Talisman ».","No account shared. In Talisman, allow your account for this site, then click “Authorize Talisman” again."],
confirmClear:["Effacer les conversations de ce navigateur ? Les reçus et les traitements distants seront conservés.","Clear this browser’s conversations? Receipts and remote work will be preserved."],
cleared:["Conversations locales effacées.","Local conversations cleared."],
historyWarning:["Cet appareil conservera vos prompts et vos réponses. N’activez pas cette option sur un ordinateur partagé.","This device will store prompts and answers. Keep this off on a shared computer."],
limitsSaved:["Limites appliquées. Chaque envoi reste manuel.","Limits applied. Every request remains manual."],
errorLabel:["Requête non aboutie","Request unsuccessful"],
reconcileOnly:["Réponse non récupérée. Vérifiez le reçu ; aucune nouvelle soumission automatique.","Response not recovered. Check the receipt; there is no automatic resubmission."],
ledgerNotice:["Observation du registre du gateway, pas une preuve indépendante de paiement sur chaîne.","Gateway ledger observation, not independent proof of an on-chain payment."],
refreshDone:["Quota et reçus actualisés.","Quota and receipts refreshed."],
localOnly:["Historique local","Local history"],
reservedLabel:["Réservation","Reservation"],
settledLabel:["Règlement","Settlement"],
unknown:["inconnu","unknown"],
released:["Libéré","Released"],
settledState:["Réglé","Settled"],
reservedState:["Réservé","Reserved"],
estimated:["À réconcilier","Reconciling"],
unknownState:["À vérifier","Needs checking"],
details:["Détails du reçu","Receipt details"],
lastResponse:["HTTP","HTTP"],
pastReceipt:["Reçu du compte","Account receipt"],
context:["messages dans le contexte","messages in context"],
shortReply:["Réponse limitée par le plafond de tokens.","Response reached the output token limit."],
cooldown:["Prochain envoi disponible dans","Next send available in"],
seconds:["s","s"],
keepKey:["L’accès API reste uniquement en mémoire du serveur local.","API access stays only in the local server’s memory."]
};
const ERRORS = {
 DIRECT_NOT_ALLOWED: ["Ce message n’est pas éligible au direct.", "This message is not eligible for direct mode."],
 DIRECT_MINER_INVALID: ["Choisissez un mineur distinct du compte client.", "Choose a miner different from the client account."],
 DIRECT_PREVIEW_EXPIRED: ["L’estimation a expiré. Recommencez la préparation.", "The quote expired. Prepare it again."],
 DIRECT_UNAVAILABLE: ["Installez les dépendances Node du mode direct.", "Install the Node dependencies for direct mode."],
 QUOTA_EXHAUSTED: ["Le quota du gateway est épuisé.", "The gateway quota is exhausted."],
REQUEST_CAP_EXCEEDS_SESSION:["Le plafond par message dépasse votre plafond total. Ajustez les deux valeurs.","Your per-request cap exceeds your total cap. Adjust both values."],
overloaded:["Capacité FLOP saturée. Aucun nouvel essai automatique.","FLOP is at capacity. No automatic retry."],
rate_limit_exceeded:["Limite de fréquence FLOP atteinte. Attendez avant un nouvel envoi.","FLOP rate limit reached. Wait before another send."],
GATEWAY_UNREACHABLE:["Le gateway n’a pas répondu. Le résultat peut être inconnu : vérifiez le reçu.","The gateway did not respond. The outcome may be unknown: check the receipt."],
RECONCILE_REQUIRED:["Un résultat reste à vérifier. Actualisez les reçus avant de continuer.","An outcome needs checking. Refresh receipts before continuing."],
SESSION_LIMIT:["Le plafond local de cette session est atteint. Revoyez explicitement vos limites pour continuer.","This local session limit is reached. Explicitly review your limits before continuing."],
LIMIT_INVALID:["Choisissez des plafonds positifs et finis. Le plafond total doit couvrir les montants déjà engagés. Vérifiez aussi la longueur de réponse.","Choose positive, finite caps. The total cap must cover amounts already committed. Also check the output token limit."],
MODEL_NOT_AUTHORIZED:["Ce modèle n’est pas autorisé par votre accès actuel.","Your current access does not allow this model."],
MODEL_NOT_AVAILABLE:["Le modèle autorisé n’est pas actuellement annoncé par le gateway.","The allowed model is not currently advertised by the gateway."],
CHALLENGE_INVALID:["Le message de connexion ne correspond pas au réseau ou au compte attendu. Ne le signez pas.","The login message does not match the expected network or account. Do not sign it."],
EXPECTED_DID_MISMATCH:["Ce compte ne correspond pas au DID personnel attendu.","This account does not match the expected personal DID."],
DID_MISMATCH:["Le DID ne correspond pas à la clé publique du compte choisi.","The DID does not match the selected account’s public key."],
SIGNATURE_INVALID:["La signature Ed25519 ne correspond pas au message et au compte.","The Ed25519 signature does not match the message and account."],
CONNECT_REQUIRED:["Connectez ou reconnectez le même compte avec Talisman.","Connect or reconnect the same account with Talisman."],
devnet_enrollment_expired:["Accès gateway expiré. Le chat peut proposer une session directe.","Gateway access expired. The chat can offer a direct session."],
devnet_allowance_exhausted:["L’allocation de ce compte est épuisée. Une reconnexion ne la renouvelle pas.","This account’s allowance is exhausted. Reconnecting does not renew it."],
wallet_unfunded:["Ce compte n’a pas le solde minimal requis par FLOP. Vérifiez son solde sur le réseau de test.","This account lacks FLOP’s required minimum balance. Check its test-network balance."],
api_key_expired:["L’accès a expiré. Une nouvelle signature ne prolonge pas l’allocation.","Access has expired. A new signature does not extend the allowance."],
CHALLENGE_EXPIRED:["Le message a expiré ou a déjà été soumis. Demandez une nouvelle connexion du même compte.","The message expired or was already submitted. Start a new connection for the same account."],
MESSAGES_INVALID:["Conversation trop longue ou message invalide. Commencez une nouvelle conversation.","The conversation is too long or contains an invalid message. Start a new conversation."],
COOLDOWN:["Attendez la fin du délai avant un nouvel envoi.","Wait for the cooldown before sending again."],
LOCAL_ERROR:["Erreur locale. Aucun nouvel essai automatique ; vérifiez les reçus.","Local error. No automatic retry; check receipts."],
OUTCOME_UNKNOWN:["Résultat inconnu : vérifiez les reçus avant de continuer.","Unknown outcome: check receipts before continuing."],
RECEIPTS_INVALID:["Le format des reçus ne correspond pas au contrat attendu. Aucun envoi autorisé.","The receipt format differs from the expected contract. Sending remains blocked."],
ED25519_REQUIRED:["Sélectionnez le compte Ed25519 lié à votre DID.","Select the Ed25519 account linked to your DID."]
};
let lang = "en", state = null, busy = false, extension = null, challenge = null, accounts = [];
let directPoll;
let conversations = [], activeId = null, requestLimit = "0.9", maxTokens = 48;
const csrf = document.querySelector('meta[name="chat-local"]').content;
const STORE = "flop-did-chat-history-v1";
try {
 lang = localStorage.getItem("flop-did-chat-language") || "en";
 const saved = JSON.parse(localStorage.getItem(STORE) || "null");
 if (saved?.schema === 1 && Array.isArray(saved.conversations)) {
  conversations = saved.conversations.filter(c => typeof c.id === "string" && Array.isArray(c.turns)).slice(-100);
  $("remember").checked = true;
 }
} catch {}
if (!["fr", "en"].includes(lang)) lang = "en";
function t(key) { return TEXT[key]?.[lang === "fr" ? 0 : 1] || key; }
function formatError(error) {
 const code = error?.error || error?.code || "LOCAL_ERROR";
 const translated = ERRORS[code]?.[lang === "fr" ? 0 : 1];
 const detail = typeof error?.detail === "string" ? error.detail : "";
 return (translated || code) + (detail ? " — " + detail : "");
}
function el(tag, className, text) {
 const element = document.createElement(tag);
 if (className) element.className = className;
 if (text !== undefined) element.textContent = text;
 return element;
}
function icon(name) {
 const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
 const use = document.createElementNS(svg.namespaceURI, "use");
 use.setAttribute("href", "#i-" + name); svg.append(use); return svg;
}
async function api(path, payload = {}) {
 const response = await fetch("/api/" + path, { method: "POST",
  headers: { "Content-Type": "application/json", "X-Chat-Local": csrf },
  body: JSON.stringify(payload), signal: AbortSignal.timeout(path === "chat" ? 180000 : 90000) });
 const data = await response.json();
 if (!response.ok) throw data;
 return data;
}
function banner(text, kind = "") {
 $("banner").textContent = text; $("banner").className = "banner " + kind; $("banner").hidden = !text; $("banner").dataset.cooldown = "false";
}
let toastTimer;
function toast(text) { $("toast").textContent = text; $("toast").hidden = false; clearTimeout(toastTimer); toastTimer = setTimeout(() => $("toast").hidden = true, 4500); }
function save() {
 try {
  if ($("remember").checked) localStorage.setItem(STORE, JSON.stringify({ schema: 1, conversations: safeConversationStore(conversations) }));
  else localStorage.removeItem(STORE);
 } catch { toast(lang === "fr" ? "Stockage local indisponible." : "Local storage unavailable."); }
}
function newConversation() {
 const c = { id: crypto.randomUUID(), title: t("newChat"), account: state?.account?.address || null, turns: [] };
 conversations.push(c); activeId = c.id; save(); renderConversations(); renderMessages(); renderDirect(); updateSend();
 return c;
}
function currentConversation() { return conversations.find(c => c.id === activeId) || newConversation(); }
function renderConversations() {
 const list = $("conversation-list"); list.replaceChildren();
 const account = state?.account?.address;
 const visible = conversations.filter(c => !account || !c.account || c.account === account);
 for (const c of [...visible].reverse()) {
  const button = el("button", "conversation-item" + (c.id === activeId ? " active" : ""));
  const title = c.turns.length ? c.title : t("newChat");
  button.append(icon("chat"), el("span", "", title));
  button.title = title;
  button.addEventListener("click", () => { if (!busy) { activeId = c.id; renderConversations(); renderMessages(); renderDirect(); updateSend(); } });
  list.append(button);
 }
}
function renderBody(container, text) {
 // Plain text and fenced code only; no remote HTML, scripts, images or link execution.
 const parts = String(text).split(/~~~|```/);
 parts.forEach((part, index) => {
  if (index % 2) { const pre = el("pre"); pre.append(el("code", "", part.replace(/^[a-z0-9+#_-]*\n/i, ""))); container.append(pre); }
  else if (part) container.append(el("p", "", part));
 });
}
function appendMessage(role, text, turn, error = false) {
 const item = el("article", "message " + role + (error ? " error" : ""));
 const head = el("div", "message-head");
 head.append(el("span", "avatar", role === "user" ? (lang === "fr" ? "V" : "Y") : "f."),
             el("span", "", role === "user" ? t("you") : t("assistant")));
 const body = el("div", "message-body"); renderBody(body, text);
 item.append(head, body);
 if (role !== "user") {
  const meta = el("div", "message-meta");
  if (turn?.usage?.total_tokens !== undefined) meta.append(el("span", "", amount(turn.usage.total_tokens, lang) + " tokens"));
  if (turn?.route === "direct") meta.append(el("span", "", t("directTitle")));
  if (turn?.finish === "length") meta.append(el("span", "", t("shortReply")));
  if (turn?.id) meta.append(el("code", "", short(turn.id, 10, 5)));
  const copy = el("button", "copy-button"); copy.append(icon("copy"), el("span", "", t("copy")));
  copy.addEventListener("click", async () => { try { await navigator.clipboard.writeText(text); toast(t("copied")); } catch { toast(lang === "fr" ? "Copie indisponible." : "Copy unavailable."); } });
  meta.append(copy); item.append(meta);
 }
 $("messages").append(item);
}
function renderMessages() {
 $("messages").replaceChildren();
 const c = conversations.find(x => x.id === activeId);
 $("welcome").hidden = Boolean(c?.turns.length);
 for (const turn of c?.turns || []) {
  appendMessage("user", turn.prompt, turn);
  if (typeof turn.answer === "string") appendMessage("assistant", turn.answer, turn);
  else if (turn.error) appendMessage("assistant", turn.error, turn, true);
  else if (turn.state === "pending" && !busy) appendMessage("assistant", t("reconcileOnly"), turn, true);
 }
 $("working").hidden = !busy || $("direct-dialog").open;
 const context = c ? contextFor(c, "").length - 1 : 0;
 $("context-count").textContent = context ? context + " " + t("context") : "";
}
function receiptState(row) {
 return row.state === "released" ? t("released") : row.state === "settled" ? t("settledState")
  : row.state === "reserved" ? t("reservedState") : row.state === "estimated" ? t("estimated") : t("unknownState");
}
function renderReceipts() {
 const own = state?.requests || [], external = state?.recent_receipts || [];
 const combined = [...own, ...external].sort((a, b) => (b.created_at || 0) - (a.created_at || 0)).slice(0, 30);
 $("receipt-count").textContent = String(combined.length); $("receipts").replaceChildren();
 if (!combined.length) { $("receipts").append(el("div", "empty-receipts", t("emptyReceipts"))); return; }
 for (const row of combined) {
  const card = el("article", "receipt"), top = el("div", "receipt-top");
  const isOwn = own.some(r => r.request_id === row.request_id);
  top.append(el("strong", "", row.created_at ? new Date(row.created_at).toLocaleTimeString(lang, { hour: "2-digit", minute: "2-digit" }) : "—"),
   el("span", "badge " + (row.state === "released" ? "warning" : row.state !== "settled" ? "pending" : ""), receiptState(row)));
  card.append(top, el("code", "", row.request_id));
  if (!isOwn) card.append(el("div", "micro", t("pastReceipt")));
  const settlement = row.settled_spend_raw !== null && row.settled_spend_raw !== undefined ? rawFlop(String(row.settled_spend_raw)) : row.settled_spend;
  const summary = el("div", "receipt-summary", t("reservedLabel") + " : " + amount(row.reserved_spend, lang)
   + " · " + t("settledLabel") + " : " + (settlement === null || settlement === undefined ? t("unknown") : amount(settlement, lang)) + " FLOP");
  if (row.route === "direct") {
   summary.append(el("div", "", t("directTitle") + (row.chain_state ? " · " + row.chain_state : "")));
   if (/^0x[0-9a-f]{64}$/.test(row.terminal_event)) {
    const link = el("a", "", t("directExplorer"));
    link.href = "https://explorer.devnet.flop.network/transactions/" + row.terminal_event;
    link.target = "_blank"; link.rel = "noreferrer";
    summary.append(link);
   }
  }
  if (row.response_status) summary.append(el("div", "", "HTTP " + row.response_status));
  card.append(summary);
  const details = el("details"), title = el("summary", "", t("details"));
  const safe = Object.fromEntries(["request_id", "model", "state", "response_status", "reserved_spend", "settled_spend", "settled_spend_raw", "terminal_event", "channel_id", "receipt_error", "miner", "opening_tx", "opening_fee_estimate_raw", "miner_paid_raw", "burned_raw"].filter(k => k in row).map(k => [k, row[k]]));
  details.append(title, el("pre", "", JSON.stringify(safe, null, 2)), el("p", "micro", t("ledgerNotice")));
  card.append(details); $("receipts").append(card);
 }
}
function renderState(next) {
 state = next;
 $("author-did").textContent = state.author_did;
 $("quota").textContent = state.auth ? amount(state.auth.remaining_quota, lang, 4) : "—";
 $("expires").textContent = state.auth?.expires_at ? new Date(state.auth.expires_at).toLocaleString(lang, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—";
 $("wallet-address").textContent = state.account?.address || t("notConnected");
 $("wallet-did").textContent = state.account?.did || "";
 $("connect-label").textContent = state.account ? short(state.account.address, 6, 5) : t("connect");
 $("disconnect").hidden = !state.account;
 $("did-input").value = state.expected_did || $("did-input").value;
 const selected = $("model-select").value, select = $("model-select"); select.replaceChildren();
 for (const model of state.models) {
  const option = el("option", "", model.name);
  option.value = model.id;
  option.disabled = Boolean(state.auth && state.auth.model !== model.id);
  if (option.disabled) option.textContent += " · " + t("notAuthorized");
  select.append(option);
 }
 if (state.direct?.available && state.gateway_block && !state.models.some(m => m.id === "qwen/qwen2.5-0.5b-instruct")) {
  const option = el("option", "", "Qwen2.5 0.5B Instruct (devnet)");
  option.value = "qwen/qwen2.5-0.5b-instruct";
  select.append(option);
 }
 if (!select.options.length) select.append(el("option", "", state.models_checked_at ? t("emptyCatalog") : t("noCatalog")));
 else select.value = state.auth?.model || ([...select.options].some(o => o.value === selected) ? selected : select.options[0].value);
 $("model-access").textContent = state.auth ? t("oneModel") : "";
 const numbers = metrics(state.requests);
 $("settled").textContent = amount(numbers.settled, lang) + (numbers.unknownSettled ? " + ?" : "") + (numbers.settled !== null ? " FLOP" : "");
 $("settled").title = numbers.settledExactRaw ? rawFlop(numbers.settledExactRaw) + " FLOP" : t("ledgerNotice");
 $("reserved").textContent = amount(numbers.reserved, lang) + (numbers.reservationUnknown ? " + ?" : "") + (numbers.reserved !== null ? " FLOP" : "");
 $("tokens").textContent = amount(numbers.tokens, lang, 0);
 $("budget-value").textContent = amount(state.limits.session_committed, lang) + " / " + amount(state.limits.session_cap, lang) + " FLOP";
 requestLimit = state.limits.request_cap;
 $("request-limit").value = requestLimit;
 $("session-limit").value = state.limits.session_cap;
 $("reconcile-note").hidden = !state.unresolved.length;
 $("reconcile").disabled = directActive(state.direct?.job?.phase);
 renderReceipts(); renderConversations(); renderDirect(); updateSend();
}
function translate() {
 document.documentElement.lang = lang;
 document.querySelectorAll("[data-i18n]").forEach(node => node.textContent = t(node.dataset.i18n));
 document.querySelectorAll("[data-placeholder]").forEach(node => node.placeholder = t(node.dataset.placeholder));
 $("lang").textContent = lang === "fr" ? "EN" : "FR";
 $("lang").setAttribute("aria-label", lang === "fr" ? "Switch to English" : "Passer en français");
 $("model-select").setAttribute("aria-label",lang === "fr" ? "Modèle" : "Model");
 $("close-wallet").setAttribute("aria-label",lang === "fr" ? "Fermer" : "Close");
 $("refresh").setAttribute("aria-label", lang === "fr" ? "Actualiser le quota et les reçus" : "Refresh quota and receipts");
 $("send").setAttribute("aria-label", lang === "fr" ? "Envoyer" : "Send");
 $("limit-label").textContent = t("settingsLabel");
 $("settings-toggle").title = maxTokens + " tokens · " + amount(requestLimit, lang) + " FLOP max.";
 if (state) renderState(state);
 renderConversations(); renderMessages();
}
function updateSend() {
 $("send").disabled = !canSend(state, busy, $("prompt").value, $("model-select").value);
 $("new-chat").disabled = busy;
 $("connect").disabled = busy;
 $("model-select").disabled = busy || !$("model-select").options.length;
 $("working").hidden = !busy || $("direct-dialog").open;
 const remaining = Math.ceil((state?.cooldown_until || 0) - Date.now() / 1000);
 if (remaining > 0 && !busy) {
  banner(t("cooldown") + " " + remaining + " " + t("seconds") + ". " + (state.last_error ? formatError(state.last_error) : ""), "error");
  $("banner").dataset.cooldown = "true";
 } else if ($("banner").dataset.cooldown === "true") banner("");
}
async function refreshState(showToast = true) {
 $("refresh").disabled = true;
 try {
  const row = state?.requests.find(r => r.route === "direct" && state.unresolved.includes(r.request_id));
  renderState(row ? await api("direct/reconcile", { id: row.request_id }) : await api("refresh"));
  if (showToast) toast(t("refreshDone"));
 }
 catch (error) { banner(formatError(error), "error"); }
 finally { $("refresh").disabled = false; }
}
$("connect").addEventListener("click", () => { $("wallet-error").hidden = true; $("wallet-dialog").showModal(); });
$("close-wallet").addEventListener("click", () => $("wallet-dialog").close());
$("load-accounts").addEventListener("click", async () => {
 $("wallet-error").hidden = true;
 $("prepare-challenge").disabled = true;
 $("challenge-section").hidden = true; challenge = null;
 $("load-accounts").disabled = true;
 $("account-select").replaceChildren(el("option", "", t("accountsEmpty")));
 try {
  const provider = window.injectedWeb3?.talisman;
  if (!provider) throw { detail: t("noTalisman"), error: "" };
  extension = await provider.enable("FLOP DID Chat");
  if (!extension.signer?.signRaw) throw { error: "ED25519_REQUIRED" };
  const available = await extension.accounts.get();
  accounts = substrateCandidates(available);
  if (!accounts.length) throw { detail: t(Array.isArray(available) && available.length ? "noCompatibleAccounts" : "noAccounts"), error: "" };
  $("account-select").replaceChildren();
  for (const account of accounts) {
   const option = el("option", "", (account.name || t("selectAccount")) + " · " + short(account.address));
   option.value = account.address; $("account-select").append(option);
  }
  $("prepare-challenge").disabled = false;
 } catch (error) { $("wallet-error").textContent = error.detail || formatError(error); $("wallet-error").hidden = false; } finally { $("load-accounts").disabled = false; }
});
$("prepare-challenge").addEventListener("click", async () => {
 $("prepare-challenge").disabled = true; $("wallet-error").hidden = true;
 try {
  challenge = await api("challenge", { address: $("account-select").value, did: $("did-input").value.trim() });
  $("challenge-account").textContent = challenge.account.did + "\n" + challenge.account.address;
  $("challenge-message").textContent = challenge.message;
  $("challenge-section").hidden = false; $("sign-challenge").disabled = false;
 } catch (error) { $("wallet-error").textContent = formatError(error); $("wallet-error").hidden = false; }
 finally { $("prepare-challenge").disabled = false; }
});
$("sign-challenge").addEventListener("click", async () => {
 $("sign-challenge").disabled = true; $("wallet-error").hidden = true;
 try {
  if (!challenge || challenge.expires_at <= Date.now()) throw { error: "CHALLENGE_EXPIRED" };
  const data = "0x" + Array.from(new TextEncoder().encode(challenge.message), b => b.toString(16).padStart(2, "0")).join("");
  const signed = await extension.signer.signRaw({ address: $("account-select").value, data, type: "bytes" });
  renderState(await api("enroll", { signature: signed.signature }));
  const c = currentConversation();
  if (c.account && c.account !== state.account.address) newConversation();
  else { c.account = state.account.address; save(); }
  $("wallet-dialog").close();
  banner(state.connected ? t("connected") : state.gateway_block ? t("directLocalLogin") : t("readinessError"), state.connected ? "success" : "");
  renderMessages();
 } catch (error) { $("wallet-error").textContent = error?.message || formatError(error); $("wallet-error").hidden = false;
  try { renderState(await (await fetch("/api/state")).json()); } catch {}
 }
});
$("account-select").addEventListener("change", () => { challenge = null; $("challenge-section").hidden = true; });
$("did-input").addEventListener("input", () => { challenge = null; $("challenge-section").hidden = true; });
$("chat-form").addEventListener("submit", async event => {
 event.preventDefault();
 const text = $("prompt").value.trim(), model = $("model-select").value;
 if (!canSend(state, busy, text, model)) return;
 const c = currentConversation();
 if (c.account && c.account !== state.account.address) { banner(t("readinessError"), "error"); return; }
 const messages = contextFor(c, text);
 const turn = { id: "chat-" + crypto.randomUUID().replaceAll("-", ""), prompt: text, state: "pending" };
 c.account = state.account.address; c.turns.push(turn);
 if (c.turns.length === 1) c.title = text.slice(0, 42);
 busy = true; save(); $("prompt").value = ""; banner(""); renderConversations(); renderMessages(); updateSend();
 document.querySelector(".chat-area").scrollTop = document.querySelector(".chat-area").scrollHeight;
 try {
  const result = await api("chat", { request_id: turn.id, model, messages, max_tokens: maxTokens, max_cost_flop: requestLimit });
  if (result.completion) { turn.answer = result.completion.text; turn.usage = result.completion.usage; turn.finish = result.completion.finish_reason; turn.state = "answered"; }
  else { turn.error = result.error ? formatError(result.error) : t("reconcileOnly"); turn.state = "failed"; }
  if (result.state) renderState(result.state);
  if (result.error) banner(formatError(result.error), "error");
 } catch (error) {
  turn.state = "failed"; turn.error = error?.error ? formatError(error) : t("reconcileOnly");
  banner(turn.error, "error");
  try { renderState(await (await fetch("/api/state")).json()); } catch {}
 } finally {
  busy = false; save(); renderMessages(); renderDirect(); updateSend();
  document.querySelector(".chat-area").scrollTop = document.querySelector(".chat-area").scrollHeight;
 }
});
$("prompt").addEventListener("input", updateSend);
$("prompt").addEventListener("keydown", event => {
 if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); if (!$("send").disabled) $("chat-form").requestSubmit(); }
});
$("model-select").addEventListener("change", updateSend);
$("new-chat").addEventListener("click", () => { if (!busy) { newConversation(); $("prompt").focus(); } });
document.querySelectorAll(".suggestion").forEach(button => button.addEventListener("click", () => { $("prompt").value = button.dataset[lang === "fr" ? "promptFr" : "promptEn"]; updateSend(); $("prompt").focus(); }));
$("lang").addEventListener("click", () => { lang = lang === "fr" ? "en" : "fr"; try { localStorage.setItem("flop-did-chat-language", lang); } catch {} translate(); });
$("remember").addEventListener("change", () => { save(); if ($("remember").checked) toast(t("historyWarning")); });
$("clear-history").addEventListener("click", () => {
 if (busy || !confirm(t("confirmClear"))) return;
 conversations = []; activeId = null; newConversation(); save(); toast(t("cleared"));
});
$("settings-toggle").addEventListener("click", () => {
 $("settings").hidden = !$("settings").hidden;
 $("settings-toggle").setAttribute("aria-expanded", String(!$("settings").hidden));
});
$("apply-limits").addEventListener("click", async () => {
 try {
  const requestCap = Number($("request-limit").value), tokens = Number($("max-tokens").value);
  if (!Number.isFinite(requestCap) || requestCap <= 0 || !Number.isInteger(tokens) || tokens < 1 || tokens > 1024) throw { error: "LIMIT_INVALID" };
  renderState(await api("limits", { request_cap: $("request-limit").value, session_cap: $("session-limit").value }));
  requestLimit = String(requestCap); maxTokens = tokens; $("settings").hidden = true; $("settings-toggle").setAttribute("aria-expanded", "false"); translate(); toast(t("limitsSaved"));
 } catch (error) { banner(formatError(error), "error"); }
});
$("refresh").addEventListener("click", () => refreshState());
$("reconcile").addEventListener("click", () => refreshState());
$("disconnect").addEventListener("click", async () => { try { renderState(await api("disconnect")); banner(""); } catch (error) { banner(formatError(error), "error"); } });
function renderDirect() {
 const direct = state?.direct;
 const conversation = conversations.find(c => c.id === activeId);
 const turn = conversation?.turns.at(-1);
 $("direct-choice").hidden = !direct?.request_id || direct.request_id !== turn?.id || turn?.state !== "failed";
 const select = $("direct-miner"), previous = select.value;
 select.replaceChildren(el("option", "", "—"));
 select.options[0].value = "";
 for (const miner of direct?.miners || []) {
  const option = el("option", "", miner.name + " · " + short(miner.address));
  option.value = miner.address;
  option.disabled = miner.address === state.account?.address;
  select.append(option);
 }
 if ([...select.options].some(o => o.value === previous)) select.value = previous;
 $("direct-prepare").disabled = !select.value || busy;
 const job = direct?.job;
 if (!job) return;
 const phases = { checking: "directChecking", review: "directReview", signing: "directSigning",
  submitted: "directSubmitted", opened: "directOpened", verified: "directVerified",
  settled: "directSettled", released: "directReleased", reconcile: "directReconcile", stopped: "directStopped" };
 $("direct-status").textContent = t(phases[job.phase] || "directStopped");
 $("direct-sign").hidden = job.phase !== "review";
 $("direct-preview").hidden = !job.preview;
 if (job.preview) {
  const quote = job.preview;
  const display = value => rawFlop(value) + " FLOP";
  $("direct-preview").textContent = [
   job.miner.name + " · " + job.miner.address, job.miner.endpoint, quote.model + " · " + quote.precision,
   t("responseLength") + "  " + quote.max_tokens,
   t("directReserve") + "  " + display(quote.escrow), t("directFee") + "  " + display(quote.fee),
   t("directTotal") + "  " + display(quote.total), t("directFeeCap") + "  " + display(quote.fee_cap),
   quote.channel_id,
  ].join("\n");
 }
 const source = conversations.find(c => c.account === state.account?.address && c.turns.some(t => t.id === job.source_id));
 const matched = source?.turns.find(t => t.id === job.source_id);
 if (matched && typeof job.reply === "string" && matched.answer !== job.reply) {
  Object.assign(matched, { answer: job.reply, route: "direct", state: "answered" });
  delete matched.error;
  save();
  renderMessages();
 }
}

const directActive = phase => ["checking", "review", "signing", "submitted", "opened", "verified"].includes(phase);
function syncDirectPolling() {
 clearInterval(directPoll);
 busy = directActive(state?.direct?.job?.phase);
 if (busy) directPoll = setInterval(async () => {
  try {
   const next = await (await fetch("/api/state", { signal: AbortSignal.timeout(5000) })).json();
   if (next.direct?.job?.id !== state?.direct?.job?.id) return;
   if (next.direct.job.phase === "review" && state.direct.job.phase === "signing") return;
   renderState(next);
   if (!directActive(next.direct.job.phase)) syncDirectPolling();
  } catch { /* Wait for the server to report a durable outcome. */ }
 }, 1250);
 updateSend();
}
$("direct-miner").addEventListener("change", () => $("direct-prepare").disabled = !$("direct-miner").value || busy);
$("direct-prepare").addEventListener("click", async () => {
 if (busy || !state.direct.request_id || !$("direct-miner").value) return;
 busy = true;
 $("direct-error").hidden = true;
 try {
  renderState(await api("direct/prepare", { request_id: state.direct.request_id, miner: $("direct-miner").value }));
  $("direct-dialog").showModal();
  syncDirectPolling();
 } catch (error) {
  busy = false; renderDirect(); updateSend(); banner(formatError(error), "error");
 }
});
$("direct-sign").addEventListener("click", async () => {
 const job = state.direct.job;
 if (job?.phase !== "review" || $("direct-sign").disabled) return;
 $("direct-sign").disabled = true;
 $("direct-error").hidden = true;
 let handedOff = false;
 try {
  const wallet = extension || await window.injectedWeb3?.talisman?.enable("FLOP DID Chat");
  if (!wallet?.signer?.signPayload) throw { detail: t("noTalisman") };
  const { payload } = await api("direct/sign", { id: job.id });
  const { signature } = await wallet.signer.signPayload(payload);
  handedOff = true;
  renderState(await api("direct/submit", { id: job.id, signature }));
 } catch (error) {
  $("direct-error").textContent = error.message || formatError(error);
  $("direct-error").hidden = false;
  try {
   renderState(!handedOff ? await api("direct/cancel", { id: job.id })
     : await (await fetch("/api/state", { signal: AbortSignal.timeout(5000) })).json());
  } catch {}
 } finally {
  $("direct-sign").disabled = false;
  syncDirectPolling();
 }
});
async function closeDirect() {
 const job = state?.direct?.job;
 if (["checking", "review", "signing"].includes(job?.phase)) {
  try { renderState(await api("direct/cancel", { id: job.id })); }
  catch (error) { banner(formatError(error), "error"); }
 }
 $("direct-dialog").close();
 syncDirectPolling();
 renderDirect();
}
$("direct-close").addEventListener("click", closeDirect);
$("direct-dialog").addEventListener("cancel", event => { event.preventDefault(); void closeDirect(); });

async function boot() {
 translate();
 try {
  renderState(await (await fetch("/api/state")).json());
  if (!activeId) activeId = conversations.at(-1)?.id || null;
  if (!activeId) newConversation();
  renderMessages(); renderConversations();
  if (directActive(state?.direct?.job?.phase)) {
   $("direct-dialog").showModal();
   syncDirectPolling();
  }
  try { renderState(await api("models")); } catch (error) { banner(formatError(error), "error"); }
 } catch { banner(lang === "fr" ? "Serveur local indisponible. Relancez l’application." : "Local server unavailable. Restart the application.", "error"); }
}
setInterval(updateSend, 1000);
boot();
