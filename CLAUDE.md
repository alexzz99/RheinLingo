# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

RheinLingo : app personnelle d'apprentissage de l'allemand (B1→B2), Streamlit + Supabase (PostgreSQL) + LLM (Gemini par défaut, Claude en alternative). Code, commentaires, docstrings, UI et README sont **en français** ; garder cette convention. L'UI est pensée mobile (iPhone 11) : une colonne, boutons pleine largeur, pas de gros tableaux.

Étapes 1 (socle) et 2 (répétition espacée SM-2, `services/revision.py` + `pages/3_Reviser.py`) terminées. Restent à faire, une étape à la fois et seulement sur demande : exercices générés, conversation, tableau de bord. Le vocabulaire du domaine est dans `GLOSSARY.md`.

Révision : FR→DE uniquement. `revisions` est un journal (l'état d'un mot = sa dernière ligne, un mot sans ligne = nouveau). Jour calculé à Berlin (`revision.aujourdhui()`), jamais avec `current_date` côté base. Seule la première note d'un mot par session est enregistrée.

## Commandes

```bash
python -m venv .venv && .venv\Scripts\activate   # Python 3.11+
pip install -r requirements.txt
streamlit run app.py                              # lancement local
python -m py_compile app.py pages/*.py core/*.py services/*.py   # seul contrôle disponible (pas de tests ni de linter)
```

Config : copier `.streamlit/secrets.toml.example` vers `.streamlit/secrets.toml` (ignoré par git). Le schéma se déploie en collant `migrations/001_init.sql` dans le SQL Editor de Supabase (script ré-exécutable).

## Architecture

- **Garde d'authentification** : chaque page appelle `ui.configurer_page(...)` en première ligne ; elle fait `st.set_page_config`, puis `auth.exiger_connexion()` (affiche le login et `st.stop()` sans session), puis la barre de navigation. Toute nouvelle page doit suivre ce schéma, sinon elle est accessible sans connexion.
- **Client Supabase par session** : `db.nouveau_client()` crée un client (clé `anon` uniquement ; `service_role` refusée par `_verifier_cle_anon`), stocké dans `st.session_state["client"]` après `sign_in_with_password`. Ne jamais le mettre dans `st.cache_resource` (il porte le jeton de l'utilisateur ; la RLS repose sur `auth.uid()`). Récupération : `db.client_connecte()`.
- **user_id automatique** : les colonnes `user_id` ont `default auth.uid()` ; le code n'envoie jamais `user_id`. RLS `auth.uid() = user_id` sur les 3 tables.
- **Couche LLM** (`core/llm.py`) : interface `FournisseurLLM.generer(prompt, systeme)`, implémentations `GeminiLLM` / `ClaudeLLM`, fabrique `obtenir_llm()` pilotée par `LLM_PROVIDER` et `LLM_MODEL`. Aucun nom de modèle en dur. Les 429 sont convertis en `LLMQuotaError` ; l'UI passe par `ui.afficher_erreur`.
- **Configuration** : `core/config.lire()` lit `st.secrets` puis les variables d'environnement (même mécanisme en local et sur Streamlit Cloud).
- **Services** (`services/vocabulaire.py`) : logique métier + CRUD, reçoivent le client en paramètre ; `completer_mot` demande un JSON au LLM et le parse de façon tolérante.
- **Pages Streamlit** : l'état des formulaires vit dans `st.session_state` avec des clés préfixées (`a_*` pour « Ajouter »). Les mutations d'état de widgets se font dans des callbacks `on_click` (ou avant l'instanciation du widget), sinon Streamlit lève une exception. Dans « Mon vocabulaire », une seule carte à la fois est en édition (`edition_id`) ou en confirmation de suppression (`suppr_id`) pour éviter de rendre N formulaires.
