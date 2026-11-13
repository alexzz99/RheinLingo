"""Lecture de la configuration.

Ordre de recherche : st.secrets (secrets.toml en local, « Secrets » sur
Streamlit Community Cloud), puis variables d'environnement.
"""

from __future__ import annotations

import os

import streamlit as st


class ConfigManquante(Exception):
    """Une valeur de configuration obligatoire est absente."""


def lire(nom: str, obligatoire: bool = True) -> str | None:
    """Retourne la valeur de configuration `nom`.

    Lève ConfigManquante si elle est absente et `obligatoire` est vrai.
    """
    valeur = None
    try:
        if nom in st.secrets:
            valeur = st.secrets[nom]
    except Exception:
        # Pas de fichier secrets.toml : on passe aux variables d'environnement.
        pass
    if valeur is None:
        valeur = os.environ.get(nom)

    valeur = str(valeur).strip() if valeur is not None else None
    if not valeur:
        if obligatoire:
            raise ConfigManquante(
                f"La variable « {nom} » est absente. "
                "Renseigne-la dans .streamlit/secrets.toml (ou dans les Secrets Streamlit Cloud)."
            )
        return None
    return valeur
