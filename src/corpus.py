import json
import random
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass

from src.config import CHEMIN_CORPUS, DOSSIER_RAW

# Themes retenus (>= 5 exiges). Le rattachement se fait par prefixe du
# numero d'article -- simple, deterministe, et facile a etendre.
PREFIXES_THEMES = {
    "L3121": "Duree du travail et heures supplementaires",
    "L3141": "Conges payes",
    "L1221": "Contrat de travail",
    "L1242": "Contrat de travail",              # CDD
    "L1231": "Licenciement", "L1232": "Licenciement",
    "L1233": "Licenciement", "L1234": "Licenciement",
    "L1237": "Rupture conventionnelle et autres ruptures",
    "L3231": "Salaire minimum (SMIC)",
    "L1152": "Harcelement et discrimination",
    "L1153": "Harcelement et discrimination",
    "L2311": "Representation du personnel",     # CSE
}

_BALISES_HTML = re.compile(r"<[^>]+>")
_ESPACES = re.compile(r"\s+")


@dataclass
class Article:
    """Un article du Code du travail, nettoye et localise dans un theme."""
    id: str
    numero: str
    titre: str
    texte: str
    section: str
    source: str = "Base LEGI (data.gouv.fr / DILA)"


def nettoyer(brut: str) -> str:
    """Supprime les scories HTML du contenu LEGI, normalise les espaces."""
    return _ESPACES.sub(" ", _BALISES_HTML.sub(" ", brut)).strip()


def lire_article(chemin_xml) -> Article | None:
    """Parse un fichier XML d'article. None si hors perimetre.

    Filtres : version non en vigueur (le dump consolide contient les
    versions abrogees/modifiees -- sans ce filtre on citerait du droit
    mort), numero absent, theme non retenu, texte vide.
    """
    try:
        racine = ET.parse(chemin_xml).getroot()
    except ET.ParseError:
        return None
    if racine.findtext(".//ETAT", default="") != "VIGUEUR":
        return None
    numero = racine.findtext(".//META_ARTICLE/NUM", default="").strip()
    section = PREFIXES_THEMES.get(numero.split("-")[0]) if numero else None
    if not section:
        return None
    contenu = racine.find(".//BLOC_TEXTUEL/CONTENU")
    if contenu is None:
        return None
    texte = nettoyer(" ".join(contenu.itertext()))
    if not texte:
        return None
    # Hierarchie (partie > livre > titre > chapitre) : le dernier intitule
    # sert de titre fin a l'article.
    intitules = [t.text.strip() for t in racine.findall(".//CONTEXTE//TITRE_TM")
                 if t.text and t.text.strip()]
    return Article(id=numero, numero=numero,
                   titre=intitules[-1] if intitules else "",
                   texte=texte, section=section)


def construire() -> list[Article]:
    """Parcourt data/raw/ ; deduplique par numero (versions multiples)."""
    if not DOSSIER_RAW.exists():
        sys.exit(f"{DOSSIER_RAW} introuvable -- lancer d'abord "
                 "python -m src.extraction_legi ... --extraire")
    articles, vus = [], set()
    for chemin in sorted(DOSSIER_RAW.rglob("*.xml")):
        article = lire_article(chemin)
        if article and article.numero not in vus:
            vus.add(article.numero)
            articles.append(article)
    return articles


def controle_qualite(articles: list[Article], n: int = 10) -> None:
    """Consigne de l'enonce : afficher n documents au hasard et les RELIRE."""
    print(f"\n=== Controle qualite : {n} articles au hasard ===")
    for a in random.sample(articles, min(n, len(articles))):
        print(f"\n[{a.numero}] ({a.section}) {a.titre}")
        print(f"  {a.texte[:300]}{'...' if len(a.texte) > 300 else ''}")


if __name__ == "__main__":
    articles = construire()
    if not articles:
        sys.exit("0 article extrait : verifier les balises XML (voir docstring).")
    themes = {a.section for a in articles}
    print(f"{len(articles)} articles en vigueur, {len(themes)} themes :")
    for t in sorted(themes):
        print(f"  - {t}")
    CHEMIN_CORPUS.write_text(
        json.dumps([asdict(a) for a in articles], ensure_ascii=False, indent=2),
        encoding="utf-8")
    print(f"\nCorpus ecrit : {CHEMIN_CORPUS}")
    controle_qualite(articles)
