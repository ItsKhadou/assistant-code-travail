import json
import sys

from src.base_vectorielle import BaseVectorielle
from src.config import CHEMIN_CORPUS, CHEMIN_CORPUS_DEMO

if __name__ == "__main__":
    chemin = CHEMIN_CORPUS_DEMO if "--demo" in sys.argv else CHEMIN_CORPUS
    if not chemin.exists():
        sys.exit(f"Corpus introuvable : {chemin}\n"
                 "Lancer d'abord python -m src.corpus (ou --demo).")
    if chemin == CHEMIN_CORPUS_DEMO:
        print("⚠️  MODE DEMO : 10 articles paraphrases non officiels, "
              "uniquement pour tester le pipeline.")
    documents = json.loads(chemin.read_text(encoding="utf-8"))
    BaseVectorielle().construire(documents, force="--force" in sys.argv)
