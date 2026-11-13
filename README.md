# 🇩🇪 RheinLingo

Application personnelle pour apprendre l'allemand au quotidien (B1 → B2), en complément du VHS-Lernportal.
Pensée pour un usage sur smartphone (iPhone) : interface en une colonne, gros boutons.

**Étape 1 (ce dépôt) : le socle**
- Connexion par email + mot de passe (Supabase Auth, compte unique)
- Ajout d'un mot : l'IA propose traduction, genre, pluriel, exemple et thème ; tu valides ou corriges
- Liste du vocabulaire filtrable par thème et source, avec modification et suppression
- Couche LLM interchangeable : Gemini (gratuit) ou Claude

**Étapes à venir** : répétition espacée (SM-2), exercices générés, conversation, tableau de bord.
Les tables `revisions` et `erreurs` sont déjà créées pour les accueillir.

## Structure

```
app.py                    Accueil + déconnexion
pages/                    Pages Streamlit (ajout, liste)
core/                     config, llm, db, auth, ui
services/vocabulaire.py   Logique métier (IA + accès base)
migrations/001_init.sql   Schéma SQL + RLS
.streamlit/               config.toml, secrets.toml.example
```

## 1. Créer le projet Supabase

1. Sur [supabase.com](https://supabase.com), crée un projet (région proche, ex. Frankfurt).
2. **Project Settings → API** : note l'**URL** du projet et la clé **anon / publishable**.
   ⚠️ N'utilise **jamais** la clé `service_role` dans l'application : elle contourne la sécurité.

## 2. Exécuter la migration

1. Ouvre **SQL Editor → New query**.
2. Colle le contenu de `migrations/001_init.sql` et clique **Run**.
3. Vérifie dans **Table Editor** que `vocabulaire`, `revisions` et `erreurs` existent
   avec le badge « RLS enabled ».

## 3. Créer ton compte unique

1. **Authentication → Users → Add user → Create new user** : saisis ton email et un mot de passe,
   coche *Auto Confirm User*.
2. **Authentication → Sign In / Providers → Email** : désactive **Allow new users to sign up**
   (personne d'autre ne pourra créer de compte).

## 4. Obtenir une clé LLM

- **Gemini** (niveau gratuit) : clé sur [Google AI Studio](https://aistudio.google.com/apikey).
- **Claude** (optionnel) : clé sur [console.anthropic.com](https://console.anthropic.com).

Le nom du modèle n'est pas codé en dur : tu le choisis dans `LLM_MODEL`
(consulte la documentation du fournisseur pour le nom exact et les quotas).

## 5. Configurer les secrets (local)

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Édite `.streamlit/secrets.toml` : `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `LLM_PROVIDER`
(`gemini` ou `claude`), `LLM_MODEL` et la clé du fournisseur choisi.
Ce fichier est dans `.gitignore` : il ne sera jamais envoyé sur GitHub.

Pour changer de fournisseur : modifie `LLM_PROVIDER` et `LLM_MODEL`, sans toucher au code.

## 6. Lancer en local

Python 3.11+ requis.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Mac/Linux : source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

Pour tester sur ton iPhone en local (même Wi-Fi) : `streamlit run app.py --server.address 0.0.0.0`
puis ouvre `http://<ip-de-ton-pc>:8501` dans Safari.

## 7. Déployer sur Streamlit Community Cloud

1. Crée un dépôt **GitHub privé** et pousse le code (vérifie que `secrets.toml` n'y est pas).
2. Sur [share.streamlit.io](https://share.streamlit.io), **Create app** → choisis le dépôt,
   la branche et le fichier principal `app.py`.
3. **Advanced settings** : choisis Python 3.11 ou plus, puis colle dans **Secrets** le contenu de ton
   `secrets.toml` local.
4. **Deploy**. Sur l'iPhone : ouvre l'URL dans Safari → Partager → **Sur l'écran d'accueil**.

## Dépannage

| Symptôme | Cause probable |
|---|---|
| « Quota … atteint » | Limite du niveau gratuit (erreur 429) : attends, ou passe `LLM_PROVIDER=claude`. |
| La liste est vide alors que le mot existe | Le mot a été créé avec un autre utilisateur (la RLS filtre par `user_id`). |
| « Email ou mot de passe incorrect » | Vérifie le compte dans Supabase et qu'il est confirmé. |
| « La variable … est absente » | Il manque une clé dans `secrets.toml` / les Secrets Streamlit Cloud. |
| « … contient la clé service_role » | Remplace par la clé **anon**. |
