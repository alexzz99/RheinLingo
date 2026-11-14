"""Éléments d'interface communs, pensés pour un smartphone (iPhone 11, ~414 px)."""

from __future__ import annotations

import streamlit as st

from core import auth, config
from core.llm import LLMError, LLMQuotaError

# Marges réduites et boutons plus hauts (plus faciles à toucher au doigt).
_CSS = """
<style>
.block-container { padding: 1rem 0.9rem 4rem 0.9rem; }
.stButton > button, .stFormSubmitButton > button { min-height: 2.8rem; }
h1 { font-size: 1.7rem !important; }
</style>
"""


def configurer_page(titre: str, icone: str = "🇩🇪") -> None:
    """À appeler en tout premier dans chaque page : mise en page mobile + garde de connexion."""
    st.set_page_config(
        page_title=f"{titre} · RheinLingo",
        page_icon=icone,
        layout="centered",  # une seule colonne
        initial_sidebar_state="collapsed",
    )
    st.markdown(_CSS, unsafe_allow_html=True)
    auth.exiger_connexion()
    barre_navigation()


def barre_navigation() -> None:
    """Navigation en haut de page (évite d'ouvrir le menu burger sur mobile)."""
    with st.popover("☰ Menu", use_container_width=True):
        st.page_link("app.py", label="Accueil", icon="🏠", use_container_width=True)
        st.page_link("pages/3_Reviser.py", label="Réviser", icon="🧠", use_container_width=True)
        st.page_link("pages/1_Ajouter_un_mot.py", label="Ajouter un mot", icon="➕",
                     use_container_width=True)
        st.page_link("pages/2_Mon_vocabulaire.py", label="Mon vocabulaire", icon="📚",
                     use_container_width=True)


def afficher_erreur(e: Exception) -> None:
    """Transforme une exception technique en message clair pour l'UI."""
    if isinstance(e, LLMQuotaError):
        st.warning(f"⏳ {e}")
    elif isinstance(e, (LLMError, config.ConfigManquante)):
        st.error(str(e))
    else:
        st.error(f"Une erreur est survenue : {e}")
