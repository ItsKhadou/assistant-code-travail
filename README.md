# Assistant Code du travail — RAG

Assistant en ligne de commande qui répond en langage naturel aux questions
sur le droit du travail français **en citant systématiquement ses articles
sources**. Projet final M2 MD5 —
chaque brique du RAG est implémentée à la main (LangChain/LlamaIndex : non
utilisés, conformément à l'énoncé).

> ⚠️ Cet assistant ne fournit pas de conseil juridique. Consultez un avocat ou
> l'inspection du travail pour votre situation personnelle.

## Ce qui distingue ce projet

- **Recherche hybride** (jalon 6) : les numéros d'articles présents dans la
  question (« que dit L3121-1 ? ») sont détectés par expression régulière et
  récupérés par accès *exact* aux métadonnées, puis complétés par la
  recherche sémantique — là où le vectoriel seul échoue sur les identifiants.
- **Score de confiance** (jalon 6) : chaque source est affichée avec sa
  similarité (jauge ██████░░░░) ; sous un seuil calibré sur notre jeu de
  test, la réponse est précédée d'une mise en garde.
- **Garanties dans le code, pas dans le prompt** : avertissement juridique
  concaténé en Python à chaque réponse, et vérification par regex que toute
  référence citée figure bien dans le contexte fourni.
- **Déduplication par article** (retrieval) : sur-interrogation `k×3` puis
  un seul chunk conservé par numéro d'article — un article sous-découpé en
  plusieurs chunks ne consomme plus plusieurs places du top-k. Correctif
  issu de nos tests sur corpus réel.

## Installation

```bash
git clone https://github.com/ItsKhadou/assistant-code-travail.git
cd assistant-code-travail
python -m venv .venv
# Windows : .venv\Scripts\Activate.ps1  |  Linux/Mac : source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env    # puis renseigner GROQ_API_KEY
```

> **Windows** : la console utilise par defaut l'encodage cp1252, ce qui
> provoque une `UnicodeEncodeError` sur les caracteres ⚠️ affiches par le
> projet. Definir `PYTHONUTF8=1` avant de lancer les scripts (ou de facon
> permanente avec la commande PowerShell suivante, puis rouvrir le
> terminal) :
> ```powershell
> [Environment]::SetEnvironmentVariable("PYTHONUTF8", "1", "User")
> ```

## Utilisation

```bash
# (option) essai immédiat sur le mini-corpus de démonstration :
python -m src.indexation --demo

# 1) Corpus réel — archive LEGI (data.gouv.fr / DILA) placée dans data/ :
python -m src.extraction_legi data/Freemium_legi_global_XXXXXXXX.tar.gz --extraire
# 2) Construction du corpus nettoyé :
python -m src.corpus
# 3) Indexation (UNE fois ; --force pour reconstruire) :
python -m src.indexation --force
# 4) Validation du retrieval AVANT le LLM + calibration du seuil :
python -m tests.evaluation_retrieval
# 5) L'assistant :
python -m src.cli
```

Au lancement, la base persistée dans `base_vectorielle/` est **rechargée
sans réindexation** ; la date d'indexation et le modèle d'embedding stockés
avec elle sont affichés dans le bandeau.

## Architecture

| Module | Jalon | Rôle |
|---|---|---|
| `src/extraction_legi.py` | 1 | extraction sélective du dump LEGI (flux, jamais décompressé en entier) |
| `src/corpus.py` | 1 | XML → `Article` (dataclass) nettoyés + métadonnées |
| `src/base_vectorielle.py` | 2-3-6 | classe `BaseVectorielle` : chunking, persistance, retrieval, accès par numéro |
| `src/indexation.py` | 2 | script de construction de la base |
| `src/juriste.py` | 4+6 | classe `Juriste` : hybride, prompt strict, Groq, garanties codées |
| `src/cli.py` | 5 | interface interactive (couleurs, jauges de similarité) |
| `tests/evaluation_retrieval.py` | 3 | jeu d'évaluation + calibration du seuil |

## Questions de réflexion

### Q1 — Granularité du chunking
Nous avons comparé les deux approches. Indexer par article : chaque chunk
correspond à un numéro citable, le vecteur porte un seul sujet, et aucune
phrase n'est coupée. Par contre on perd le contexte de la section, et les
renvois entre articles ne sont pas résolus. Regrouper par section : plus de
contexte et les renvois internes sont résolus, mais le vecteur devient une
moyenne de plusieurs sujets, la recherche est moins précise, et on ne sait
plus quel article citer exactement. Nous avons retenu une approche hybride
légère : l'article reste l'unité d'indexation, mais le texte embeddé
commence par un en-tête (numéro — thème — titre) suivi du texte. L'en-tête
est placé en premier à cause de la troncature : si le modèle d'embedding
coupe un texte trop long, on perd la fin de l'article mais jamais son
identité. Les rares articles trop longs sont sous-découpés aux frontières
de phrases. Nos tests sur corpus réel ont montré une limite de cette
approche : l'en-tête aide à distinguer les thèmes entre eux, mais à
l'intérieur d'un même thème, des dizaines d'articles partagent le même
en-tête et se ressemblent trop.

### Q2 — Traçabilité
Le numéro d'article est stocké aux deux endroits, avec deux rôles
différents. Dans le texte embeddé, il participe à la recherche. Dans les
métadonnées, il est récupérable par le code sans parsing : c'est lui qui
sert à construire le contexte numéroté envoyé au LLM, à afficher les
sources, et à faire la recherche exacte par numéro. Pour que le LLM cite
correctement, chaque extrait du contexte porte son numéro : le modèle n'a
qu'à recopier, pas à se souvenir. La température est basse (0.1) et le
prompt interdit de citer un numéro absent des extraits. Mais un prompt
n'est suivi que statistiquement, donc la garantie finale est dans le code :
la fonction `_verifier_citations` extrait par regex tous les numéros cités
dans la réponse du LLM et les compare aux numéros réellement fournis dans
le contexte. Toute référence citée mais absente déclenche un avertissement
demandant de vérifier sur Légifrance. Le prompt interdit d'inventer, le
code vérifie que l'interdiction a été respectée.

### Q3 — Fraîcheur
Notre corpus provient de l'archive `Freemium_legi_global_20250713` : il
reflète l'état du droit au 13 juillet 2025, quelle que soit la date où nous
l'avons indexé. La date d'indexation est stockée dans les métadonnées de la
collection ChromaDB au moment de la construction de la base, et elle est
affichée dans le bandeau à chaque démarrage de l'assistant, avec un rappel
que le droit évolue et qu'il faut vérifier sur legifrance.gouv.fr. La mise
à jour est une opération volontaire, pas un effet de bord du lancement :
télécharger la nouvelle archive, relancer l'extraction et la construction
du corpus, puis réindexer explicitement avec `--force`. Le filtre
`ETAT == VIGUEUR` fait le ménage automatiquement : les articles abrogés
entre-temps disparaissent, les nouveaux entrent. Nous avons préféré cette
reconstruction complète aux mises à jour incrémentales quotidiennes que la
DILA propose aussi : plus simple et plus facile à vérifier, pour un corpus
de notre taille.

### Q4 — Réponses conditionnelles
Beaucoup de réponses dépendent de la taille de l'entreprise, de la
convention collective ou de l'ancienneté. Nous avons choisi la réponse
générale assortie de réserves plutôt que la question de clarification : la
règle 5 de notre prompt système demande au LLM de donner la règle générale
du Code ET de signaler explicitement que la réponse peut varier selon la
situation. Ce choix est adapté à notre interface en ligne de commande sans
historique de conversation : poser une question de clarification supposerait
de mémoriser les échanges précédents, ce qui correspond à l'amélioration
« historique de conversation » que nous n'avons pas implémentée. Si nous
l'ajoutions, la clarification deviendrait le meilleur choix pour les
questions les plus dépendantes du contexte.

### Q5 — La frontière du conseil juridique
Une question factuelle a sa réponse directement dans le texte du Code
(« combien de jours de congés par an ? ») ; une question d'interprétation
demande d'appliquer le droit à une situation personnelle (« mon
licenciement est-il abusif ? »), ce qui est le travail d'un avocat, pas
d'un système documentaire. La règle 6 de notre prompt demande au LLM de ne
pas trancher les cas personnels : il explique la règle générale et oriente
vers un avocat ou l'inspection du travail. En complément, deux garanties ne
dépendent pas du LLM. L'avertissement juridique est concaténé en Python à
chaque réponse : contrairement à une consigne de prompt, le code ne
l'oublie jamais, ce qui répond à l'exigence « pas même une fois sur dix »
de l'énoncé. Et si aucun extrait pertinent n'existe, le LLM doit répondre
« Je ne trouve pas cette information dans ma base » plutôt qu'inventer —
comportement que nous avons vérifié avec des questions hors corpus.

