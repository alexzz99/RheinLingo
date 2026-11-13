"""Authentification Supabase (email + mot de passe, compte unique).

Toutes les pages appellent `exiger_connexion()` en première ligne :
sans session valide, seul le formulaire de connexion est affiché.
"""

from __future__ import annotations

import streamlit as st
from supabase import Client

from core import config, db


def _se_connecter(email: str, mot_de_passe: str) -> None:
    """Tente la connexion ; mémorise le client authentifié dans la session."""
    client = db.nouveau_client()
    reponse = client.auth.sign_in_with_password({"email": email, "password": mot_de_passe})
    if reponse.user is None:
        raise ValueError("Connexion refusée.")
    st.session_state["client"] = client
    st.session_state["email"] = reponse.user.email


def se_deconnecter() -> None:
    """Ferme la session Supabase et vide l'état Streamlit."""
    client = db.client_connecte()
    if client is not None:
        try:
            client.auth.sign_out()
        except Exception:
            pass  # on vide l'état local quoi qu'il arrive
    st.session_state.clear()


def exiger_connexion() -> Client:
    """Retourne le client connecté, ou affiche la page de connexion et stoppe le script."""
    client = db.client_connecte()
    if client is not None:
        return client

    st.title("🇩🇪 RheinLingo")
    st.caption("Connexion requise")

    # Un formulaire avec des clés stables : le trousseau iCloud peut remplir les champs.
    with st.form("connexion"):
        email = st.text_input("Email", key="login_email")
        mot_de_passe = st.text_input("Mot de passe", type="password", key="login_mdp")
        envoye = st.form_submit_button("Se connecter", use_container_width=True, type="primary")

    if envoye:
        try:
            _se_connecter(email.strip(), mot_de_passe)
            st.rerun()
        except config.ConfigManquante as e:
            st.error(str(e))
        except Exception:
            # Message volontairement vague : on ne détaille pas la cause à un inconnu.
            st.error("Email ou mot de passe incorrect.")
    st.stop()
