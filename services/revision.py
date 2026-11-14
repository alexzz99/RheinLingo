"""Répétition espacée (algorithme SM-2) : calcul, file du jour et enregistrement.

`revisions` est un journal : l'état d'un mot est sa dernière ligne. Un mot sans
ligne est un mot nouveau. Aucun appel LLM ici.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from supabase import Client

FUSEAU = ZoneInfo("Europe/Berlin")
NOUVEAUX_PAR_JOUR = 10
FACILITE_INITIALE = 2.5
FACILITE_MIN = 1.3

# Notes proposées à l'écran (SM-2 en accepte 0 à 5, les notes < 3 sont un échec)
NOTE_A_REVOIR, NOTE_DIFFICILE, NOTE_BIEN, NOTE_FACILE = 1, 3, 4, 5

_ARTICLES = r"(?:der|die|das|den|dem|des|ein|eine|einen|einem|einer|eines)"


def aujourdhui() -> date:
    """Date du jour à Berlin (le jour change à minuit heure de Berlin, pas en UTC)."""
    return datetime.now(FUSEAU).date()


# --------------------------------------------------------------------------
# Algorithme SM-2 (fonction pure)
# --------------------------------------------------------------------------
def calculer_sm2(
    resultat: int, intervalle: int, facteur: float, repetitions: int
) -> tuple[int, float, int]:
    """Retourne (nouvel intervalle en jours, nouveau facteur, nouvelles répétitions).

    - note < 3 : échec, retour à 1 jour, répétitions remises à 0, facteur inchangé ;
    - sinon : 1er succès -> 1 jour, 2e -> 6 jours, ensuite intervalle * facteur,
      et le facteur évolue selon la note.
    """
    if resultat < 3:
        return 1, facteur, 0

    repetitions += 1
    if repetitions == 1:
        nouvel_intervalle = 1
    elif repetitions == 2:
        nouvel_intervalle = 6
    else:
        nouvel_intervalle = round(intervalle * facteur)

    ecart = 5 - resultat
    nouveau_facteur = max(FACILITE_MIN, facteur + 0.1 - ecart * (0.08 + ecart * 0.02))
    return nouvel_intervalle, round(nouveau_facteur, 2), repetitions


# --------------------------------------------------------------------------
# Lecture de l'état et file du jour
# --------------------------------------------------------------------------
def _lire_tout(requete_fabrique, taille: int = 1000) -> list[dict]:
    """Lit toutes les lignes d'une requête par pages (PostgREST plafonne à 1000)."""
    lignes, debut = [], 0
    while True:
        page = requete_fabrique().range(debut, debut + taille - 1).execute().data
        lignes.extend(page)
        if len(page) < taille:
            return lignes
        debut += taille


def _jour_berlin(horodatage: str) -> date:
    """Convertit un timestamptz renvoyé par Supabase en date de Berlin."""
    return datetime.fromisoformat(horodatage).astimezone(FUSEAU).date()


def _etat(revisions: list[dict]) -> dict:
    """État SM-2 d'un mot à partir de ses révisions (de la plus récente à la plus ancienne)."""
    repetitions = 0
    for r in revisions:
        if r["resultat"] < 3:
            break
        repetitions += 1
    derniere = revisions[0]
    return {
        "intervalle": derniere["intervalle_jours"],
        "facteur": float(derniere["facteur_facilite"]),
        "repetitions": repetitions,
        "echeance": date.fromisoformat(derniere["prochaine_echeance"]),
    }


def mots_a_reviser(client: Client, nouveaux_max: int = NOUVEAUX_PAR_JOUR) -> list[dict]:
    """File du jour : mots échus (illimités, les plus en retard d'abord) puis mots nouveaux.

    Les nouveaux sont plafonnés : le quota du jour tient compte des mots
    déjà vus pour la première fois aujourd'hui. Chaque mot retourné porte une
    clé « etat » (intervalle, facteur, repetitions).
    """
    aujourd = aujourdhui()
    mots = _lire_tout(
        lambda: client.table("vocabulaire")
        .select("id, mot, traduction, genre, pluriel, exemple, theme, cree_le")
        .order("id")
    )
    revisions = _lire_tout(
        lambda: client.table("revisions")
        .select("vocabulaire_id, date_revision, resultat, intervalle_jours, "
                "facteur_facilite, prochaine_echeance")
        .order("date_revision", desc=True)
        .order("id", desc=True)
    )

    par_mot: dict[int, list[dict]] = {}
    for r in revisions:
        par_mot.setdefault(r["vocabulaire_id"], []).append(r)

    echus, nouveaux = [], []
    vus_aujourdhui = 0
    for m in mots:
        historique = par_mot.get(m["id"])
        if not historique:
            nouveaux.append({**m, "etat": {"intervalle": 0, "facteur": FACILITE_INITIALE,
                                           "repetitions": 0}})
            continue
        # Première révision = la plus ancienne (dernier élément de la liste)
        if _jour_berlin(historique[-1]["date_revision"]) == aujourd:
            vus_aujourdhui += 1
        etat = _etat(historique)
        if etat["echeance"] <= aujourd:
            echus.append({**m, "etat": etat})

    echus.sort(key=lambda m: m["etat"]["echeance"])
    quota = max(0, nouveaux_max - vus_aujourdhui)
    return echus + nouveaux[:quota]


def enregistrer_revision(client: Client, mot_id: int, resultat: int, etat: dict) -> None:
    """Calcule le nouvel état SM-2 et l'ajoute au journal. user_id vient de la base."""
    intervalle, facteur, _ = calculer_sm2(
        resultat, etat["intervalle"], etat["facteur"], etat["repetitions"]
    )
    client.table("revisions").insert({
        "vocabulaire_id": mot_id,
        "resultat": resultat,
        "intervalle_jours": intervalle,
        "facteur_facilite": facteur,
        "prochaine_echeance": (aujourdhui() + timedelta(days=intervalle)).isoformat(),
    }).execute()


# --------------------------------------------------------------------------
# Indice : phrase d'exemple avec un blanc à la place du mot
# --------------------------------------------------------------------------
def masquer_phrase(phrase: str | None, mot: str, pluriel: str | None, genre: str | None) -> str | None:
    """Remplace le mot (ou son pluriel) par « ____ » dans la phrase.

    Pour un nom (genre connu), l'article collé au mot est masqué aussi, afin de
    ne pas révéler le genre. Retourne None si la phrase est vide ou si le mot
    n'y apparaît pas tel quel (le bouton « Indice » n'est alors pas proposé).
    """
    if not phrase or not mot:
        return None
    formes = [f for f in (mot, pluriel) if f and f.strip()]
    motif = "|".join(re.escape(f.strip()) for f in sorted(formes, key=len, reverse=True))
    article = rf"(?:{_ARTICLES}\s+)?" if genre else ""
    regex = re.compile(rf"(?<!\w){article}(?:{motif})(?!\w)", re.IGNORECASE)
    if not regex.search(phrase):
        return None
    return regex.sub("____", phrase)
