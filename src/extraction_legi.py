import sys
import tarfile
from pathlib import Path

from src.config import DOSSIER_RAW

# Identifiant LEGI du Code du travail -- verifiable dans l'URL de
# n'importe quelle page du Code du travail sur legifrance.gouv.fr.
ID_CODE_TRAVAIL = "LEGITEXT000006072050"


def parcourir(chemin_archive: str, extraire: bool = False,
              nb_apercus: int = 10) -> None:
    """Parcourt l'archive en flux ("r|gz") et filtre les articles du Code.

    Le mode flux lit sequentiellement sans construire d'index : c'est la
    seule approche raisonnable sur une archive de cette taille.
    """
    n_entrees, n_articles, apercus = 0, 0, []
    with tarfile.open(chemin_archive, mode="r|gz") as tar:
        for membre in tar:
            n_entrees += 1
            if n_entrees % 200_000 == 0:
                print(f"  ... {n_entrees:,} entrees, {n_articles} articles trouves")
            if ID_CODE_TRAVAIL not in membre.name:
                continue
            if not (membre.isfile() and membre.name.endswith(".xml")
                    and "/article/" in membre.name):
                continue
            n_articles += 1
            if len(apercus) < nb_apercus:
                apercus.append(membre.name)
            if extraire:
                # filter="data" : protection contre les chemins pieges
                # (Python >= 3.12 ; retirer l'argument sinon).
                tar.extract(membre, path=DOSSIER_RAW, filter="data")

    print(f"\n{n_entrees:,} entrees parcourues, "
          f"{n_articles} fichiers d'articles du Code du travail.")
    print("Exemples de chemins :")
    for chemin in apercus:
        print(f"  {chemin}")
    if extraire:
        print(f"\nExtraction terminee dans {DOSSIER_RAW}/")


if __name__ == "__main__":
    if len(sys.argv) < 2 or not Path(sys.argv[1]).exists():
        sys.exit(__doc__)
    parcourir(sys.argv[1], extraire="--extraire" in sys.argv)
