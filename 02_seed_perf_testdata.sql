-- Seeding performance testdata (multi-tenant) via procédure MySQL
-- Pré-requis : exécuter d'abord `01_truncate_perf_testdata.sql` si tu veux partir d'une base vide.
-- Adapter éventuellement : DB_NAME dans la ligne USE si besoin.
-- NOTE : ce script utilise des IDs déterministes pour pouvoir lier facilement les FK.

-- USE `DB_NAME`;

DELIMITER $$
DROP PROCEDURE IF EXISTS seed_perf_testdata$$
CREATE PROCEDURE seed_perf_testdata()
BEGIN
  DECLARE enterprises_count INT DEFAULT 6;
  DECLARE articles_per_ent INT DEFAULT 8;   -- => 48 articles au total
  DECLARE clients_per_ent INT DEFAULT 5;    -- => 30 clients au total
  DECLARE e INT DEFAULT 1;
  DECLARE a INT;
  DECLARE s INT;
  DECLARE has_branches INT;

  DECLARE now_dt DATETIME DEFAULT NOW();
  DECLARE today DATE DEFAULT CURDATE();

  -- Mot de passe hash Django (make_password('12345678'))
  DECLARE v_password_hash VARCHAR(200) DEFAULT 'pbkdf2_sha256$1000000$qCQP4t2k3xs4pewQN8bFiR$uoGwnEQvQBJz8+8v/fH3RUyJapQWZa5rjdvX339PizU=';

  -- Paramètres de prix (réalistes et déterministes)
  DECLARE g_article INT;
  DECLARE lot1_qty INT;
  DECLARE lot2_qty INT;
  DECLARE lot1_cost DECIMAL(10,2);
  DECLARE lot2_cost DECIMAL(10,2);
  DECLARE lot1_sale DECIMAL(10,2);
  DECLARE lot2_sale DECIMAL(10,2);
  DECLARE sortie_total1 DECIMAL(14,2);
  DECLARE sortie_total2 DECIMAL(14,2);
  DECLARE paiement_amount1 DECIMAL(14,2);
  DECLARE paiement_amount2 DECIMAL(14,2);

  -- IDs déterministes (formules)
  -- users: 1 superadmin, puis pour chaque entreprise :
  --   admin_user_id = 1000 + e*10 + 1
  --   agent_user_id = 1000 + e*10 + 2
  DECLARE superadmin_id BIGINT DEFAULT 1;

  WHILE e <= enterprises_count DO
    SET has_branches = IF(MOD(e, 2) = 0, 1, 0); -- alterne: certaines entreprises ont 2 succursales, d'autres non

    -- Entreprise
    INSERT INTO stock_entreprise
      (id, nom, secteur, pays, adresse, telephone, email, nif, responsable, logo, slogan, has_branches)
    VALUES
      (e,
       CONCAT('Entreprise ', e),
       'Agro',
       'FR',
       CONCAT('Adresse entreprise ', e),
       CONCAT('070000000', e),
       CONCAT('contact', e, '@example.com'),
       CONCAT('NIF', e),
       CONCAT('Resp ', e),
       NULL,
       CONCAT('Slogan ', e),
       has_branches);

    -- Succursales (si has_branches)
    IF has_branches = 1 THEN
      INSERT INTO stock_succursale (id, entreprise_id, nom, adresse, telephone, email, is_active, created_at)
      VALUES
        (e*100 + 1, e, CONCAT('Succursale ', e, ' - A'),
         CONCAT('Adresse succ ', e, 'A'), NULL, NULL, 1, now_dt),
        (e*100 + 2, e, CONCAT('Succursale ', e, ' - B'),
         CONCAT('Adresse succ ', e, 'B'), NULL, NULL, 1, now_dt);
    END IF;

    -- Devises (2 par entreprise)
    INSERT INTO stock_devise (id, sigle, nom, symbole, est_principal, entreprise_id)
    VALUES
      (e*10 + 1, CONCAT('DV', e, 'A'), CONCAT('Devise ', e, ' A'), CONCAT('S', e, 'A'), 1, e),
      (e*10 + 2, CONCAT('DV', e, 'B'), CONCAT('Devise ', e, ' B'), CONCAT('S', e, 'B'), 0, e);

    -- Unités (2 par entreprise)
    INSERT INTO stock_unite (id, libelle, description, entreprise_id, succursale_id)
    VALUES
      (e*1000 + 1, CONCAT('Unite ', e, ' - kg'), '', e, NULL),
      (e*1000 + 2, CONCAT('Unite ', e, ' - boite'), '', e, NULL);

    -- Types d'articles (2 par entreprise)
    INSERT INTO stock_typearticle (id, libelle, description, entreprise_id, succursale_id)
    VALUES
      (e*2000 + 1, CONCAT('Type ', e, ' - I'), '', e, NULL),
      (e*2000 + 2, CONCAT('Type ', e, ' - II'), '', e, NULL);

    -- Sous-types (4 par entreprise)
    INSERT INTO stock_soustypearticle (id, type_article_id, libelle, description, entreprise_id, succursale_id)
    VALUES
      (e*10000 + 1, e*2000 + 1, CONCAT('SousType ', e, ' - 1'), '', e, NULL),
      (e*10000 + 2, e*2000 + 1, CONCAT('SousType ', e, ' - 2'), '', e, NULL),
      (e*10000 + 3, e*2000 + 2, CONCAT('SousType ', e, ' - 3'), '', e, NULL),
      (e*10000 + 4, e*2000 + 2, CONCAT('SousType ', e, ' - 4'), '', e, NULL);

    -- Users + Memberships (superadmin global 1 seule fois, puis admin/agent par entreprise)
    IF e = 1 THEN
      -- SuperAdmin plateforme
      INSERT INTO users_user
        (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, role)
      VALUES
        (superadmin_id, v_password_hash, NULL, 1, 'superadmin', 'Super', 'Admin', 'superadmin@example.com', 1, 1, now_dt, 'superadmin');
    END IF;

    -- Admin de l'entreprise
    INSERT INTO users_user
      (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, role)
    VALUES
      (1000 + e*10 + 1, v_password_hash, NULL, 0,
       CONCAT('admin_ent_', e), CONCAT('Admin', e), 'Entreprise', CONCAT('admin', e, '@example.com'),
       0, 1, now_dt, 'admin');

    INSERT INTO users_membership
      (id, user_id, entreprise_id, role, is_active, created_at, default_succursale_id)
    VALUES
      (10000 + e*10 + 1, 1000 + e*10 + 1, e, 'admin', 1, now_dt, NULL);

    -- Agent de l'entreprise (uniquement si has_branches=1 pour éviter le cas “agent sans succursale” qui bloque les endpoints)
    IF has_branches = 1 THEN
      INSERT INTO users_user
        (id, password, last_login, is_superuser, username, first_name, last_name, email, is_staff, is_active, date_joined, role)
      VALUES
        (1000 + e*10 + 2, v_password_hash, NULL, 0,
         CONCAT('agent_ent_', e), CONCAT('Agent', e), 'Entreprise', CONCAT('agent', e, '@example.com'),
         0, 1, now_dt, 'admin');

      INSERT INTO users_membership
        (id, user_id, entreprise_id, role, is_active, created_at, default_succursale_id)
      VALUES
        (10000 + e*10 + 2, 1000 + e*10 + 2, e, 'user', 1, now_dt, e*100 + 1);

      -- Autoriser l'agent sur les 2 succursales
      INSERT INTO users_userbranch (id, is_active, created_at, membership_id, succursale_id)
      VALUES
        (20000 + e*100 + 1, 1, now_dt, 10000 + e*10 + 2, e*100 + 1),
        (20000 + e*100 + 2, 1, now_dt, 10000 + e*10 + 2, e*100 + 2);
    END IF;

    -- Clients (utilisés pour créer les sorties / dettes)
    SET a = 1;
    WHILE a <= clients_per_ent DO
      INSERT INTO stock_client
        (id, nom, telephone, adresse, email, date_enregistrement, entreprise_id, succursale_id)
      VALUES
        (CONCAT('C', e, LPAD(a,3,'0')),
         CONCAT('Client ', e, '-', a),
         NULL,
         CONCAT('Adresse client ', e, '-', a),
         CONCAT('client', e, '_', a, '@example.com'),
         now_dt,
         e,
         IF(has_branches = 1,
            IF(MOD(a,2)=1, e*100 + 1, e*100 + 2),
            NULL));
      SET a = a + 1;
    END WHILE;

    -- Articles + Stock + Entrees/Lignes + Sorties/Lignes/FIFO + Dettes/Paiements/Mouvements
    SET a = 1;
    WHILE a <= articles_per_ent DO
      SET g_article = (e-1)*articles_per_ent + a; -- index global 1..(enterprises*articles)

      -- Article succursale: seulement si l'entreprise a des branches (sinon NULL)
      -- Succursale A si a impair, B si a pair
      INSERT INTO stock_article
        (article_id, nom_scientifique, nom_commercial, sous_type_article_id, unite_id, emplacement, entreprise_id, succursale_id)
      VALUES
        (CONCAT('A', e, LPAD(a,3,'0')),
         CONCAT('Article sci e', e, ' a', a),
         NULL,
         (e*10000 + MOD(a-1,4) + 1),
         (e*1000 + MOD(a-1,2) + 1),
         '1',
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      -- Stock initial (on consommera ensuite pour ramener à 0)
      INSERT INTO stock_stock (article_id, Qte, seuilAlert)
      VALUES
        (CONCAT('A', e, LPAD(a,3,'0')),
         0,
         5);

      -- Calcul de quantités + prix déterministes
      SET lot1_qty = 20 + MOD(g_article, 6) * 5;         -- ex: 20..45
      SET lot2_qty = 15 + MOD(g_article + 1, 5) * 4;     -- ex: 15..31
      SET lot1_cost = ROUND(10.00 + g_article * 0.75, 2); -- ex: ~10..46
      SET lot2_cost = ROUND(lot1_cost + 3.50, 2);
      SET lot1_sale = ROUND(lot1_cost * 1.80, 2);
      SET lot2_sale = ROUND(lot2_cost * 1.80, 2);

      -- --- Lot ENTREE #1 ---
      INSERT INTO stock_entree
        (id, libele, description, date_op, entreprise_id, succursale_id)
      VALUES
        (e*100000 + a*10 + 1,
         CONCAT('Entree e', e, ' a', a, ' lot1'),
         '',
         now_dt,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      INSERT INTO stock_ligneentree
        (id, article_id, quantite, quantite_restante, prix_unitaire, prix_vente, date_expiration, date_entree, seuil_alerte, entree_id, devise_id)
      VALUES
        (e*100000 + a*10 + 11,
         CONCAT('A', e, LPAD(a,3,'0')),
         lot1_qty,
         lot1_qty,
         lot1_cost,
         lot1_sale,
         NULL,
         now_dt,
         5,
         e*100000 + a*10 + 1,
         e*10 + 1);

      -- --- Lot ENTREE #2 ---
      INSERT INTO stock_entree
        (id, libele, description, date_op, entreprise_id, succursale_id)
      VALUES
        (e*100000 + a*10 + 2,
         CONCAT('Entree e', e, ' a', a, ' lot2'),
         '',
         now_dt,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      INSERT INTO stock_ligneentree
        (id, article_id, quantite, quantite_restante, prix_unitaire, prix_vente, date_expiration, date_entree, seuil_alerte, entree_id, devise_id)
      VALUES
        (e*100000 + a*10 + 12,
         CONCAT('A', e, LPAD(a,3,'0')),
         lot2_qty,
         lot2_qty,
         lot2_cost,
         lot2_sale,
         NULL,
         now_dt,
         5,
         e*100000 + a*10 + 2,
         e*10 + 1);

      -- Stock = somme des lots
      UPDATE stock_stock
      SET Qte = lot1_qty + lot2_qty
      WHERE article_id = CONCAT('A', e, LPAD(a,3,'0'));

      -- Succursale du contexte (si branches)
      -- Utilisée pour les dettes/paiements/mouvements

      -- --- Sortie #1 (consomme lot1) ---
      SET s = 1;
      SET sortie_total1 = ROUND(lot1_qty * lot1_sale, 2);
      SET paiement_amount1 = ROUND(sortie_total1 * 0.40, 2);

      INSERT INTO stock_sortie
        (id, motif, client_id, devise_id, statut, date_creation, entreprise_id, succursale_id)
      VALUES
        (e*100000 + a*10 + 21,
         CONCAT('Vente e', e, ' a', a, ' lot1'),
         CONCAT('C', e, LPAD((MOD((a-1)*2 + 1, clients_per_ent) + 1),3,'0')),
         e*10 + 1,
         'EN_CREDIT',
         now_dt,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      INSERT INTO stock_lignesortie
        (id, sortie_id, article_id, quantite, prix_unitaire, date_sortie, devise_id)
      VALUES
        (e*100000 + a*10 + 31,
         e*100000 + a*10 + 21,
         CONCAT('A', e, LPAD(a,3,'0')),
         lot1_qty,
         lot1_sale,
         now_dt,
         e*10 + 1);

      -- FIFO: lot de la sortie = ligneentree lot1
      INSERT INTO stock_lignesortielot
        (id, ligne_sortie_id, lot_entree_id, quantite, prix_achat, prix_vente)
      VALUES
        (e*100000 + a*10 + 41,
         e*100000 + a*10 + 31,
         e*100000 + a*10 + 11,
         lot1_qty,
         lot1_cost,
         lot1_sale);

      INSERT INTO stock_beneficelot
        (id, lot_entree_id, ligne_sortie_id, quantite_vendue, prix_achat, prix_vente, benefice_unitaire, benefice_total, date_calcul)
      VALUES
        (e*100000 + a*10 + 51,
         e*100000 + a*10 + 11,
         e*100000 + a*10 + 31,
         lot1_qty,
         lot1_cost,
         lot1_sale,
         ROUND(lot1_sale - lot1_cost, 2),
         ROUND((lot1_sale - lot1_cost) * lot1_qty, 2),
         now_dt);

      -- Mettre le lot consommé à 0 (FIFO simplifié: lot consommé intégralement)
      UPDATE stock_ligneentree
      SET quantite_restante = 0
      WHERE id = e*100000 + a*10 + 11;

      -- --- Sortie #2 (consomme lot2) ---
      SET s = 2;
      SET sortie_total2 = ROUND(lot2_qty * lot2_sale, 2);
      SET paiement_amount2 = ROUND(sortie_total2 * 0.40, 2);

      INSERT INTO stock_sortie
        (id, motif, client_id, devise_id, statut, date_creation, entreprise_id, succursale_id)
      VALUES
        (e*100000 + a*10 + 22,
         CONCAT('Vente e', e, ' a', a, ' lot2'),
         CONCAT('C', e, LPAD((MOD((a-1)*2 + 2, clients_per_ent) + 1),3,'0')),
         e*10 + 1,
         'EN_CREDIT',
         now_dt,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      INSERT INTO stock_lignesortie
        (id, sortie_id, article_id, quantite, prix_unitaire, date_sortie, devise_id)
      VALUES
        (e*100000 + a*10 + 32,
         e*100000 + a*10 + 22,
         CONCAT('A', e, LPAD(a,3,'0')),
         lot2_qty,
         lot2_sale,
         now_dt,
         e*10 + 1);

      INSERT INTO stock_lignesortielot
        (id, ligne_sortie_id, lot_entree_id, quantite, prix_achat, prix_vente)
      VALUES
        (e*100000 + a*10 + 42,
         e*100000 + a*10 + 32,
         e*100000 + a*10 + 12,
         lot2_qty,
         lot2_cost,
         lot2_sale);

      INSERT INTO stock_beneficelot
        (id, lot_entree_id, ligne_sortie_id, quantite_vendue, prix_achat, prix_vente, benefice_unitaire, benefice_total, date_calcul)
      VALUES
        (e*100000 + a*10 + 52,
         e*100000 + a*10 + 12,
         e*100000 + a*10 + 32,
         lot2_qty,
         lot2_cost,
         lot2_sale,
         ROUND(lot2_sale - lot2_cost, 2),
         ROUND((lot2_sale - lot2_cost) * lot2_qty, 2),
         now_dt);

      UPDATE stock_ligneentree
      SET quantite_restante = 0
      WHERE id = e*100000 + a*10 + 12;

      -- Stock après 2 sorties
      UPDATE stock_stock
      SET Qte = 0
      WHERE article_id = CONCAT('A', e, LPAD(a,3,'0'));

      -- --- Dette + Paiement + Mouvement caisse pour chaque sortie ---
      -- Dette #1 (pour sortie lot1)
      INSERT INTO stock_detteclient
        (id, client_id, sortie_id, montant_total, montant_paye, solde_restant, devise_id, date_creation, date_echeance, statut, commentaire, entreprise_id, succursale_id)
      VALUES
        (e*10000000 + a*100 + 1,
         CONCAT('C', e, LPAD((MOD((a-1)*2 + 1, clients_per_ent) + 1),3,'0')),
         e*100000 + a*10 + 21,
         sortie_total1,
         paiement_amount1,
         ROUND(sortie_total1 - paiement_amount1, 2),
         e*10 + 1,
         now_dt,
         DATE_ADD(today, INTERVAL 30 DAY),
         IF(ROUND(sortie_total1 - paiement_amount1, 2) <= 0, 'PAYEE', 'EN_COURS'),
         NULL,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      INSERT INTO stock_paiementdette
        (id, dette_id, montant_paye, date_paiement, moyen, reference, utilisateur_id, devise_id, entreprise_id, succursale_id)
      VALUES
        (e*10000000 + a*100 + 11,
         e*10000000 + a*100 + 1,
         paiement_amount1,
         now_dt,
         'Cash',
         CONCAT('PAY-', e, '-', a, '-1'),
         IF(has_branches = 1, (1000 + e*10 + 2), (1000 + e*10 + 1)),
         e*10 + 1,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      INSERT INTO stock_mouvementcaisse
        (id, date, montant, devise_id, `type`, motif, moyen, reference_piece, sortie_id, entree_id, entreprise_id, succursale_id)
      VALUES
        (e*10000000 + a*100 + 21,
         now_dt,
         paiement_amount1,
         e*10 + 1,
         'ENTREE',
         CONCAT('Paiement dette client (sortie lot1) - e', e, ' a', a),
         'Cash',
         CONCAT('DET-', e*10000000 + a*100 + 1),
         NULL,
         NULL,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      -- Dette #2 (pour sortie lot2)
      INSERT INTO stock_detteclient
        (id, client_id, sortie_id, montant_total, montant_paye, solde_restant, devise_id, date_creation, date_echeance, statut, commentaire, entreprise_id, succursale_id)
      VALUES
        (e*10000000 + a*100 + 2,
         CONCAT('C', e, LPAD((MOD((a-1)*2 + 2, clients_per_ent) + 1),3,'0')),
         e*100000 + a*10 + 22,
         sortie_total2,
         paiement_amount2,
         ROUND(sortie_total2 - paiement_amount2, 2),
         e*10 + 1,
         now_dt,
         DATE_ADD(today, INTERVAL 30 DAY),
         IF(ROUND(sortie_total2 - paiement_amount2, 2) <= 0, 'PAYEE', 'EN_COURS'),
         NULL,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      INSERT INTO stock_paiementdette
        (id, dette_id, montant_paye, date_paiement, moyen, reference, utilisateur_id, devise_id, entreprise_id, succursale_id)
      VALUES
        (e*10000000 + a*100 + 12,
         e*10000000 + a*100 + 2,
         paiement_amount2,
         now_dt,
         'Cash',
         CONCAT('PAY-', e, '-', a, '-2'),
         IF(has_branches = 1, (1000 + e*10 + 2), (1000 + e*10 + 1)),
         e*10 + 1,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      INSERT INTO stock_mouvementcaisse
        (id, date, montant, devise_id, `type`, motif, moyen, reference_piece, sortie_id, entree_id, entreprise_id, succursale_id)
      VALUES
        (e*10000000 + a*100 + 22,
         now_dt,
         paiement_amount2,
         e*10 + 1,
         'ENTREE',
         CONCAT('Paiement dette client (sortie lot2) - e', e, ' a', a),
         'Cash',
         CONCAT('DET-', e*10000000 + a*100 + 2),
         NULL,
         NULL,
         e,
         IF(has_branches = 1, IF(MOD(a,2)=1, e*100 + 1, e*100 + 2), NULL));

      SET a = a + 1;
    END WHILE;

    SET e = e + 1;
  END WHILE;
END$$
DELIMITER ;

-- Exécution
CALL seed_perf_testdata();

