-- ============================================================================
-- RheinLingo — Migration 001 : schéma initial
-- À exécuter dans Supabase : SQL Editor > New query > coller > Run.
-- Le script est ré-exécutable sans danger (if not exists / drop policy if exists).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Table vocabulaire : un mot = une ligne
-- user_id est rempli automatiquement avec l'utilisateur connecté (auth.uid()).
-- ----------------------------------------------------------------------------
create table if not exists public.vocabulaire (
    id          bigint generated always as identity primary key,
    user_id     uuid not null default auth.uid()
                    references auth.users (id) on delete cascade,
    mot         text not null,
    traduction  text not null,
    genre       text check (genre in ('der', 'die', 'das')),   -- null si pas un nom
    pluriel     text,
    exemple     text,
    source      text not null default 'manuel'
                    check (source in ('vhs', 'goethe', 'manuel')),
    theme       text,
    cree_le     timestamptz not null default now()
);

-- Pas de doublon d'un même mot (insensible à la casse) pour un utilisateur
create unique index if not exists vocabulaire_user_mot_uniq
    on public.vocabulaire (user_id, lower(mot));
create index if not exists vocabulaire_user_theme_idx
    on public.vocabulaire (user_id, theme);

-- ----------------------------------------------------------------------------
-- Table revisions : historique des révisions (étape 2 : algorithme SM-2)
-- Chaque ligne = une révision d'un mot, avec l'état SM-2 calculé à ce moment.
-- ----------------------------------------------------------------------------
create table if not exists public.revisions (
    id                  bigint generated always as identity primary key,
    user_id             uuid not null default auth.uid()
                            references auth.users (id) on delete cascade,
    vocabulaire_id      bigint not null
                            references public.vocabulaire (id) on delete cascade,
    date_revision       timestamptz not null default now(),
    resultat            smallint not null check (resultat between 0 and 5),
    intervalle_jours    integer not null default 0 check (intervalle_jours >= 0),
    facteur_facilite    numeric(4, 2) not null default 2.5 check (facteur_facilite >= 1.3),
    prochaine_echeance  date not null default current_date
);

create index if not exists revisions_user_echeance_idx
    on public.revisions (user_id, prochaine_echeance);
create index if not exists revisions_user_mot_idx
    on public.revisions (user_id, vocabulaire_id, date_revision desc);

-- ----------------------------------------------------------------------------
-- Table erreurs : journal des fautes à retravailler (étapes 3-4)
-- ----------------------------------------------------------------------------
create table if not exists public.erreurs (
    id              bigint generated always as identity primary key,
    user_id         uuid not null default auth.uid()
                        references auth.users (id) on delete cascade,
    phrase_fautive  text not null,
    correction      text not null,
    categorie       text not null default 'autre'
                        check (categorie in (
                            'genre', 'declinaison', 'ordre_des_mots',
                            'conjugaison', 'preposition', 'autre')),
    explication     text,
    cree_le         timestamptz not null default now()
);

create index if not exists erreurs_user_categorie_idx
    on public.erreurs (user_id, categorie);

-- ----------------------------------------------------------------------------
-- Row Level Security : chaque utilisateur ne voit/modifie que ses lignes.
-- "using" filtre les lignes lues/modifiées/supprimées ;
-- "with check" contrôle les lignes écrites (insert/update).
-- ----------------------------------------------------------------------------
alter table public.vocabulaire enable row level security;
alter table public.revisions   enable row level security;
alter table public.erreurs     enable row level security;

drop policy if exists "vocabulaire_proprietaire" on public.vocabulaire;
create policy "vocabulaire_proprietaire" on public.vocabulaire
    for all to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "revisions_proprietaire" on public.revisions;
create policy "revisions_proprietaire" on public.revisions
    for all to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "erreurs_proprietaire" on public.erreurs;
create policy "erreurs_proprietaire" on public.erreurs
    for all to authenticated
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);
