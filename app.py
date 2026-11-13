"""Point d'entrée de RheinLingo (accueil).

Lancement : streamlit run app.py
"""

import streamlit as st

from core import auth, db, ui
from services import vocabulaire

ui.configurer_page("Accueil")  # inclut la garde de connexion

client = db.client_connecte()

st.title("🇩🇪 RheinLingo")
st.caption(f"Connecté : {st.session_state.get('email', '')}")

try:
    nb_mots = len(vocabulaire.lister_mots(client, limite=1000))
    st.metric("Mots dans ton vocabulaire", nb_mots)
except Exception as e:
    ui.afficher_erreur(e)

st.page_link("pages/1_Ajouter_un_mot.py", label="Ajouter un mot", icon="➕", use_container_width=True)
st.page_link("pages/2_Mon_vocabulaire.py", label="Mon vocabulaire", icon="📚", use_container_width=True)

# Étapes suivantes (non développées) : révision espacée, exercices, conversation, tableau de bord.

st.divider()
if st.button("Se déconnecter", use_container_width=True):
    auth.se_deconnecter()
    st.rerun()
