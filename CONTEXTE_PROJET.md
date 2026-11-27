# FLOP DID Chat · état de reprise

La branche locale feat/testnet-v0.3.0 prépare la migration de la v0.2.2 vers le Testnet. Le point de retour du code est 1eacbb7. Conserver les journaux locaux pour réconcilier tout envoi en attente avant un changement de version.

Le serveur Python, l’interface EN/FR et le worker SDK 0.13.1 prennent en charge la connexion Talisman sr25519/Ed25519, le faucet à validation manuelle, le gateway et le direct sur un mineur explicitement configuré. Les données locales Testnet sont isolées du précédent registre. Les réglages directs par défaut sont 1200 secondes, 0,05 FLOP et 256 tokens. Les procédures et limites figurent dans les deux README et SECURITY.md.

Le 27 novembre 2026, les lectures publiques ont confirmé la genèse, le runtime 1014039, les propriétés FLOP, huit modèles et l’inscription gateway indisponible (404). Le faucet annonçait un budget nul à 12:43 UTC. Les commandes de validation, les observations et la recette utilisateur figurent dans VALIDATION.md.

Les 44 tests Python, les 18 tests Node et deux parcours Chromium avec wallet simulé passent. Les lanceurs Windows ont été relus sous Linux. La prochaine étape est la contre-vérification locale du diff puis une recette Talisman et Windows avec l’accord de l’utilisateur. La branche reste locale pour revue.
