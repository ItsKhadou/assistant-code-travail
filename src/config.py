from pathlib import Path

# --- Chemins -----------------------------------------------------------
RACINE = Path(__file__).resolve().parent.parent
DOSSIER_DONNEES = RACINE / "data"
CHEMIN_CORPUS = DOSSIER_DONNEES / "documents.json"
CHEMIN_CORPUS_DEMO = DOSSIER_DONNEES / "corpus_demo.json"
DOSSIER_RAW = DOSSIER_DONNEES / "raw"
CHEMIN_BASE = str(RACINE / "base_vectorielle")

# --- Modeles -----------------------------------------------------------
MODELE_EMBEDDING = "paraphrase-multilingual-MiniLM-L12-v2"
MODELE_LLM = "llama-3.3-70b-versatile"  # verifier le catalogue Groq du jour

# --- Parametres RAG ----------------------------------------------------
NOM_COLLECTION = "code_travail"
TOP_K = 5
TEMPERATURE = 0.1
MAX_TOKENS = 1024
TAILLE_MAX_CHUNK = 1500  # caracteres avant sous-decoupage

# Seuil de confiance (similarite cosinus 0..1) : en dessous du seuil pour
# le MEILLEUR extrait, la reponse est accompagnee d'une mise en garde.
# Calibre sur le corpus reel (375 articles, tests.evaluation_retrieval) :
# bonnes reponses (top-1 correct) entre 0.78 et 0.82, questions hors
# corpus entre 0.25 et 0.58. Seuil place au-dessus du plafond hors corpus,
# avec marge sous le plancher des bonnes reponses.
SEUIL_CONFIANCE = 0.35

# --- Garanties codees en dur (jamais confiees au LLM) -------------------
AVERTISSEMENT = (
    "⚠️  Cet assistant ne fournit pas de conseil juridique. Consultez un "
    "avocat ou l'inspection du travail pour votre situation personnelle."
)
PHRASE_ECHEC = "Je ne trouve pas cette information dans ma base."


