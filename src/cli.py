import os

from src.base_vectorielle import BaseVectorielle
from src.juriste import Juriste

os.system("")  # active les couleurs ANSI sous Windows
VERT, JAUNE, GRIS, RESET = "\033[32m", "\033[33m", "\033[90m", "\033[0m"


def barre(similarite: float, largeur: int = 10) -> str:
    """Petite jauge visuelle de similarite : ██████░░░░"""
    pleins = round(similarite * largeur)
    return "█" * pleins + "░" * (largeur - pleins)


def bandeau(base: BaseVectorielle) -> None:
    collection = base.charger()
    meta = collection.metadata or {}
    print(f"""{VERT}
  ╔═══════════════════════════════════════════════════════╗
  ║   ASSISTANT CODE DU TRAVAIL — RAG (M2 MD5)            ║
  ╚═══════════════════════════════════════════════════════╝{RESET}
  Base : {collection.count()} chunks | indexee le {meta.get('date_indexation', '?')}
  Modele d'embedding : {meta.get('embedding_model', '?')}
  {JAUNE}Le droit evolue : corpus fige a la date d'indexation.
  Verifiez toute information sur legifrance.gouv.fr.{RESET}
  Tapez votre question ({GRIS}:aide{RESET} pour les commandes).""")


def boucle() -> None:
    base = BaseVectorielle()
    bandeau(base)
    juriste = Juriste(base)
    while True:
        try:
            question = input(f"\n{VERT}Question >{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAu revoir !")
            break
        if not question:
            continue
        if question.lower() in {":quitter", "quit", "exit", "q"}:
            print("Au revoir !")
            break
        if question.lower() == ":aide":
            print("  Posez une question sur le droit du travail, ou "
                  "':quitter' pour sortir.\n  Astuce : 'que dit L3121-1 ?' "
                  "utilise la recherche exacte par numero.")
            continue

        resultat = juriste.repondre(question)
        print("\n" + resultat.texte)
        print(f"\n{GRIS}Sources consultees :{RESET}")
        for s in resultat.sources:
            jauge = barre(s.similarite)
            print(f"  {jauge} {s.similarite:.2f}  {s.numero} ({s.section})")


if __name__ == "__main__":
    boucle()