## Choix techniques
Embedding `paraphrase-multilingual-MiniLM-L12-v2` (multilingue, 384 dims),
vecteurs normalisés, nom du modèle vérifié au rechargement. ChromaDB
`PersistentClient`, distance cosinus. Groq à température 0.1, top-8.
Corpus : option B (dump XML LEGI), filtre `ETAT == VIGUEUR`, 8 thèmes
(voir `corpus.PREFIXES_THEMES`).

Chiffres mesurés sur notre corpus réel : 375 articles en vigueur, 393
chunks, 8 thèmes, `TOP_K=8`. `SEUIL_CONFIANCE=0.60`, calibré sur notre jeu
de test (questions hors corpus ≤ 0.58, bonnes réponses ≥ 0.78).

## Limites connues et pistes
Renvois croisés signalés (règle 4) mais non résolus — piste : résolution en
un saut via `BaseVectorielle.par_numeros` sur les numéros détectés dans les
extraits récupérés. Questions comparatives : la décomposition en
sous-questions serait la suite naturelle. La recherche vectorielle sépare
bien les thèmes entre eux mais distingue mal les sous-régimes d'un même
thème partageant le même vocabulaire : sur « comment fonctionne la rupture
conventionnelle ? », `L1237-11` (rupture conventionnelle individuelle) se
classe au rang 14 face à des articles sur la rupture conventionnelle
*collective*, alors qu'il ressort en rang 1 sur une question plus ciblée
(« la rupture conventionnelle peut-elle être imposée par l'employeur ? »).
Pistes : reranking cross-encoder, ou reformulation de la question.

## Usage de l'IA
Projet développé avec assistance IA (autorisée par l'enseignant).
L'ensemble du code a été exécuté, testé et relu par les trois membres du
trinôme, qui en ont validé la compréhension module par module.
