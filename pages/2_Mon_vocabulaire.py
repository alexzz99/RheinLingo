"""Page « Mon vocabulaire » : liste en cartes, filtrable par thème et source, avec édition."""

import streamlit as st

from core import db, ui
from services import vocabulaire as voc

ui.configurer_page("Mon vocabulaire", "📚")
client = db.client_connecte()

TOUS = "Tous"

st.title("📚 Mon vocabulaire")

# Une seule carte est en édition / en attente de suppression à la fois
st.session_state.setdefault("edition_id", None)
st.session_state.setdefault("suppr_id", None)


def _editer(mot_id):
    st.session_state["edition_id"], st.session_state["suppr_id"] = mot_id, None


def _demander_suppression(mot_id):
    st.session_state["suppr_id"], st.session_state["edition_id"] = mot_id, None


def _annuler():
    st.session_state["edition_id"] = st.session_state["suppr_id"] = None


def _supprimer(mot_id):
    try:
        voc.supprimer_mot(client, mot_id)
    except Exception as e:
        st.session_state["_erreur"] = f"Suppression impossible : {e}"
    _annuler()


try:
    themes = voc.lister_themes(client)
except Exception as e:
    ui.afficher_erreur(e)
    st.stop()

# Filtres repliés par défaut pour gagner de la place sur mobile
with st.expander("🔎 Filtres"):
    theme = st.selectbox("Thème", [TOUS, *themes])
    source = st.selectbox("Source", [TOUS, *voc.SOURCES])

if "_erreur" in st.session_state:
    st.error(st.session_state.pop("_erreur"))

try:
    mots = voc.lister_mots(
        client,
        theme=None if theme == TOUS else theme,
        source=None if source == TOUS else source,
    )
except Exception as e:
    ui.afficher_erreur(e)
    st.stop()

st.caption(f"{len(mots)} mot(s)")
if not mots:
    st.info("Aucun mot pour l'instant. Utilise « Ajouter » pour commencer.")

for m in mots:
    with st.container(border=True):
        st.markdown(f"**{voc.etiqueter(m)}** — {m['traduction']}")
        meta = [x for x in (m.get("theme"), m["source"]) if x]
        if m.get("pluriel"):
            meta.insert(0, f"pl. {m['pluriel']}")
        st.caption(" · ".join(meta))

        # --- Mode édition (uniquement pour la carte choisie) ---
        if st.session_state["edition_id"] == m["id"]:
            with st.form(f"edit_{m['id']}"):
                mot = st.text_input("Mot", m["mot"])
                traduction = st.text_input("Traduction", m["traduction"])
                genres = ["", *voc.GENRES]
                genre = st.selectbox("Genre", genres, index=genres.index(m["genre"] or ""),
                                     format_func=lambda g: g or "— (pas un nom)")
                pluriel = st.text_input("Pluriel", m.get("pluriel") or "")
                exemple = st.text_area("Exemple", m.get("exemple") or "")
                src = st.selectbox("Source", voc.SOURCES, index=voc.SOURCES.index(m["source"]))
                nv_theme = st.text_input("Thème", m.get("theme") or "")
                ok = st.form_submit_button("💾 Enregistrer", type="primary", use_container_width=True)
            if ok:
                if not mot.strip() or not traduction.strip():
                    st.error("Le mot et la traduction sont obligatoires.")
                else:
                    try:
                        voc.modifier_mot(client, m["id"], {
                            "mot": mot, "traduction": traduction, "genre": genre or None,
                            "pluriel": pluriel, "exemple": exemple, "source": src, "theme": nv_theme,
                        })
                        _annuler()
                        st.rerun()
                    except Exception as e:
                        st.error("Ce mot existe déjà." if voc.est_doublon(e) else f"Échec : {e}")
            st.button("Annuler", key=f"ann_{m['id']}", use_container_width=True, on_click=_annuler)

        # --- Confirmation de suppression ---
        elif st.session_state["suppr_id"] == m["id"]:
            st.warning("Supprimer ce mot définitivement ?")
            st.button("🗑️ Oui, supprimer", key=f"ok_{m['id']}", type="primary",
                      use_container_width=True, on_click=_supprimer, args=(m["id"],))
            st.button("Annuler", key=f"non_{m['id']}", use_container_width=True, on_click=_annuler)

        # --- Affichage normal ---
        else:
            with st.expander("Détails"):
                if m.get("exemple"):
                    st.write(f"_{m['exemple']}_")
                st.button("✏️ Modifier", key=f"mod_{m['id']}", use_container_width=True,
                          on_click=_editer, args=(m["id"],))
                st.button("🗑️ Supprimer", key=f"sup_{m['id']}", use_container_width=True,
                          on_click=_demander_suppression, args=(m["id"],))
