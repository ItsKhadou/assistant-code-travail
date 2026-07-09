import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv
from groq import Groq

from src.base_vectorielle import BaseVectorielle, Extrait
from src.config import (AVERTISSEMENT, MAX_TOKENS, MODELE_LLM,
                              PHRASE_ECHEC, SEUIL_CONFIANCE, TEMPERATURE,
                              TOP_K)

load_dotenv()  # GROQ_API_KEY depuis .env -- jamais en dur, jamais commite

REGEX_ARTICLE = re.compile(r"\b[LRD]\s?\.?\s?(\d{4}-\d+(?:-\d+)?)\b", re.I)

PROMPT_SYSTEME = """Tu es un assistant documentaire specialise dans le Code du travail francais.

REGLES STRICTES :
1. Reponds UNIQUEMENT a partir des extraits numerotes ci-dessous. Toute
   connaissance exterieure est interdite, meme si tu crois la connaitre.
2. Rattache chaque affirmation a son numero d'article entre crochets,
   exemple [L3141-3]. Ne cite JAMAIS un numero absent des extraits.
3. Si les extraits ne permettent pas de repondre : reponds exactement
   "{phrase_echec}"
4. Si un extrait renvoie a un article absent des extraits ("au sens de
   l'article X"), dis-le explicitement au lieu d'en supposer le contenu.
5. Si la reponse depend de la situation (taille d'entreprise, convention
   collective, anciennete) : donne la regle generale du Code ET signale
   explicitement cette reserve.
6. Si la question demande un avis sur un cas personnel ("mon licenciement
   est-il abusif ?") : ne tranche pas, explique la regle generale et
   oriente vers un avocat ou l'inspection du travail.
7. Certains extraits peuvent etre hors sujet : ignore-les.

EXTRAITS :
{contexte}"""


@dataclass
class Reponse:
    texte: str            # avertissement inclus (garanti par le code)
    sources: list[Extrait]
    confiance: float      # similarite du meilleur extrait semantique


class Juriste:
    def __init__(self, base: BaseVectorielle | None = None):
        self.base = base or BaseVectorielle()
        self._llm = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # ---------------- recherche hybride (jalon 6) ----------------------
    def _extraits_hybrides(self, question: str, k: int) -> list[Extrait]:
        """Acces exact pour les numeros cites, semantique pour le reste."""
        numeros = [f"{m.group(0)[0].upper()}{m.group(1)}"
                   for m in REGEX_ARTICLE.finditer(question)]
        exacts = self.base.par_numeros(sorted(set(numeros)))
        semantiques = self.base.rechercher(question, k)
        deja = {e.numero for e in exacts}
        return exacts + [e for e in semantiques if e.numero not in deja][:k]

    # ---------------- garde-fous codes en dur ---------------------------
    @staticmethod
    def _verifier_citations(texte: str, extraits: list[Extrait]) -> str:
        """Signale toute reference citee hors du contexte fourni."""
        autorises = {e.numero for e in extraits}
        inventes = set(re.findall(r"[LRD]\d{4}-\d+(?:-\d+)?", texte)) - autorises
        if inventes:
            texte += ("\n\n⚠️  References citees hors des sources "
                      f"consultees : {', '.join(sorted(inventes))} -- "
                      "a verifier sur legifrance.gouv.fr.")
        return texte

    # ---------------- pipeline d'une question ---------------------------
    def repondre(self, question: str, k: int = TOP_K) -> Reponse:
        extraits = self._extraits_hybrides(question, k)
        confiance = max((e.similarite for e in extraits
                         if e.similarite < 1.0), default=0.0)

        contexte = "\n\n".join(
            f"[{i}] Article {e.numero} ({e.section}) :\n{e.texte}"
            for i, e in enumerate(extraits, 1))
        completion = self._llm.chat.completions.create(
            model=MODELE_LLM, temperature=TEMPERATURE, max_tokens=MAX_TOKENS,
            messages=[
                {"role": "system",
                 "content": PROMPT_SYSTEME.format(phrase_echec=PHRASE_ECHEC,
                                                  contexte=contexte)},
                {"role": "user", "content": question},
            ])
        texte = completion.choices[0].message.content.strip()
        texte = self._verifier_citations(texte, extraits)

        # Jalon 6 : mise en garde si le retrieval lui-meme est peu sur.
        # Pas de mise en garde si un extrait vient de la correspondance
        # exacte par numero (similarite == 1.0) : la confiance elle-meme
        # ignore ces extraits (ligne 92-93), mais l'avertissement ne doit
        # pas contredire un resultat exact.
        exact_present = any(e.similarite == 1.0 for e in extraits)
        if confiance < SEUIL_CONFIANCE and PHRASE_ECHEC not in texte and not exact_present:
            texte = ("⚠️  Fiabilite faible : aucun extrait ne correspond "
                     f"fortement a la question (meilleure similarite : "
                     f"{confiance:.2f}). Reponse a prendre avec prudence.\n\n"
                     + texte)

        # LA garantie non negociable, concatenee en Python : 100 % fiable.
        texte = f"{texte}\n\n{AVERTISSEMENT}"
        return Reponse(texte=texte, sources=extraits, confiance=confiance)
