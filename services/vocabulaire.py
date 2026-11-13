"""Logique métier du vocabulaire : complétion par l'IA et accès à la table `vocabulaire`.

Toutes les fonctions d'accès reçoivent le client Supabase authentifié ;
la RLS garantit qu'on ne touche que ses propres lignes.
"""

from __future__ import annotations

import json

from supabase import Client

from core.llm import FournisseurLLM, LLMError

SOURCES = ["vhs", "goethe", "manuel"]
GENRES = ["der", "die", "das"]

_SYSTEME = (
    "Tu es un professeur d'allemand qui aide un apprenant francophone de niveau B1-B2. "
    "Tu réponds uniquement par un objet JSON valide, sans texte autour."
)


# --------------------------------------------------------------------------
# Complétion par l'IA
# --------------------------------------------------------------------------
def completer_mot(llm: FournisseurLLM, mot: str, themes_existants: list[str]) -> dict:
    """Demande au LLM traduction, genre, pluriel, exemple et thème pour `mot`.

    Retourne un dict avec les clés : traduction, genre, pluriel, exemple, theme.
    """
    themes = ", ".join(themes_existants) if themes_existants else "(aucun pour l'instant)"
    prompt = f"""Mot allemand : « {mot} »

Renvoie un objet JSON avec exactement ces clés :
- "traduction" : traduction française courte (plusieurs sens séparés par « ; » si utile)
- "genre" : "der", "die" ou "das" si c'est un nom, sinon null
- "pluriel" : forme du pluriel sans article (ex. "Häuser") si c'est un nom, sinon null
- "exemple" : une phrase d'exemple naturelle en allemand, niveau B1-B2, utilisant le mot
- "theme" : un thème court en français (1-2 mots). Réutilise un thème existant s'il convient : {themes}
"""
    texte = llm.generer(prompt, _SYSTEME)
    return _parser_json(texte)


def _parser_json(texte: str) -> dict:
    """Extrait l'objet JSON de la réponse (tolère les balises ```json ... ```)."""
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin <= debut:
        raise LLMError("La réponse de l'IA n'est pas exploitable. Réessaie.")
    try:
        brut = json.loads(texte[debut : fin + 1])
    except json.JSONDecodeError as e:
        raise LLMError("La réponse de l'IA n'est pas un JSON valide. Réessaie.") from e

    genre = str(brut.get("genre") or "").strip().lower()
    return {
        "traduction": str(brut.get("traduction") or "").strip(),
        "genre": genre if genre in GENRES else None,
        "pluriel": str(brut.get("pluriel") or "").strip(),
        "exemple": str(brut.get("exemple") or "").strip(),
        "theme": str(brut.get("theme") or "").strip(),
    }


# --------------------------------------------------------------------------
# Accès base de données
# --------------------------------------------------------------------------
def _nettoyer(donnees: dict) -> dict:
    """Chaînes vides -> None (sauf champs obligatoires), espaces retirés."""
    propre = {}
    for cle, valeur in donnees.items():
        if isinstance(valeur, str):
            valeur = valeur.strip() or None
        propre[cle] = valeur
    return propre


def ajouter_mot(client: Client, donnees: dict) -> None:
    """Insère un mot. user_id est rempli par la base (auth.uid())."""
    client.table("vocabulaire").insert(_nettoyer(donnees)).execute()


def modifier_mot(client: Client, mot_id: int, donnees: dict) -> None:
    """Met à jour un mot existant."""
    client.table("vocabulaire").update(_nettoyer(donnees)).eq("id", mot_id).execute()


def supprimer_mot(client: Client, mot_id: int) -> None:
    """Supprime un mot (et ses révisions, par cascade)."""
    client.table("vocabulaire").delete().eq("id", mot_id).execute()


def lister_mots(
    client: Client, theme: str | None = None, source: str | None = None, limite: int = 200
) -> list[dict]:
    """Liste les mots, du plus récent au plus ancien, avec filtres optionnels."""
    requete = client.table("vocabulaire").select("*").order("cree_le", desc=True).limit(limite)
    if theme:
        requete = requete.eq("theme", theme)
    if source:
        requete = requete.eq("source", source)
    return requete.execute().data


def lister_themes(client: Client) -> list[str]:
    """Thèmes déjà utilisés (distincts, triés)."""
    lignes = client.table("vocabulaire").select("theme").execute().data
    return sorted({l["theme"] for l in lignes if l.get("theme")}, key=str.lower)


def est_doublon(erreur: Exception) -> bool:
    """Vrai si l'erreur vient de l'index d'unicité (mot déjà enregistré)."""
    return "23505" in str(erreur) or "duplicate" in str(erreur).lower()


def etiqueter(m: dict) -> str:
    """« das Haus » ou simplement « laufen » si pas de genre."""
    return f"{m['genre']} {m['mot']}" if m.get("genre") else m["mot"]
