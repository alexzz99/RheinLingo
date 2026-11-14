"""Page « Réviser » : répétition espacée FR → DE (algorithme SM-2).

Face avant : le mot français + le thème (+ bouton « Indice » : phrase à trou).
Face arrière : article + mot allemand + phrase d'exemple. Auto-évaluation en 4 notes.
"""

import streamlit as st

from core import db, ui
from services import revision as rev
from services import vocabulaire as voc

ui.configurer_page("Réviser", "🧠")
client = db.client_connecte()

st.title("🧠 Réviser")


# --------------------------------------------------------------------------
# État de la session de révision (clés préfixées r_)
# --------------------------------------------------------------------------
def _charger_file():
    """Construit la file du jour et réinitialise la progression."""
    mots = rev.mots_a_reviser(client)
    st.session_state["r_mots"] = {m["id"]: m for m in mots}
    st.session_state["r_file"] = [m["id"] for m in mots]
    st.session_state["r_pos"] = 0
    st.session_state["r_total"] = len(mots)
    st.session_state["r_valides"] = 0
    st.session_state["r_notes"] = set()  # mots déjà notés dans cette session
    st.session_state["r_revele"] = False
    st.session_state["r_indice"] = False


def _recharger():
    for cle in [c for c in st.session_state if c.startswith("r_")]:
        del st.session_state[cle]


def _reveler():
    st.session_state["r_revele"] = True


def _indice():
    st.session_state["r_indice"] = True


def _noter(mot_id: int, note: int):
    """Enregistre la note (la première seulement : les repasses ne touchent pas SM-2)."""
    mot = st.session_state["r_mots"][mot_id]
    if mot_id not in st.session_state["r_notes"]:
        try:
            rev.enregistrer_revision(client, mot_id, note, mot["etat"])
        except Exception as e:
            st.session_state["_erreur_r"] = f"Enregistrement impossible : {e}"
            return
        st.session_state["r_notes"].add(mot_id)

    if note < 3:
        st.session_state["r_file"].append(mot_id)  # la carte revient en fin de file
    else:
        st.session_state["r_valides"] += 1
    st.session_state["r_pos"] += 1
    st.session_state["r_revele"] = False
    st.session_state["r_indice"] = False


if "r_file" not in st.session_state:
    try:
        _charger_file()
    except Exception as e:
        ui.afficher_erreur(e)
        st.stop()

if "_erreur_r" in st.session_state:
    st.error(st.session_state.pop("_erreur_r"))

file_ = st.session_state["r_file"]
pos = st.session_state["r_pos"]
total = st.session_state["r_total"]

# --------------------------------------------------------------------------
# Écrans de fin
# --------------------------------------------------------------------------
if total == 0:
    st.success("Rien à réviser pour le moment. Reviens demain, ou ajoute des mots.")
    st.button("🔄 Actualiser", use_container_width=True, on_click=_recharger)
    st.stop()

if pos >= len(file_):
    st.success(f"🎉 Session terminée : {total} mot(s) révisé(s).")
    st.button("🔄 Actualiser la file", use_container_width=True, on_click=_recharger)
    st.stop()

# --------------------------------------------------------------------------
# Carte courante
# --------------------------------------------------------------------------
mot = st.session_state["r_mots"][file_[pos]]
revele = st.session_state["r_revele"]
indice_utilise = st.session_state["r_indice"]

st.progress(st.session_state["r_valides"] / total,
            text=f"{st.session_state['r_valides']}/{total} validés")

phrase_a_trou = rev.masquer_phrase(mot.get("exemple"), mot["mot"], mot.get("pluriel"), mot.get("genre"))

with st.container(border=True):
    st.markdown(f"### {mot['traduction']}")
    if mot.get("theme"):
        st.caption(f"Thème : {mot['theme']}")

    if not revele:
        if indice_utilise and phrase_a_trou:
            st.info(phrase_a_trou)
    else:
        st.markdown(f"## {voc.etiqueter(mot)}")
        if mot.get("pluriel"):
            st.caption(f"pluriel : {mot['pluriel']}")
        if mot.get("exemple"):
            st.write(f"_{mot['exemple']}_")

if not revele:
    if phrase_a_trou and not indice_utilise:
        st.button("💡 Indice", use_container_width=True, on_click=_indice)
    st.button("👁️ Montrer la réponse", type="primary", use_container_width=True,
              on_click=_reveler)
else:
    st.caption("Comment tu t'en es sorti ?")
    st.button("🔁 À revoir", key="n1", use_container_width=True,
              on_click=_noter, args=(mot["id"], rev.NOTE_A_REVOIR))
    st.button("😐 Difficile", key="n3", use_container_width=True,
              on_click=_noter, args=(mot["id"], rev.NOTE_DIFFICILE))
    st.button("👍 Bien", key="n4", use_container_width=True,
              on_click=_noter, args=(mot["id"], rev.NOTE_BIEN))
    st.button("⚡ Facile", key="n5", use_container_width=True, disabled=indice_utilise,
              help="Réservé aux mots trouvés sans indice" if indice_utilise else None,
              on_click=_noter, args=(mot["id"], rev.NOTE_FACILE))
