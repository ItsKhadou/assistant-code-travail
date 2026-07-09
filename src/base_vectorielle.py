import sys
from dataclasses import dataclass
from datetime import date

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import (CHEMIN_BASE, MODELE_EMBEDDING, NOM_COLLECTION,
                              TAILLE_MAX_CHUNK, TOP_K)


@dataclass
class Extrait:
    """Un chunk retrouve, pret a etre cite."""
    numero: str
    titre: str
    section: str
    texte: str
    similarite: float  # cosinus dans [0..1] : 1 = identique


class BaseVectorielle:
    def __init__(self):
        self._client = chromadb.PersistentClient(path=CHEMIN_BASE)
        self._modele = None  # charge paresseusement (5 s au premier appel)
        self._collection = None

    # ------------------------------------------------------------------
    #  Outils internes
    # ------------------------------------------------------------------
    @property
    def modele(self) -> SentenceTransformer:
        if self._modele is None:
            self._modele = SentenceTransformer(MODELE_EMBEDDING)
        return self._modele

    @staticmethod
    def _texte_a_embedder(doc: dict, morceau: str) -> str:
        """En-tete identitaire (numero — section — titre) PUIS texte.

        L'en-tete en premier : en cas de troncature par le modele
        d'embedding, on perd la fin du texte, jamais l'identite du chunk.
        C'est notre chunking "hybride leger" (cf. Q1 du README).
        """
        en_tete = f"Article {doc['numero']} — {doc['section']}"
        if doc.get("titre"):
            en_tete += f" — {doc['titre']}"
        return f"{en_tete}\n{morceau}"

    @staticmethod
    def _decouper(texte: str) -> list[str]:
        """1 article = 1 chunk ; sous-decoupage aux frontieres de phrases
        pour les rares articles depassant TAILLE_MAX_CHUNK."""
        if len(texte) <= TAILLE_MAX_CHUNK:
            return [texte]
        morceaux, courant = [], ""
        for phrase in texte.replace(". ", ".\x00").split("\x00"):
            if len(courant) + len(phrase) > TAILLE_MAX_CHUNK and courant:
                morceaux.append(courant.strip())
                courant = ""
            courant += phrase + " "
        if courant.strip():
            morceaux.append(courant.strip())
        return morceaux

    # ------------------------------------------------------------------
    #  Jalon 2 : construction (une seule fois)
    # ------------------------------------------------------------------
    def construire(self, documents: list[dict], force: bool = False) -> None:
        noms = [c.name for c in self._client.list_collections()]
        if NOM_COLLECTION in noms:
            if not force:
                sys.exit("La base existe deja et sera rechargee telle quelle "
                         "a l'interrogation (pas de reindexation au "
                         "lancement !). Reconstruction volontaire : --force")
            self._client.delete_collection(NOM_COLLECTION)
            print("Ancienne collection supprimee (--force).")

        collection = self._client.create_collection(
            name=NOM_COLLECTION,
            metadata={"embedding_model": MODELE_EMBEDDING,
                      "date_indexation": date.today().isoformat(),
                      "hnsw:space": "cosine"})

        ids, textes, metas = [], [], []
        for doc in documents:
            morceaux = self._decouper(doc["texte"])
            for i, morceau in enumerate(morceaux):
                suffixe = f"__part{i + 1}" if len(morceaux) > 1 else ""
                ids.append(f"{doc['id']}{suffixe}")
                textes.append(self._texte_a_embedder(doc, morceau))
                metas.append({"numero": doc["numero"],
                              "titre": doc.get("titre", ""),
                              "section": doc["section"],
                              "source": doc["source"]})
        print(f"{len(documents)} documents -> {len(ids)} chunks.")

        # normalize_embeddings=True : produit scalaire == cosinus.
        vecteurs = self.modele.encode(textes, normalize_embeddings=True,
                                      show_progress_bar=True)
        for debut in range(0, len(ids), 500):  # insertion par lots
            fin = debut + 500
            collection.add(ids=ids[debut:fin],
                           embeddings=[v.tolist() for v in vecteurs[debut:fin]],
                           documents=textes[debut:fin],
                           metadatas=metas[debut:fin])
        print(f"Base persistee : {CHEMIN_BASE} ({collection.count()} chunks, "
              f"modele {MODELE_EMBEDDING}).")

    # ------------------------------------------------------------------
    #  Jalon 2 : rechargement (a chaque lancement, sans reindexer)
    # ------------------------------------------------------------------
    def charger(self):
        if self._collection is None:
            try:
                self._collection = self._client.get_collection(NOM_COLLECTION)
            except Exception:
                sys.exit("Base introuvable : lancer une fois "
                         "python -m src.indexation")
            modele_base = (self._collection.metadata or {}).get("embedding_model")
            if modele_base != MODELE_EMBEDDING:
                sys.exit(f"Base construite avec '{modele_base}' mais config "
                         f"= '{MODELE_EMBEDDING}' : reindexer (--force) ou "
                         "corriger config.py.")
        return self._collection

    # ------------------------------------------------------------------
    #  Jalon 3 : retrieval semantique
    # ------------------------------------------------------------------
    def rechercher(self, question: str, k: int = TOP_K) -> list[Extrait]:
        """Sur-interroge (k*3) puis deduplique par numero d'article : sans
        cela, un article sous-decoupe en plusieurs chunks pouvait occuper
        plusieurs places du top-k au detriment d'autres articles pertinents."""
        collection = self.charger()
        vecteur = self.modele.encode(question, normalize_embeddings=True)
        res = collection.query(query_embeddings=[vecteur.tolist()], n_results=k * 3)
        extraits = [Extrait(numero=m["numero"], titre=m.get("titre", ""),
                            section=m["section"], texte=t,
                            # distance cosinus d = 1 - cos => similarite = 1 - d
                            similarite=round(1 - d, 4))
                    for t, m, d in zip(res["documents"][0], res["metadatas"][0],
                                       res["distances"][0])]
        vus, dedupliques = set(), []
        for e in extraits:
            if e.numero not in vus:
                vus.add(e.numero)
                dedupliques.append(e)
        return dedupliques[:k]

    # ------------------------------------------------------------------
    #  Jalon 6 : acces exact par numero (brique de la recherche hybride)
    # ------------------------------------------------------------------
    def par_numeros(self, numeros: list[str]) -> list[Extrait]:
        """Recherche EXACTE sur la metadonnee 'numero' -- la ou le
        vectoriel echoue ("que dit L3121-1 ?" n'a aucun sens semantique)."""
        if not numeros:
            return []
        collection = self.charger()
        res = collection.get(where={"numero": {"$in": numeros}})
        return [Extrait(numero=m["numero"], titre=m.get("titre", ""),
                        section=m["section"], texte=t,
                        similarite=1.0)  # correspondance exacte demandee
                for t, m in zip(res["documents"], res["metadatas"])]
