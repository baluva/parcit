-- Contrôles de qualité du parc informatique (DuckDB).
-- Chaque requête renvoie les lignes en écart, à remonter au manager.

CREATE OR REPLACE VIEW equipements AS SELECT * FROM read_csv_auto('data/equipements.csv');
CREATE OR REPLACE VIEW utilisateurs AS SELECT * FROM read_csv_auto('data/utilisateurs.csv');
CREATE OR REPLACE VIEW mouvements AS SELECT * FROM read_csv_auto('data/mouvements.csv');

-- 1. Numéros de série en doublon
CREATE OR REPLACE VIEW ctl_doublons_serie AS
SELECT e.id_equipement, e.numero_serie, e.type, e.site
FROM equipements e
WHERE e.numero_serie IN (SELECT numero_serie FROM equipements GROUP BY 1 HAVING count(*) > 1);

-- 2. Matériel encore attribué à un collaborateur parti
CREATE OR REPLACE VIEW ctl_attribue_parti AS
SELECT e.id_equipement, e.type, e.matricule, u.date_depart
FROM equipements e JOIN utilisateurs u USING (matricule)
WHERE e.statut = 'attribué' AND u.statut = 'parti';

-- 3. Statut en base différent du dernier mouvement enregistré
CREATE OR REPLACE VIEW ctl_statut_incoherent AS
WITH dernier AS (
    SELECT id_equipement, type AS dernier_mvt
    FROM mouvements
    QUALIFY row_number() OVER (PARTITION BY id_equipement ORDER BY date DESC, id_mouvement DESC) = 1
)
SELECT e.id_equipement, e.statut, d.dernier_mvt
FROM equipements e JOIN dernier d USING (id_equipement)
WHERE e.statut <> CASE d.dernier_mvt WHEN 'attribution' THEN 'attribué'
                                     WHEN 'mise au rebut' THEN 'réformé'
                                     ELSE 'en stock' END;

-- 4. Champs obligatoires manquants
CREATE OR REPLACE VIEW ctl_champs_manquants AS
SELECT id_equipement, statut, matricule, fin_garantie
FROM equipements
WHERE fin_garantie IS NULL OR (statut = 'attribué' AND matricule IS NULL);

-- 5. Synthèse pour le reporting
CREATE OR REPLACE VIEW synthese_controles AS
SELECT 'Doublons de n° de série' AS controle, count(*) AS nb_ecarts FROM ctl_doublons_serie
UNION ALL SELECT 'Attribué à un collaborateur parti', count(*) FROM ctl_attribue_parti
UNION ALL SELECT 'Statut ≠ dernier mouvement', count(*) FROM ctl_statut_incoherent
UNION ALL SELECT 'Champs obligatoires manquants', count(*) FROM ctl_champs_manquants;

-- 6. Parc à renouveler (hors garantie, toujours en service)
CREATE OR REPLACE VIEW a_renouveler AS
SELECT id_equipement, type, modele, site, date_achat, fin_garantie
FROM equipements
WHERE statut <> 'réformé' AND fin_garantie < DATE '2026-10-01';
