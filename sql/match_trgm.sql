-- =====================================================================
-- Matching flou côté base avec PostgreSQL (pg_trgm + unaccent).
-- Montre l'approche SQL : similarité trigramme sur les noms normalisés
-- (insensible à la casse et aux accents), complément du module Python.
-- =====================================================================
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

CREATE SCHEMA IF NOT EXISTS dedup;

DROP TABLE IF EXISTS dedup.clients;
CREATE TABLE dedup.clients (
    row_id text, true_id int, first_name text, last_name text,
    email text, phone text, city text, birthdate text, source text
);
-- Chargement : \copy dedup.clients(row_id,true_id,first_name,last_name,email,phone,city,birthdate)
--   FROM 'data/source_a.csv' CSV HEADER  (idem source_b, puis UPDATE source)

-- Nom normalisé (minuscule + sans accent) pour la similarité
CREATE OR REPLACE VIEW dedup.v_clients AS
SELECT *, lower(unaccent(coalesce(first_name,'') || ' ' || coalesce(last_name,''))) AS name_norm,
          lower(unaccent(coalesce(email,''))) AS email_norm
FROM dedup.clients;

-- Paires candidates : similarité de noms >= 0.6 OU email identique, sur des lignes distinctes.
-- (En vrai : on ajouterait un blocking pour éviter le produit cartésien.)
--   SELECT a.row_id, b.row_id,
--          round(similarity(a.name_norm, b.name_norm)::numeric, 2) AS sim_nom,
--          (a.email_norm = b.email_norm AND a.email_norm <> '') AS meme_email
--   FROM dedup.v_clients a
--   JOIN dedup.v_clients b ON a.row_id < b.row_id
--   WHERE similarity(a.name_norm, b.name_norm) >= 0.6
--      OR (a.email_norm = b.email_norm AND a.email_norm <> '')
--   ORDER BY sim_nom DESC
--   LIMIT 20;
