# FLOP DID Chat 0.3.0 · Testnet

Discutez avec un modèle du Testnet via le gateway public ou un mineur de votre choix. Talisman conserve la clé de votre compte sr25519 ou Ed25519. L’interface française et anglaise tourne sur votre ordinateur. Les tests hors ligne et les lectures publiques sont validés. Un premier crédit et un premier chat réglé avec un vrai compte Talisman restent à valider. [Validation](VALIDATION.md) · [English](README.md) · [DID auteur](IDENTITY.md)

## Démarrer

Installez Python 3.11 ou ultérieur, Node.js 24 avec npm et l’extension Talisman. Sous Windows, exécutez **INSTALLER_WINDOWS.cmd**, puis **LANCER.cmd**. Sous Linux ou macOS, lancez ces commandes dans le dépôt.

~~~sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes --only-binary=:all: -r requirements.lock.txt
npm ci --ignore-scripts --no-audit --no-fund
python flop_chat.py --open-browser
~~~

Ouvrez l’adresse locale affichée dans le navigateur équipé de Talisman. Cliquez sur **Connecter Talisman**, choisissez le compte et son type de signature, relisez le défi puis signez-le. Pour un DID historique, sélectionnez Ed25519 si le type indiqué par l’extension est incorrect. Les options `--expected-address <SS58>` et `--expected-did <did:key:…>` peuvent verrouiller l’identité, ensemble ou séparément. [Guide d’import d’un DID existant](https://github.com/AMCONSEIL/did-to-talisman)

## Obtenir des FLOP de test

**Vérifier le solde et le faucet** affiche le solde libre au dernier bloc finalisé, le budget restant et la condition de dépense. Lorsque le robinet est ouvert, **Réclamer +10 FLOP** demande une signature de message à Talisman. Le plafond est de 10 FLOP par période glissante de 24 heures. Un crédit accepté affiche son statut et un lien vers sa transaction. Un HTTP 429 affiche le délai annoncé. Si le faucet répond `agent_spend_missing`, une dépense réglée sur le réseau débloque le crédit suivant. Une réponse perdue laisse le crédit en attente sur disque et bloque le double envoi. [Explorateur Testnet](https://testnet.flopscan.io)

## Envoyer un message

**Gateway.** Le menu affiche le catalogue texte en direct. Le 27 novembre, l’inscription répondait HTTP 404. La connexion locale, le faucet et le mode direct restent utilisables. Lorsque l’inscription ouvrira, le chat contrôlera le défi, le modèle autorisé, le quota et les reçus avant envoi. L’admission d’un mineur nécessite un reçu qui l’identifie. [Catalogue public](https://gateway.testnet.flop.network/v1/models)

**Direct.** Demandez à l’opérateur du mineur son adresse Testnet et son origine HTTPS. Créez `.local/direct-miners.json` avec un tableau de cette forme, remplacez les valeurs d’exemple et relancez le chat.

~~~json
[{"name":"Mon mineur","address":"REMPLACER_PAR_SS58_TESTNET","endpoint":"https://miner.example.org"}]
~~~

Vous pouvez aussi renseigner `enclaveKey` avec la clé de session confirmée par l’opérateur (64 caractères hexadécimaux minuscules). Dans **Réglages**, choisissez **Direct**, puis un modèle du catalogue ou son identifiant exact en minuscules, par exemple `qwen/qwen3-14b`. Envoyez le message, sélectionnez le mineur, ajustez la réserve et cliquez sur **Voir les coûts**. L’application vérifie une preuve de disponibilité signée sur un défi neuf, la version du worker et l’identité du modèle au bloc finalisé avant de demander la signature d’ouverture.

Vérifiez l’origine HTTPS, le modèle, le canal et le coût. Par défaut, la réserve vaut 0,05 FLOP, la réponse est limitée à 256 tokens (1024 maximum) et la durée du canal est de 1200 secondes. Le plafond local des frais d’ouverture vaut 0,02 FLOP. Talisman signe `computeChannel.forceOpen` pour un tour. Le SDK utilise une clé éphémère pour la session et le mineur soumet le règlement coopératif. **Vérifier les reçus** recherche à finalité le canal, le hash de règlement, les montants et les Gn réglés. La réponse vérifiée peut arriver avant le règlement. [Sécurité et reprise](SECURITY.md)
