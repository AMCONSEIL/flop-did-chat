# FLOP DID Chat · état de reprise

La branche locale feat/testnet-v0.3.0 prépare la migration de la v0.2.2 vers le Testnet. Le point de retour du code est 1eacbb7. Conserver les journaux locaux pour réconcilier tout envoi en attente avant un changement de version.

Le serveur Python, l’interface EN/FR et le worker SDK 0.13.1 prennent en charge la connexion Talisman sr25519/Ed25519, le faucet à validation manuelle, le gateway et le direct sur un mineur explicitement configuré. Les données locales Testnet sont isolées du précédent registre. Les réglages directs par défaut sont 1200 secondes, 0,05 FLOP et 256 tokens. Les procédures et limites figurent dans les deux README et SECURITY.md.

Le 27 novembre 2026, les lectures publiques ont confirmé la genèse, le runtime 1014039, les propriétés FLOP, huit modèles et l’inscription gateway indisponible (404). Le faucet annonçait un budget nul à 12:43 UTC. Les commandes de validation, les observations et la recette utilisateur figurent dans VALIDATION.md.

Le contrôle initial a validé 44 tests Python, 18 tests Node et deux parcours Chromium avec wallet simulé. Les lanceurs Windows ont été relus sous Linux avant la recette ci-dessous.

## Recette Windows du 27 novembre 2026

Le clone de recette utilise `feat/testnet-v0.3.0` au commit `9e66472`. Le lancement sur le port 50511, la connexion Talisman avec un DID Technocore Ed25519, la lecture du solde Testnet et l’affichage du devis direct Yukon ont été vérifiés. Les mineurs Yukon et Floperati sont configurés localement. L’inscription gateway renvoie HTTP 404.

La tentative Yukon est en attente de réconciliation, sans hash d’ouverture ni réponse. Le contrôle a trouvé la finalité au bloc 248399 alors que la tête atteignait 248849. Le canal était absent de la tête et de l’état finalisé, avec un nonce de compte identique au bloc de départ et à la tête. Conserver le journal. La recette `forceOpen` attend la résolution de [FLOP #1775](https://github.com/flop-labs/network/issues/1775). Reprendre par « Vérifier les reçus » quand la finalité progresse, avant tout nouvel envoi. La cause de l’absence d’ouverture pour Yukon reste à établir.

Le formulaire français et anglais donne un libellé explicite pour les DID Technocore importés et mémorise le type de signature vérifié par adresse dans le navigateur. Le helper du test sr25519 transmet le défi à Node en octets UTF-8 pour éviter la conversion Windows. Sur Windows, les 44 tests Python et les 18 tests Node passent. Edge avec un compte simulé a confirmé l’aide en cas de mauvais type, la connexion Ed25519, la mémorisation après rechargement et le libellé français. Le bilan figure dans [VALIDATION.md](VALIDATION.md). Les changements sont préparés sur `feat/testnet-v0.3.0` pour revue avant fusion.
