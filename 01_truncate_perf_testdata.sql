-- Seeding performance testdata (multi-tenant) - TRUNCATE préalable
-- Exécutez ceci UNIQUEMENT si vous voulez écraser les données de test.

-- ! Optionnel : décommentez et adaptez le nom de la base
-- USE `api_cantines`;

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE `stock_mouvementcaisse`;
TRUNCATE TABLE `stock_beneficelot`;
TRUNCATE TABLE `stock_lignesortielot`;
TRUNCATE TABLE `stock_lignesortie`;
TRUNCATE TABLE `stock_detteclient`;
TRUNCATE TABLE `stock_paiementdette`;
TRUNCATE TABLE `stock_sortie`;
TRUNCATE TABLE `stock_ligneentree`;
TRUNCATE TABLE `stock_entree`;
TRUNCATE TABLE `stock_stock`;
TRUNCATE TABLE `stock_client`;
TRUNCATE TABLE `stock_article`;
TRUNCATE TABLE `stock_soustypearticle`;
TRUNCATE TABLE `stock_typearticle`;
TRUNCATE TABLE `stock_unite`;
TRUNCATE TABLE `stock_devise`;
TRUNCATE TABLE `stock_succursale`;
TRUNCATE TABLE `stock_entreprise`;

TRUNCATE TABLE `users_userbranch`;
TRUNCATE TABLE `users_membership`;

-- Attention : users_user a aussi des tables M2M (groups/user_permissions).
-- On ne les touche pas ici : le seeding remplit uniquement users_user + FK métiers.
TRUNCATE TABLE `users_user`;

SET FOREIGN_KEY_CHECKS = 1;

