"""Page « Ajouter un mot » : saisie -> complétion par l'IA -> validation/correction -> enregistrement."""

import streamlit as st

from core import db, ui
from core.llm import obtenir_llm
from services import vocabulaire as voc

ui.configurer_page("Ajouter un mot", "➕")
client = db.client_connecte()

AUCUN = "— aucun —"
NOUVEAU = "➕ Nouveau thème…"

# Valeurs initiales des champs (clés stables : l'état survit si Safari recharge la page)
for cle, defaut in {
    "a_mot": "", "a_traduction": "", "a_genre": "", "a_pluriel": "", "a_exemple": "",
    "a_source": "manuel", "a_theme_choix": AUCUN, "a_theme_nouveau": "", "a_visible": False,
}.items():
    st.session_state.setdefault(cle, defaut)


def _reinitialiser() -> None:
    """Remet le formulaire à zéro (appelé depuis un callback, donc avant le rendu)."""
    for cle, defaut in {
        "a_mot": "", "a_traduction": "", "a_genre": "", "a_pluriel": "", "a_exemple": "",
        "a_theme_choix": AUCUN, "a_theme_nouveau": "", "a_visible": False,
    }.items():
        st.session_state[cle] = defaut


def _enregistrer() -> None:
    """Callback du bouton « Enregistrer » : valide, insère, prépare un message."""
    s = st.session_state
    mot, traduction = s["a_mot"].strip(), s["a_traduction"].strip()
    if not mot or not traduction:
        s["_erreur"] = "Le mot et la traduction sont obligatoires."
        return

    if s["a_theme_choix"] == NOUVEAU:
        theme = s["a_theme_nouveau"].strip()
    elif s["a_theme_choix"] == AUCUN:
        theme = ""
    else:
        theme = s["a_theme_choix"]

    try:
        voc.ajouter_mot(client, {
            "mot": mot,
            "traduction": traduction,
            "genre": s["a_genre"] or None,
            "pluriel": s["a_pluriel"],
            "exemple": s["a_exemple"],
            "source": s["a_source"],
            "theme": theme,
        })
    except Exception as e:
        s["_erreur"] = (
            f"« {mot} » est déjà dans ton vocabulaire." if voc.est_doublon(e) else f"Échec de l'enregistrement : {e}"
        )
        return
    s["_succes"] = f"✅ « {mot} » enregistré."
    _reinitialiser()


st.title("➕ Ajouter un mot")

# Messages laissés par le callback d'enregistrement
if "_succes" in st.session_state:
    st.success(st.session_state.pop("_succes"))
if "_erreur" in st.session_state:
    st.error(st.session_state.pop("_erreur"))

try:
    themes = voc.lister_themes(client)
except Exception as e:
    ui.afficher_erreur(e)
    st.stop()

st.text_input("Mot allemand", key="a_mot", placeholder="ex. Haus, laufen, trotzdem…")

# 1) Complétion par l'IA ; 2) ou saisie à la main (utile si le quota est atteint)
if st.button("✨ Compléter avec l'IA", type="primary", use_container_width=True,
             disabled=not st.session_state["a_mot"].strip()):
    try:
        with st.spinner("L'IA réfléchit…"):
            propose = voc.completer_mot(obtenir_llm(), st.session_state["a_mot"].strip(), themes)
        s = st.session_state
        s["a_traduction"] = propose["traduction"]
        s["a_genre"] = propose["genre"] or ""
        s["a_pluriel"] = propose["pluriel"]
        s["a_exemple"] = propose["exemple"]
        if propose["theme"] in themes:
            s["a_theme_choix"], s["a_theme_nouveau"] = propose["theme"], ""
        elif propose["theme"]:
            s["a_theme_choix"], s["a_theme_nouveau"] = NOUVEAU, propose["theme"]
        s["a_visible"] = True
    except Exception as e:
        ui.afficher_erreur(e)

if not st.session_state["a_visible"]:
    if st.button("Saisir à la main (sans IA)", use_container_width=True):
        st.session_state["a_visible"] = True
        st.rerun()

# Champs éditables : tu valides ou corriges avant d'enregistrer
if st.session_state["a_visible"]:
    st.divider()
    st.caption("Vérifie et corrige si besoin, puis enregistre.")
    st.text_input("Traduction", key="a_traduction")
    st.selectbox("Genre", ["", *voc.GENRES], key="a_genre",
                 format_func=lambda g: g or "— (pas un nom)")
    st.text_input("Pluriel", key="a_pluriel")
    st.text_area("Exemple", key="a_exemple", height=100)
    st.selectbox("Source", voc.SOURCES, key="a_source")
    st.selectbox("Thème", [AUCUN, *themes, NOUVEAU], key="a_theme_choix")
    if st.session_state["a_theme_choix"] == NOUVEAU:
        st.text_input("Nom du nouveau thème", key="a_theme_nouveau")

    st.button("💾 Enregistrer", type="primary", use_container_width=True, on_click=_enregistrer)
    st.button("Annuler", use_container_width=True, on_click=_reinitialiser)
