from src.base_vectorielle import BaseVectorielle
from src.config import TOP_K

# (question, ensemble d'articles attendus) -- a enrichir au fil du projet.
# Le test reussit si AU MOINS UN des articles attendus remonte en top-k.
QUESTIONS_TEST = [
    ("Quelle est la duree legale du travail par semaine ?", {"L3121-27"}),
    ("Combien de jours de conges payes par mois de travail ?", {"L3141-3", "L3141-4"}),
    ("Quelle est la duree du preavis en cas de licenciement ?", {"L1234-1"}),
    ("Comment fonctionne la rupture conventionnelle ?", {"L1237-11", "L1237-13"}),
    ("Qu'est-ce que le harcelement moral au travail ?", {"L1152-1"}),
    ("La rupture conventionnelle peut-elle etre imposee par l'employeur ?", {"L1237-11"}),
]

# Questions volontairement HORS corpus : leurs similarites donnent le
# "plancher" sous lequel placer SEUIL_CONFIANCE.
QUESTIONS_HORS_CORPUS = [
    "Quelle est la capitale de l'Australie ?",
    "Comment fonctionne l'impot sur le revenu ?",
]


def evaluer(k: int = TOP_K) -> None:
    base = BaseVectorielle()
    succes = 0
    for question, attendus in QUESTIONS_TEST:
        extraits = base.rechercher(question, k)
        numeros = [e.numero for e in extraits]
        trouve = bool(attendus & set(numeros))
        succes += trouve
        print(f"[{'OK  ' if trouve else 'RATE'}] {question}")
        print(f"       attendu {sorted(attendus)} | top-{k} : "
              f"{[(e.numero, e.similarite) for e in extraits]}")
    print(f"\nScore : {succes}/{len(QUESTIONS_TEST)}")
    if succes < len(QUESTIONS_TEST):
        print("Diagnostic : corpus ? chunking ? en-tete d'embedding ? "
              "-- ne PAS toucher au LLM.")

    print("\n=== Calibration du seuil : similarites hors corpus ===")
    for question in QUESTIONS_HORS_CORPUS:
        meilleure = base.rechercher(question, 1)[0].similarite
        print(f"  {meilleure:.2f}  <- {question}")
    print("SEUIL_CONFIANCE doit se situer entre ces valeurs et celles "
          "des bonnes reponses ci-dessus.")


if __name__ == "__main__":
    evaluer()
