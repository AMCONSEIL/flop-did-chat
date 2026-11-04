# FLOP DID Chat

**Version locale de test 0.1.0 · Français / English · Talisman · Ed25519**

Un chat pour le gateway FLOP devnet : connexion signée dans Talisman, catalogue réel de modèles, conversations et suivi des reçus.

> **Version publique de test.** La connexion Talisman a été testée avec un DID personnel existant. Notre requête de chat a atteint FLOP mais a reçu HTTP 429, `BrokerOverloadedError: gateway channel pool is full` ; le reçu indique une réservation libérée. Aucune réponse réelle du modèle n’a encore été validée. Les 34 tests automatiques hors ligne passent. Voir les [détails de validation](VALIDATION.md) et l’[incident du gateway](https://github.com/flop-labs/network/issues/31).
>
> Les retours de la communauté sont bienvenus. Un test utilisateur réel reste nécessaire avant de s’appuyer sur ce client expérimental.

DID auteur : **did:key:z6Mkt3DNtpGBNh1KHYwLQEk6QtCcJ7vVaRPze1SU7MyhFMVD**

[English](README.md) · [Identité](IDENTITY.md) · [Sécurité et limites](SECURITY.md)

## Avant de commencer : votre DID dans Talisman

**Il faut un compte Talisman utilisant la même clé Ed25519 que votre identité `did:key` existante.** Installer Talisman ou créer un nouveau wallet ne le relie pas automatiquement à un DID existant.

Pour préparer ce compte, suivez notre précédent projet : **[did-to-talisman — importer votre DID existant dans Talisman](https://github.com/AMCONSEIL/did-to-talisman)**. Il contient le tutoriel français/anglais et l’outil local de conversion d’une sauvegarde PEM chiffrée compatible. Si ce compte est déjà importé, utilisez-le directement.

Chaque utilisateur connecte **son propre DID et son propre wallet**. Le DID auteur affiché dans ce dépôt attribue la contribution ; ce n’est pas le compte que les autres utilisateurs doivent connecter.

## Démarrer

1. Installer Python 3.11 ou plus et l’extension Talisman depuis son site officiel.
2. Lancer **INSTALLER_WINDOWS.cmd**, puis **LANCER.cmd**.
3. Ouvrir **http://127.0.0.1:50510/** dans le navigateur avec Talisman.
4. Cliquer **Connecter Talisman**, autoriser son compte **Ed25519 existant**, puis lire le challenge officiel.
5. Vérifier le compte et signer dans Talisman. Aucun transfert n’est demandé par cette connexion.
6. Rédiger un message et cliquer Envoyer. Aucun prompt ne part à la connexion.

Pour préparer un DID existant dans Talisman : [did-to-talisman](https://github.com/AMCONSEIL/did-to-talisman).
Le DID public seul ne récupère pas une clé perdue. Ne jamais fournir PEM, JSON de wallet, seed ou mot de passe à ce chat.

Linux/macOS : Python 3.11+, créer un environnement virtuel, installer les distributions épinglées du fichier de requirements puis lancer **python flop_chat.py**. L’extension Talisman doit être dans le navigateur. Ces plateformes ne sont pas recettées.

## Modèles et limites

Le catalogue est chargé depuis le gateway public. Le modèle doit aussi être autorisé par l’accès reçu : les autres sont désactivés, pas débloqués artificiellement. Au contrôle initial du 3 novembre 2026, un seul modèle était annoncé : Qwen2.5-0.5B.

Par défaut : **48 tokens de sortie, plafond de 0,9 FLOP par envoi et budget local de 0,9 FLOP pour cette exécution du serveur**. Dans Réglages, l’utilisateur choisit ses plafonds par message et pour le chat, sans maximum arbitraire fixé par cette application. Les montants doivent être positifs et finis ; le plafond par message doit tenir dans le plafond total. Le serveur applique les plafonds choisis. La réponse peut aller jusqu’à 1 024 tokens dans les limites annoncées du modèle. Ces réglages ne créent aucun crédit serveur.

L’historique de la conversation réussi fait partie du contexte envoyé et peut augmenter le coût. Maximum local : 40 messages et 30 000 caractères de contexte. Pas d’outils autonomes, téléversements ou appels automatiques.

## Comprendre les compteurs

- **Quota API** : valeur fournie par FLOP, affichée sans la convertir en solde de wallet. Ce n’est pas le solde natif du faucet.
- **Réservé** : réservation courante indiquée par les reçus non terminaux.
- **Réglé** : montants des reçus dont l’état est settled. Le montant exact en unités de base est conservé quand disponible ; un montant historique flottant reste une observation du gateway.
- **Tokens** : compteurs renvoyés dans les réponses obtenues par cette application.
- **Utilisé ou en attente / limite** : règlements connus et plafonds conservateurs des appels encore incertains, pour l’exécution courante du serveur.

Une valeur absente reste **inconnue**. Un reçu released signifie que la réservation est libérée ; settled_spend:null n’est pas converti en zéro. Les compteurs de cette application ne prétendent pas couvrir tout l’historique du compte.

Un reçu du gateway n’est **pas une vérification indépendante de finalité sur chaîne**. Un canal ou événement peut couvrir plusieurs requêtes : il n’est pas présenté comme une transaction de paiement individuelle.

## Erreurs, reprise et identité

Le request_id et son empreinte sont sauvegardés **avant** l’envoi. Un second clic avec le même identifiant ne soumet jamais une nouvelle inférence. Un timeout, reçu absent ou résultat réservé bloque l’envoi suivant jusqu’à réconciliation.

**Actualiser / Vérifier les reçus** ne soumet que des lectures. Aucun retry d’inférence automatique. Un 429/503 impose un délai local d’au moins 60 secondes, ou 10 minutes si le serveur n’indique aucun délai. Ne pas créer un autre wallet ni réclamer un nouveau faucet pour contourner une limite.

Une reconnexion du même compte change éventuellement le bearer, **jamais l’allocation ni son expiration**. Après expiration, seule une procédure officiellement autorisée pour le même compte peut restaurer l’accès.

Les clés privées restent dans Talisman. Le bearer reste en mémoire du serveur local. Changer de compte est refusé tant qu’un appel est incertain. Le serveur vérifie la signature Ed25519, le DID, le challenge, l’adresse et le genesis du devnet.

Lancement avec verrou d’identité personnel, si souhaité : **python flop_chat.py --expected-did VOTRE_DID_PUBLIC**.
Pour reprendre un reçu existant : **--reconcile-request IDENTIFIANT_PUBLIC**. Un reçu introuvable bloque la reprise.

## Données locales et arrêt

Le navigateur conserve les conversations en mémoire par défaut. **Conserver l’historique ici** active un stockage en clair des prompts/réponses dans ce navigateur : option à réserver à son ordinateur privé. Aucun bearer/signature de connexion n’y est enregistré. Effacer les conversations ne supprime pas les reçus ni le travail distant.

Le dossier **.local/** contient un journal minimal de requêtes : identité publique, IDs, empreintes non réversibles du contenu, plafonds, compteurs et reçus. Aucun prompt, réponse, mot de passe, signature de connexion ou bearer n’y est écrit. Ne pas le supprimer pour débloquer un appel incertain. Les empreintes de contenu ne sont pas une anonymisation garantie pour des prompts prévisibles.

Fermer le serveur efface son bearer en mémoire ; le budget local est propre à cette exécution. Les requêtes et reçus persistés servent à réconcilier après redémarrage. Une seconde instance sur le même dossier est refusée. Le service reste lié à 127.0.0.1 ; ne pas l’exposer sur Internet.

## Validation

Tests hors ligne : **python -m unittest discover -s tests -v** et **node --test tests/core.test.mjs**.
Les fixtures cryptographiques sont publiques (RFC8032), jamais une clé utilisateur. Aucun fonds n’est engagé par ces tests.

**La connexion Talisman réelle est validée ; une réponse réelle réussie et une conversation à plusieurs tours restent à valider avant une version stable.** Les erreurs serveur ne sont pas masquées par un mode de démonstration. Cette version n’a pas encore de signature d’attribution propre : le DID d’auteur est une référence publique, pas une preuve de version signée.

Devnet : aucune valeur monétaire, récompense ou poids d’airdrop. Application communautaire indépendante ; aucune affiliation officielle revendiquée.

Le compteur de limite locale et les plafonds se trouvent dans **Réglages**, sous la zone de saisie. Le plafond initial de 0,9 FLOP est un choix de précaution de cette application pour le premier test, pas une exigence de FLOP.
