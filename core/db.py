"""Accès à Supabase avec la clé « anon » uniquement.

Un client est créé PAR SESSION Streamlit (stocké dans st.session_state), jamais
partagé entre sessions : il porte le jeton de l'utilisateur connecté, ce qui
permet à la RLS de voir auth.uid().
"""

from __future__ import annotations

import base64
import json

import streamlit as st
from supabase import Client, create_client

from core import config


def _verifier_cle_anon(cle: str) -> None:
    """Refuse une clé service_role : elle contournerait la RLS."""
    if cle.startswith("sb_secret_"):
        raise config.ConfigManquante(
            "SUPABASE_ANON_KEY contient une clé secrète. Utilise la clé « anon / publishable »."
        )
    try:
        charge = cle.split(".")[1]
        charge += "=" * (-len(charge) % 4)  # padding base64
        role = json.loads(base64.urlsafe_b64decode(charge)).get("role")
    except Exception:
        return  # format inconnu : on ne bloque pas
    if role == "service_role":
        raise config.ConfigManquante(
            "SUPABASE_ANON_KEY contient la clé service_role. Utilise UNIQUEMENT la clé « anon »."
        )


def nouveau_client() -> Client:
    """Crée un client Supabase neuf (non authentifié)."""
    url = config.lire("SUPABASE_URL")
    cle = config.lire("SUPABASE_ANON_KEY")
    _verifier_cle_anon(cle)
    return create_client(url, cle)


def client_connecte() -> Client | None:
    """Retourne le client authentifié de la session courante, ou None."""
    return st.session_state.get("client")
