-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
--
-- Host: localhost    Database: db_cantine
-- ------------------------------------------------------
-- Server version	8.0.45

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=101 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add Outstanding Token',6,'add_outstandingtoken'),(22,'Can change Outstanding Token',6,'change_outstandingtoken'),(23,'Can delete Outstanding Token',6,'delete_outstandingtoken'),(24,'Can view Outstanding Token',6,'view_outstandingtoken'),(25,'Can add Blacklisted Token',7,'add_blacklistedtoken'),(26,'Can change Blacklisted Token',7,'change_blacklistedtoken'),(27,'Can delete Blacklisted Token',7,'delete_blacklistedtoken'),(28,'Can view Blacklisted Token',7,'view_blacklistedtoken'),(29,'Can add user',8,'add_user'),(30,'Can change user',8,'change_user'),(31,'Can delete user',8,'delete_user'),(32,'Can view user',8,'view_user'),(33,'Can add entreprise',9,'add_entreprise'),(34,'Can change entreprise',9,'change_entreprise'),(35,'Can delete entreprise',9,'delete_entreprise'),(36,'Can view entreprise',9,'view_entreprise'),(37,'Can add unite',10,'add_unite'),(38,'Can change unite',10,'change_unite'),(39,'Can delete unite',10,'delete_unite'),(40,'Can view unite',10,'view_unite'),(41,'Can add type article',11,'add_typearticle'),(42,'Can change type article',11,'change_typearticle'),(43,'Can delete type article',11,'delete_typearticle'),(44,'Can view type article',11,'view_typearticle'),(45,'Can add sous type article',12,'add_soustypearticle'),(46,'Can change sous type article',12,'change_soustypearticle'),(47,'Can delete sous type article',12,'delete_soustypearticle'),(48,'Can view sous type article',12,'view_soustypearticle'),(49,'Can add article',13,'add_article'),(50,'Can change article',13,'change_article'),(51,'Can delete article',13,'delete_article'),(52,'Can view article',13,'view_article'),(53,'Can add entree',14,'add_entree'),(54,'Can change entree',14,'change_entree'),(55,'Can delete entree',14,'delete_entree'),(56,'Can view entree',14,'view_entree'),(57,'Can add ligne entree',15,'add_ligneentree'),(58,'Can change ligne entree',15,'change_ligneentree'),(59,'Can delete ligne entree',15,'delete_ligneentree'),(60,'Can view ligne entree',15,'view_ligneentree'),(61,'Can add stock',16,'add_stock'),(62,'Can change stock',16,'change_stock'),(63,'Can delete stock',16,'delete_stock'),(64,'Can view stock',16,'view_stock'),(65,'Can add sortie',17,'add_sortie'),(66,'Can change sortie',17,'change_sortie'),(67,'Can delete sortie',17,'delete_sortie'),(68,'Can view sortie',17,'view_sortie'),(69,'Can add client',18,'add_client'),(70,'Can change client',18,'change_client'),(71,'Can delete client',18,'delete_client'),(72,'Can view client',18,'view_client'),(73,'Can add Dette client',19,'add_detteclient'),(74,'Can change Dette client',19,'change_detteclient'),(75,'Can delete Dette client',19,'delete_detteclient'),(76,'Can view Dette client',19,'view_detteclient'),(77,'Can add Paiement de dette',20,'add_paiementdette'),(78,'Can change Paiement de dette',20,'change_paiementdette'),(79,'Can delete Paiement de dette',20,'delete_paiementdette'),(80,'Can view Paiement de dette',20,'view_paiementdette'),(81,'Can add ligne sortie',21,'add_lignesortie'),(82,'Can change ligne sortie',21,'change_lignesortie'),(83,'Can delete ligne sortie',21,'delete_lignesortie'),(84,'Can view ligne sortie',21,'view_lignesortie'),(85,'Can add Lot utilisé dans sortie',22,'add_lignesortielot'),(86,'Can change Lot utilisé dans sortie',22,'change_lignesortielot'),(87,'Can delete Lot utilisé dans sortie',22,'delete_lignesortielot'),(88,'Can view Lot utilisé dans sortie',22,'view_lignesortielot'),(89,'Can add Bénéfice par lot',23,'add_beneficelot'),(90,'Can change Bénéfice par lot',23,'change_beneficelot'),(91,'Can delete Bénéfice par lot',23,'delete_beneficelot'),(92,'Can view Bénéfice par lot',23,'view_beneficelot'),(93,'Can add mouvement caisse',24,'add_mouvementcaisse'),(94,'Can change mouvement caisse',24,'change_mouvementcaisse'),(95,'Can delete mouvement caisse',24,'delete_mouvementcaisse'),(96,'Can view mouvement caisse',24,'view_mouvementcaisse'),(97,'Can add Devise',25,'add_devise'),(98,'Can change Devise',25,'change_devise'),(99,'Can delete Devise',25,'delete_devise'),(100,'Can view Devise',25,'view_devise');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_users_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_users_user_id` FOREIGN KEY (`user_id`) REFERENCES `users_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=26 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(3,'auth','group'),(2,'auth','permission'),(4,'contenttypes','contenttype'),(5,'sessions','session'),(13,'stock','article'),(23,'stock','beneficelot'),(18,'stock','client'),(19,'stock','detteclient'),(25,'stock','devise'),(14,'stock','entree'),(9,'stock','entreprise'),(15,'stock','ligneentree'),(21,'stock','lignesortie'),(22,'stock','lignesortielot'),(24,'stock','mouvementcaisse'),(20,'stock','paiementdette'),(17,'stock','sortie'),(12,'stock','soustypearticle'),(16,'stock','stock'),(11,'stock','typearticle'),(10,'stock','unite'),(7,'token_blacklist','blacklistedtoken'),(6,'token_blacklist','outstandingtoken'),(8,'users','user');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=47 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'stock','0001_initial','2026-01-31 22:26:25.501605'),(2,'contenttypes','0001_initial','2026-01-31 22:26:26.782800'),(3,'contenttypes','0002_remove_content_type_name','2026-01-31 22:26:29.099394'),(4,'auth','0001_initial','2026-01-31 22:26:36.102186'),(5,'auth','0002_alter_permission_name_max_length','2026-01-31 22:26:38.236847'),(6,'auth','0003_alter_user_email_max_length','2026-01-31 22:26:38.337986'),(7,'auth','0004_alter_user_username_opts','2026-01-31 22:26:38.428266'),(8,'auth','0005_alter_user_last_login_null','2026-01-31 22:26:38.588815'),(9,'auth','0006_require_contenttypes_0002','2026-01-31 22:26:38.767516'),(10,'auth','0007_alter_validators_add_error_messages','2026-01-31 22:26:39.078581'),(11,'auth','0008_alter_user_username_max_length','2026-01-31 22:26:39.352686'),(12,'auth','0009_alter_user_last_name_max_length','2026-01-31 22:26:39.452222'),(13,'auth','0010_alter_group_name_max_length','2026-01-31 22:26:39.833828'),(14,'auth','0011_update_proxy_permissions','2026-01-31 22:26:40.045115'),(15,'auth','0012_alter_user_first_name_max_length','2026-01-31 22:26:40.163911'),(16,'users','0001_initial','2026-01-31 22:26:54.003382'),(17,'admin','0001_initial','2026-01-31 22:26:57.982904'),(18,'admin','0002_logentry_remove_auto_add','2026-01-31 22:26:58.074386'),(19,'admin','0003_logentry_add_action_flag_choices','2026-01-31 22:26:58.247627'),(20,'sessions','0001_initial','2026-01-31 22:26:59.957147'),(21,'stock','0002_initial','2026-01-31 22:27:48.310411'),(22,'stock','0003_prixventearticle','2026-01-31 22:27:52.281099'),(23,'stock','0004_rename_nom_article_nom_scientifique_and_more','2026-01-31 22:27:54.604358'),(24,'stock','0005_client_detteclient_sortie_statut_paiementdette_and_more','2026-01-31 22:28:18.369321'),(25,'stock','0006_paiementdette_reference_paiementdette_utilisateur','2026-01-31 22:28:21.908783'),(26,'stock','0007_alter_client_unique_together_alter_client_id_and_more','2026-01-31 22:28:32.856159'),(27,'stock','0008_delete_tauxechange','2026-01-31 22:28:33.573622'),(28,'stock','0009_remove_article_entreprise_remove_client_entreprise_and_more','2026-01-31 22:29:09.988983'),(29,'stock','0010_alter_entreprise_email','2026-01-31 22:29:12.664586'),(30,'stock','0011_alter_entreprise_options','2026-01-31 22:29:12.748283'),(31,'stock','0012_alter_entreprise_options','2026-01-31 22:29:12.857805'),(32,'token_blacklist','0001_initial','2026-01-31 22:29:18.476078'),(33,'token_blacklist','0002_outstandingtoken_jti_hex','2026-01-31 22:29:19.972468'),(34,'token_blacklist','0003_auto_20171017_2007','2026-01-31 22:29:20.139780'),(35,'token_blacklist','0004_auto_20171017_2013','2026-01-31 22:29:21.921454'),(36,'token_blacklist','0005_remove_outstandingtoken_jti','2026-01-31 22:29:23.191626'),(37,'token_blacklist','0006_auto_20171017_2113','2026-01-31 22:29:23.689513'),(38,'token_blacklist','0007_auto_20171017_2214','2026-01-31 22:29:28.942223'),(39,'token_blacklist','0008_migrate_to_bigautofield','2026-01-31 22:29:38.938078'),(40,'token_blacklist','0010_fix_migrate_to_bigautofield','2026-01-31 22:29:39.083606'),(41,'token_blacklist','0011_linearizes_history','2026-01-31 22:29:39.166374'),(42,'token_blacklist','0012_alter_outstandingtoken_user','2026-01-31 22:29:39.350094'),(43,'token_blacklist','0013_alter_blacklistedtoken_options_and_more','2026-01-31 22:29:39.507069'),(44,'stock','0010_beneficelot_lignesortielot_alter_ligneentree_options_and_more','2026-02-01 14:12:16.797117'),(45,'stock','0011_add_client_to_sortie','2026-02-01 14:12:20.393515'),(46,'stock','0012_delete_prixventearticle','2026-02-04 17:25:41.736933');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_article`
--

DROP TABLE IF EXISTS `stock_article`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_article` (
  `nom_scientifique` varchar(100) NOT NULL,
  `article_id` varchar(10) NOT NULL,
  `sous_type_article_id` bigint NOT NULL,
  `unite_id` bigint NOT NULL,
  `nom_commercial` varchar(100) DEFAULT NULL,
  `emplacement` varchar(200) NOT NULL,
  PRIMARY KEY (`article_id`),
  KEY `stock_article_sous_type_article_id_d6c5b908_fk_stock_sou` (`sous_type_article_id`),
  KEY `stock_article_unite_id_d69fcfbd_fk_stock_unite_id` (`unite_id`),
  CONSTRAINT `stock_article_sous_type_article_id_d6c5b908_fk_stock_sou` FOREIGN KEY (`sous_type_article_id`) REFERENCES `stock_soustypearticle` (`id`),
  CONSTRAINT `stock_article_unite_id_d69fcfbd_fk_stock_unite_id` FOREIGN KEY (`unite_id`) REFERENCES `stock_unite` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_article`
--

LOCK TABLES `stock_article` WRITE;
/*!40000 ALTER TABLE `stock_article` DISABLE KEYS */;
INSERT INTO `stock_article` VALUES ('Attache habit','ARDI0001',33,1,NULL,'1'),('autocolant','ARDI0002',33,1,NULL,'1'),('sac cavera','ARDI0003',33,1,NULL,'1'),('sac vide GF','ARDI0004',33,1,NULL,'1'),('sachet noir','ARDI0005',33,1,NULL,'1'),('sachet vert','ARDI0006',33,1,NULL,'1'),('Fil à boule','ARDI0007',33,1,NULL,'1'),('Fil à coudre','ARDI0008',33,1,NULL,'1'),('boule odorant','ARDI0009',33,1,NULL,'1'),('silver line GF','ARDI0010',33,1,NULL,'1'),('silver line PF','ARDI0011',33,1,NULL,'1'),('tige coton','ARDI0012',33,1,NULL,'1'),('thermos 3,5l','ARDI0013',33,1,NULL,'1'),('Pelouse synthétique','ARDI0014',33,1,NULL,'1'),('Agraphe kangaro 24/6','FOAG0001',6,1,NULL,'1'),('Agrapheuse métallique','FOAG0002',6,1,NULL,'1'),('Colle élephant','FOAG0003',6,1,NULL,'1'),('Super gloue','FOAG0004',6,1,NULL,'1'),('scotch pf','FOAG0005',6,1,NULL,'1'),('Agenda GF','FOCA0001',1,1,NULL,'1'),('Agenda PF','FOCA0002',1,1,NULL,'1'),('Cahier dessin','FOCA0003',1,1,NULL,'1'),('Cahier ministre GF','FOCA0004',1,1,NULL,'1'),('Cahier ministre PF','FOCA0005',1,1,NULL,'1'),('cahier simple calcul','FOCA0006',1,1,NULL,'1'),('petit cahier ligné calli','FOCA0007',1,1,NULL,'1'),('brouillons ligne','FOCA0008',1,1,NULL,'1'),('brouillons quadrillé','FOCA0009',1,1,NULL,'1'),('demi brouillons ligne','FOCA0010',1,1,NULL,'1'),('demi brouillons quadrillé','FOCA0011',1,1,NULL,'1'),('Journal de classe','FOCA0012',1,1,NULL,'1'),('Note book','FOCA0013',1,1,NULL,'1'),('Papier bristol A1','FOCA0014',1,1,NULL,'1'),('papier bristol A4','FOCA0015',1,1,NULL,'1'),('Papier carbone','FOCA0016',1,1,NULL,'1'),('Papier maquette','FOCA0017',1,1,NULL,'1'),('Papier milimetré A3','FOCA0018',1,1,NULL,'1'),('Papier milimetré A4','FOCA0019',1,1,NULL,'1'),('Papier vitré','FOCA0020',1,1,NULL,'1'),('papier rame','FOCA0021',1,1,NULL,'1'),('Tableau periodique','FOCA0022',1,1,NULL,'1'),('classeurs','FOCA0023',1,1,NULL,'1'),('Farde en plastique','FOCA0024',1,1,NULL,'1'),('Perforateur','FOCA0025',1,1,NULL,'1'),('Post it','FOCA0026',1,1,NULL,'1'),('Enveloppe ordinaire','FOCA0027',1,1,NULL,'1'),('Enveloppe chequier','FOCA0028',1,1,NULL,'1'),('Envellope sac A3','FOCA0029',1,1,NULL,'1'),('Enveloppe sac A4','FOCA0030',1,1,NULL,'1'),('emballage cadeau simple','FOCA0031',1,1,NULL,'1'),('emballage cadeau sac','FOCA0032',1,1,NULL,'1'),('Ciseau','FODÉ0001',7,1,NULL,'1'),('Couteau maquette GF','FODÉ0002',7,1,NULL,'1'),('Couteau maquette PF','FODÉ0003',7,1,NULL,'1'),('Stylot bleu','FOST0001',2,1,NULL,'1'),('stylot noir','FOST0002',2,1,NULL,'1'),('Stylot rouge','FOST0003',2,1,NULL,'1'),('Crayon','FOST0004',2,1,NULL,'1'),('Porte mine','FOST0005',2,1,NULL,'1'),('Mine','FOST0006',2,1,NULL,'1'),('Souligneur','FOST0007',2,1,NULL,'1'),('Bic marqueur simple','FOST0008',2,1,NULL,'1'),('Marqueur a tableau blanc','FOST0009',2,1,NULL,'1'),('chaussete longue','HACH0001',26,1,NULL,'1'),('chaussette perpette','HACH0002',26,1,NULL,'1'),('chaussette versace','HACH0003',26,1,NULL,'1'),('cycliste femme court','HACH0004',26,1,NULL,'1'),('culotte homme','HASO0001',25,1,NULL,'1'),('sous vetem homme','HASO0002',25,1,NULL,'1'),('sous vetem enfant mixt','HASO0003',25,1,NULL,'1'),('sous vetem jeune gar','HASO0004',25,1,NULL,'1'),('sous vetem sexy vilya','HASO0005',25,1,NULL,'1'),('sous vetem de lux','HASO0006',25,1,NULL,'1'),('singlet hommes','HASO0007',25,1,NULL,'1'),('singlet femme de lux','HASO0008',25,1,NULL,'1'),('singlet damme fammy','HASO0009',25,1,NULL,'1'),('singlet junior','HASO0010',25,1,NULL,'1'),('soutien gorge simple','HASO0011',25,1,NULL,'1'),('soutien gorge de lux','HASO0012',25,1,NULL,'1'),('biscuit bora','PRBI0001',10,1,NULL,'1'),('biscuit choco','PRBI0002',10,1,NULL,'1'),('biscuit choco GF','PRBI0003',10,1,NULL,'1'),('BIScuit cremica','PRBI0004',10,1,NULL,'1'),('Biscuit Max','PRBI0005',10,1,NULL,'1'),('Biscuit milk plus','PRBI0006',10,1,NULL,'1'),('biscuit soja','PRBI0007',10,1,NULL,'1'),('big boss','PRBI0008',10,1,NULL,'1'),('bonbon hewa','PRBI0009',10,1,NULL,'1'),('bonbon ordinaire','PRBI0010',10,1,NULL,'1'),('Eau tamu 330ml','PRBO0001',12,7,NULL,'1'),('Eau tamu 550ml','PRBO0002',12,7,NULL,'1'),('Eau tamu 1l','PRBO0003',12,7,NULL,'1'),('Eau tamu 1,5l','PRBO0004',12,7,NULL,'1'),('jus afia','PRBO0005',12,7,NULL,'1'),('jus Embe','PRBO0006',12,7,NULL,'1'),('jus Mango','PRBO0007',12,7,NULL,'1'),('Jus naturel','PRBO0008',12,7,NULL,'1'),('jus fanta 330ml','PRBO0009',12,7,NULL,'1'),('Mirinda 2l','PRBO0010',12,7,NULL,'1'),('PAPIER HYGENIQUE','PRCO0001',16,1,NULL,'1'),('papier mouchoir','PRCO0002',16,1,NULL,'1'),('PAPIER SERVIETTE','PRCO0003',16,1,NULL,'1'),('Bougie à gateau','PRCO0004',16,1,NULL,'1'),('Allumettes GF','PRCO0005',16,1,NULL,'1'),('allumettes Petit format','PRCO0006',16,1,NULL,'1'),('creme boudchou gf','PRCR0001',19,2,NULL,'1'),('creme day by day 100ml','PRCR0002',19,2,NULL,'1'),('creme day by day 400ml','PRCR0003',19,2,NULL,'1'),('creme nevia 70g','PRCR0004',19,2,NULL,'1'),('lotion Amara','PRCR0005',19,2,NULL,'1'),('lotion rapide claire','PRCR0006',19,2,NULL,'1'),('lotion Revlon','PRCR0007',19,2,NULL,'1'),('lotion skala','PRCR0008',19,2,NULL,'1'),('lotion vestline aloe','PRCR0009',19,2,NULL,'1'),('pomade afro care 100g','PRCR0010',19,2,NULL,'1'),('pomade afro extra','PRCR0011',19,2,NULL,'1'),('pomade boudchou pf','PRCR0012',19,2,NULL,'1'),('pomade movit 20g','PRCR0013',19,2,NULL,'1'),('pomade movit 70g','PRCR0014',19,2,NULL,'1'),('pomade movit 200g','PRCR0015',19,2,NULL,'1'),('pomade radia','PRCR0016',19,2,NULL,'1'),('pomade skala 100g','PRCR0017',19,2,NULL,'1'),('pomade top line','PRCR0018',19,2,NULL,'1'),('pomade UB','PRCR0019',19,2,NULL,'1'),('pomade vaseline blue GF','PRCR0020',19,2,NULL,'1'),('pomade vestline garlic 25g','PRCR0021',19,2,NULL,'1'),('pomade vest herbal 25g','PRCR0022',19,2,NULL,'1'),('pressol gel 80g','PRCR0023',19,2,NULL,'1'),('pressol gel 125g','PRCR0024',19,2,NULL,'1'),('movit gel','PRCR0025',19,2,NULL,'1'),('Dentifrice aloe','PRDE0001',18,2,NULL,'1'),('Dentifrice colgate','PRDE0002',18,2,NULL,'1'),('Dentifrice Flodent','PRDE0003',18,2,NULL,'1'),('Dentifrice fresh up','PRDE0004',18,2,NULL,'1'),('Brosse a dent','PRDE0005',18,2,NULL,'1'),('cure dent','PRDE0006',18,2,NULL,'1'),('Chargeur 2.5A','PREN0001',31,1,NULL,'1'),('ecouteur','PREN0002',31,1,NULL,'1'),('Ralonge','PREN0003',31,1,NULL,'1'),('isolant','PREN0004',31,1,NULL,'1'),('glycerine carote','PRGL0001',21,7,NULL,'1'),('glycerine criss','PRGL0002',21,7,NULL,'1'),('glycerine eft et adultes','PRGL0003',21,7,NULL,'1'),('glycerine medical','PRGL0004',21,7,NULL,'1'),('glycerine Pop GF','PRGL0005',21,7,NULL,'1'),('glycerine Pop PF','PRGL0006',21,7,NULL,'1'),('Flash disk 8GB','PRLI0001',29,1,NULL,'1'),('Flash disk 16GB','PRLI0002',29,1,NULL,'1'),('Flash disk 32GB','PRLI0003',29,1,NULL,'1'),('carte mémoire 1GB','PRLI0004',29,1,NULL,'1'),('carte mémoire 4GB','PRLI0005',29,1,NULL,'1'),('carte mémoire 8GB','PRLI0006',29,1,NULL,'1'),('100 jour spirituel','PRLI0007',29,1,NULL,'1'),('levure','PRMA0001',13,7,NULL,'1'),('vanila liquide','PRMA0002',13,7,NULL,'1'),('Colorant gateau','PRMA0003',13,2,NULL,'1'),('Icing sugar','PRMA0004',13,2,NULL,'1'),('Mayonnaise GF','PRMA0005',13,2,NULL,'1'),('Mayonnaise PF','PRMA0006',13,2,NULL,'1'),('Vim','PRNE0001',15,1,NULL,'1'),('Omo ross 5kg','PRNE0002',15,1,NULL,'1'),('Insecticide','PRNE0003',15,1,NULL,'1'),('brosse a WC','PRNE0004',15,1,NULL,'1'),('brosse de cuisine','PRNE0005',15,1,NULL,'1'),('sceau plastique','PRNE0006',15,1,NULL,'1'),('parfum feeling','PRPA0001',22,7,NULL,'1'),('parfum for men','PRPA0002',22,7,NULL,'1'),('poudre 22 degré','PRPA0003',22,7,NULL,'1'),('poudre passion PF','PRPA0004',22,7,NULL,'1'),('9.3 Piles','PRPI0001',32,1,NULL,'1'),('Pile GF electra','PRPI0002',32,1,NULL,'1'),('pile tiger pt format','PRPI0003',32,1,NULL,'1'),('Pile touche toceball','PRPI0004',32,1,NULL,'1'),('Pile vinic','PRPI0005',32,1,NULL,'1'),('Riz','PRPR0001',8,2,NULL,'1'),('MACCARORI','PRPR0002',8,2,NULL,'1'),('Spaguetti','PRPR0003',8,2,NULL,'1'),('Farine kaunga','PRPR0004',8,2,NULL,'1'),('farine de froment azam','PRPR0005',8,2,NULL,'1'),('sucre','PRPR0006',8,2,NULL,'1'),('sel ordinaire','PRPR0007',8,2,NULL,'1'),('sel medical','PRPR0008',8,2,NULL,'1'),('Oeuf','PRRO0001',9,12,NULL,'1'),('Poisson','PRRO0002',9,2,NULL,'1'),('tomates salsa','PRRO0003',9,2,NULL,'1'),('arachide','PRRO0004',9,2,NULL,'1'),('savon Cynthol GF','PRSA0001',17,1,NULL,'1'),('savon Cynthol PF','PRSA0002',17,1,NULL,'1'),('savon germol GF','PRSA0003',17,1,NULL,'1'),('savon imperial GF','PRSA0004',17,1,NULL,'1'),('savon imperial PF','PRSA0005',17,1,NULL,'1'),('savon funbact 125g','PRSA0006',17,1,NULL,'1'),('savon pigeon','PRSA0007',17,1,NULL,'1'),('savon Lwanzo','PRSA0008',17,1,NULL,'1'),('savon monganga','PRSA0009',17,1,NULL,'1'),('Savon saibu','PRSA0010',17,1,NULL,'1'),('Savon salama','PRSA0011',17,1,NULL,'1'),('Savon bare sycovir','PRSA0012',17,1,NULL,'1'),('cotex diva','PRSE0001',23,1,NULL,'1'),('cotex lavable','PRSE0002',23,1,NULL,'1'),('cotex naomi','PRSE0003',23,1,NULL,'1'),('Cotex softcare','PRSE0004',23,1,NULL,'1'),('Cuillère','PRUS0001',14,1,NULL,'1'),('Fourchette','PRUS0002',14,1,NULL,'1'),('plat','PRUS0003',14,1,NULL,'1'),('lunch box grand format','PRUS0004',14,1,NULL,'1'),('lunch box petit format','PRUS0005',14,1,NULL,'1');
/*!40000 ALTER TABLE `stock_article` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_beneficelot`
--

DROP TABLE IF EXISTS `stock_beneficelot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_beneficelot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `quantite_vendue` int unsigned NOT NULL,
  `prix_achat` decimal(10,2) NOT NULL,
  `prix_vente` decimal(10,2) NOT NULL,
  `benefice_unitaire` decimal(10,2) NOT NULL,
  `benefice_total` decimal(12,2) NOT NULL,
  `date_calcul` datetime(6) NOT NULL,
  `ligne_sortie_id` bigint DEFAULT NULL,
  `lot_entree_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_beneficelot_ligne_sortie_id_82bcff57_fk_stock_lig` (`ligne_sortie_id`),
  KEY `stock_beneficelot_lot_entree_id_9e1012b4_fk_stock_ligneentree_id` (`lot_entree_id`),
  CONSTRAINT `stock_beneficelot_ligne_sortie_id_82bcff57_fk_stock_lig` FOREIGN KEY (`ligne_sortie_id`) REFERENCES `stock_lignesortie` (`id`),
  CONSTRAINT `stock_beneficelot_lot_entree_id_9e1012b4_fk_stock_ligneentree_id` FOREIGN KEY (`lot_entree_id`) REFERENCES `stock_ligneentree` (`id`),
  CONSTRAINT `stock_beneficelot_chk_1` CHECK ((`quantite_vendue` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_beneficelot`
--

LOCK TABLES `stock_beneficelot` WRITE;
/*!40000 ALTER TABLE `stock_beneficelot` DISABLE KEYS */;
INSERT INTO `stock_beneficelot` VALUES (1,20,0.20,0.30,0.10,2.00,'2026-02-12 13:13:26.136018',1,1),(2,10,0.20,0.30,0.10,1.00,'2026-02-12 13:21:01.881979',2,1),(3,65,0.20,0.30,0.10,6.50,'2026-02-16 14:07:41.200236',3,1),(4,40,1.00,1.50,0.50,20.00,'2026-02-16 14:07:41.284874',4,3),(5,2,0.20,0.30,0.10,0.20,'2026-02-16 14:16:38.795730',5,1),(6,1,0.20,0.30,0.10,0.10,'2026-02-16 14:31:51.161905',6,1);
/*!40000 ALTER TABLE `stock_beneficelot` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_client`
--

DROP TABLE IF EXISTS `stock_client`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_client` (
  `id` varchar(20) NOT NULL,
  `nom` varchar(150) NOT NULL,
  `telephone` varchar(50) DEFAULT NULL,
  `adresse` varchar(255) DEFAULT NULL,
  `email` varchar(254) DEFAULT NULL,
  `date_enregistrement` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_client`
--

LOCK TABLES `stock_client` WRITE;
/*!40000 ALTER TABLE `stock_client` DISABLE KEYS */;
INSERT INTO `stock_client` VALUES ('CLI0001','Jean Paul',NULL,NULL,NULL,'2026-02-12 13:11:23.325746'),('CLI0002','volonte',NULL,NULL,NULL,'2026-02-16 14:15:23.731074');
/*!40000 ALTER TABLE `stock_client` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_detteclient`
--

DROP TABLE IF EXISTS `stock_detteclient`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_detteclient` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `montant_total` decimal(12,2) NOT NULL,
  `montant_paye` decimal(12,2) NOT NULL,
  `solde_restant` decimal(12,2) NOT NULL,
  `date_creation` datetime(6) NOT NULL,
  `date_echeance` date DEFAULT NULL,
  `statut` varchar(20) NOT NULL,
  `commentaire` longtext,
  `client_id` varchar(20) NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `sortie_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `sortie_id` (`sortie_id`),
  KEY `stock_detteclient_devise_id_684fe1d6_fk_stock_devise_id` (`devise_id`),
  KEY `stock_detteclient_client_id_70fee6c4_fk` (`client_id`),
  CONSTRAINT `stock_detteclient_client_id_70fee6c4_fk` FOREIGN KEY (`client_id`) REFERENCES `stock_client` (`id`),
  CONSTRAINT `stock_detteclient_devise_id_684fe1d6_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_detteclient_sortie_id_cb8d6fd0_fk_stock_sortie_id` FOREIGN KEY (`sortie_id`) REFERENCES `stock_sortie` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_detteclient`
--

LOCK TABLES `stock_detteclient` WRITE;
/*!40000 ALTER TABLE `stock_detteclient` DISABLE KEYS */;
INSERT INTO `stock_detteclient` VALUES (1,3.00,3.00,0.00,'2026-02-12 13:21:02.066882','2026-03-14','PAYEE','Dette générée automatiquement pour la sortie #2','CLI0001',1,2),(2,0.60,0.60,0.00,'2026-02-16 14:16:38.980629','2026-03-18','PAYEE','Dette générée automatiquement pour la sortie #4','CLI0002',1,4),(3,0.30,0.00,0.30,'2026-02-16 14:31:51.346799','2026-03-18','EN_COURS','Dette générée automatiquement pour la sortie #5','CLI0001',1,5);
/*!40000 ALTER TABLE `stock_detteclient` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_devise`
--

DROP TABLE IF EXISTS `stock_devise`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_devise` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `sigle` varchar(10) NOT NULL,
  `nom` varchar(100) NOT NULL,
  `symbole` varchar(10) NOT NULL,
  `est_principal` tinyint(1) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `stock_devise_sigle_entreprise_id_252fe25d_uniq` (`sigle`,`entreprise_id`),
  KEY `stock_devise_entreprise_id_ba205630_fk_stock_entreprise_id` (`entreprise_id`),
  CONSTRAINT `stock_devise_entreprise_id_ba205630_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_devise`
--

LOCK TABLES `stock_devise` WRITE;
/*!40000 ALTER TABLE `stock_devise` DISABLE KEYS */;
INSERT INTO `stock_devise` VALUES (1,'USD','Dollar American','$',1,1);
/*!40000 ALTER TABLE `stock_devise` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_entree`
--

DROP TABLE IF EXISTS `stock_entree`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_entree` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `libele` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `date_op` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_entree`
--

LOCK TABLES `stock_entree` WRITE;
/*!40000 ALTER TABLE `stock_entree` DISABLE KEYS */;
INSERT INTO `stock_entree` VALUES (1,'Approvisionnement','','2026-02-12 13:08:16.895013'),(2,'Approvisionnement','','2026-02-16 13:46:52.536012'),(3,'Approvisionnement','','2026-02-16 13:51:41.778050');
/*!40000 ALTER TABLE `stock_entree` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_entreprise`
--

DROP TABLE IF EXISTS `stock_entreprise`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_entreprise` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nom` varchar(255) NOT NULL,
  `secteur` varchar(255) NOT NULL,
  `pays` varchar(100) NOT NULL,
  `adresse` varchar(255) NOT NULL,
  `telephone` varchar(50) NOT NULL,
  `email` varchar(191) NOT NULL,
  `nif` varchar(100) NOT NULL,
  `responsable` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `stock_entreprise_email_bd39f485_uniq` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_entreprise`
--

LOCK TABLES `stock_entreprise` WRITE;
/*!40000 ALTER TABLE `stock_entreprise` DISABLE KEYS */;
INSERT INTO `stock_entreprise` VALUES (1,'UNIVERSITE ADVENTISTE DE LUKANGA','commerce','Congo','NORD-KIVU/LUKANGA','+243996655252','uniluk@gmail.com','NIF900','console malambo');
/*!40000 ALTER TABLE `stock_entreprise` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_ligneentree`
--

DROP TABLE IF EXISTS `stock_ligneentree`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_ligneentree` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `quantite` int unsigned NOT NULL,
  `prix_unitaire` decimal(10,2) NOT NULL,
  `date_entree` datetime(6) NOT NULL,
  `date_expiration` date DEFAULT NULL,
  `seuil_alerte` int unsigned NOT NULL,
  `article_id` varchar(10) NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `entree_id` bigint NOT NULL,
  `prix_vente` decimal(10,2) NOT NULL,
  `quantite_restante` int unsigned NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_ligneentree_devise_id_2d1d5e04_fk_stock_devise_id` (`devise_id`),
  KEY `stock_ligneentree_entree_id_c3061fbb_fk_stock_entree_id` (`entree_id`),
  KEY `stock_ligne_article_e99d66_idx` (`article_id`,`date_entree`),
  CONSTRAINT `stock_ligneentree_article_id_5e64e8c1_fk_stock_art` FOREIGN KEY (`article_id`) REFERENCES `stock_article` (`article_id`),
  CONSTRAINT `stock_ligneentree_devise_id_2d1d5e04_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_ligneentree_entree_id_c3061fbb_fk_stock_entree_id` FOREIGN KEY (`entree_id`) REFERENCES `stock_entree` (`id`),
  CONSTRAINT `stock_ligneentree_chk_1` CHECK ((`quantite` >= 0)),
  CONSTRAINT `stock_ligneentree_chk_2` CHECK ((`seuil_alerte` >= 0)),
  CONSTRAINT `stock_ligneentree_chk_3` CHECK ((`quantite_restante` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_ligneentree`
--

LOCK TABLES `stock_ligneentree` WRITE;
/*!40000 ALTER TABLE `stock_ligneentree` DISABLE KEYS */;
INSERT INTO `stock_ligneentree` VALUES (1,100,0.20,'2026-02-12 13:08:16.910647',NULL,10,'PRUS0005',1,1,0.30,2),(2,100,5.00,'2026-02-16 13:46:52.536012',NULL,15,'PRLI0007',1,2,6.00,100),(3,50,1.00,'2026-02-16 13:51:41.778050',NULL,10,'PRUS0004',1,3,1.50,10);
/*!40000 ALTER TABLE `stock_ligneentree` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_lignesortie`
--

DROP TABLE IF EXISTS `stock_lignesortie`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_lignesortie` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `quantite` int unsigned NOT NULL,
  `prix_unitaire` decimal(10,2) NOT NULL,
  `date_sortie` datetime(6) NOT NULL,
  `article_id` varchar(10) NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `sortie_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_lignesortie_article_id_312442c3_fk_stock_art` (`article_id`),
  KEY `stock_lignesortie_devise_id_7c23f097_fk_stock_devise_id` (`devise_id`),
  KEY `stock_lignesortie_sortie_id_71da70c4_fk_stock_sortie_id` (`sortie_id`),
  CONSTRAINT `stock_lignesortie_article_id_312442c3_fk_stock_art` FOREIGN KEY (`article_id`) REFERENCES `stock_article` (`article_id`),
  CONSTRAINT `stock_lignesortie_devise_id_7c23f097_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_lignesortie_sortie_id_71da70c4_fk_stock_sortie_id` FOREIGN KEY (`sortie_id`) REFERENCES `stock_sortie` (`id`),
  CONSTRAINT `stock_lignesortie_chk_1` CHECK ((`quantite` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_lignesortie`
--

LOCK TABLES `stock_lignesortie` WRITE;
/*!40000 ALTER TABLE `stock_lignesortie` DISABLE KEYS */;
INSERT INTO `stock_lignesortie` VALUES (1,20,0.30,'2026-02-12 13:13:26.104770','PRUS0005',1,1),(2,10,0.30,'2026-02-12 13:21:01.881979','PRUS0005',1,2),(3,65,0.30,'2026-02-16 14:07:41.099974','PRUS0005',1,3),(4,40,1.50,'2026-02-16 14:07:41.284874','PRUS0004',1,3),(5,2,0.30,'2026-02-16 14:16:38.795730','PRUS0005',1,4),(6,1,0.30,'2026-02-16 14:31:51.161905','PRUS0005',1,5);
/*!40000 ALTER TABLE `stock_lignesortie` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_lignesortielot`
--

DROP TABLE IF EXISTS `stock_lignesortielot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_lignesortielot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `quantite` int unsigned NOT NULL,
  `prix_achat` decimal(10,2) NOT NULL,
  `prix_vente` decimal(10,2) NOT NULL,
  `ligne_sortie_id` bigint NOT NULL,
  `lot_entree_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_lignesortielot_lot_entree_id_46ef78be_fk_stock_lig` (`lot_entree_id`),
  KEY `stock_ligne_ligne_s_c7f781_idx` (`ligne_sortie_id`,`lot_entree_id`),
  CONSTRAINT `stock_lignesortielot_ligne_sortie_id_aa9087ab_fk_stock_lig` FOREIGN KEY (`ligne_sortie_id`) REFERENCES `stock_lignesortie` (`id`),
  CONSTRAINT `stock_lignesortielot_lot_entree_id_46ef78be_fk_stock_lig` FOREIGN KEY (`lot_entree_id`) REFERENCES `stock_ligneentree` (`id`),
  CONSTRAINT `stock_lignesortielot_chk_1` CHECK ((`quantite` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_lignesortielot`
--

LOCK TABLES `stock_lignesortielot` WRITE;
/*!40000 ALTER TABLE `stock_lignesortielot` DISABLE KEYS */;
INSERT INTO `stock_lignesortielot` VALUES (1,20,0.20,0.30,1,1),(2,10,0.20,0.30,2,1),(3,65,0.20,0.30,3,1),(4,40,1.00,1.50,4,3),(5,2,0.20,0.30,5,1),(6,1,0.20,0.30,6,1);
/*!40000 ALTER TABLE `stock_lignesortielot` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_mouvementcaisse`
--

DROP TABLE IF EXISTS `stock_mouvementcaisse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_mouvementcaisse` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `date` datetime(6) NOT NULL,
  `montant` decimal(12,2) NOT NULL,
  `type` varchar(10) NOT NULL,
  `motif` longtext NOT NULL,
  `moyen` varchar(30) DEFAULT NULL,
  `reference_piece` varchar(100) DEFAULT NULL,
  `devise_id` bigint DEFAULT NULL,
  `entree_id` bigint DEFAULT NULL,
  `sortie_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_mouvementcaisse_devise_id_338fdfd8_fk_stock_devise_id` (`devise_id`),
  KEY `stock_mouvementcaisse_entree_id_e4bddbfa_fk_stock_entree_id` (`entree_id`),
  KEY `stock_mouvementcaisse_sortie_id_a52a187c_fk_stock_sortie_id` (`sortie_id`),
  CONSTRAINT `stock_mouvementcaisse_devise_id_338fdfd8_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_mouvementcaisse_entree_id_e4bddbfa_fk_stock_entree_id` FOREIGN KEY (`entree_id`) REFERENCES `stock_entree` (`id`),
  CONSTRAINT `stock_mouvementcaisse_sortie_id_a52a187c_fk_stock_sortie_id` FOREIGN KEY (`sortie_id`) REFERENCES `stock_sortie` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_mouvementcaisse`
--

LOCK TABLES `stock_mouvementcaisse` WRITE;
/*!40000 ALTER TABLE `stock_mouvementcaisse` DISABLE KEYS */;
INSERT INTO `stock_mouvementcaisse` VALUES (1,'2026-02-12 13:03:59.793904',10000.00,'ENTREE','Capital','Cash','',1,NULL,NULL),(2,'2026-02-12 13:08:17.010912',20.00,'SORTIE','Approvisionnement entrée #1','Cash',NULL,1,1,NULL),(3,'2026-02-12 13:13:26.136018',6.00,'ENTREE','Vente sortie #1 - USD','Cash',NULL,1,NULL,1),(4,'2026-02-12 13:21:01.881979',0.00,'ENTREE','Vente sortie #2 - USD (EN CRÉDIT - montant 0)','Crédit',NULL,1,NULL,2),(5,'2026-02-12 13:22:53.424339',2.00,'ENTREE','Paiement dette client Jean Paul','Espèces','DET-1',1,NULL,NULL),(6,'2026-02-12 13:24:59.881379',1.00,'ENTREE','Paiement dette client Jean Paul','Espèces','DET-1',1,NULL,NULL),(7,'2026-02-16 13:46:52.567262',500.00,'SORTIE','Approvisionnement entrée #2','Cash',NULL,1,2,NULL),(8,'2026-02-16 13:49:58.163722',5000.00,'ENTREE','capial propre','Cash','',1,NULL,NULL),(9,'2026-02-16 13:51:41.793673',50.00,'SORTIE','Approvisionnement entrée #3','Cash',NULL,1,3,NULL),(10,'2026-02-16 14:07:41.300500',79.50,'ENTREE','Vente sortie #3 - USD','Cash',NULL,1,NULL,3),(11,'2026-02-16 14:16:38.795730',0.00,'ENTREE','Vente sortie #4 - USD (EN CRÉDIT - montant 0)','Crédit',NULL,1,NULL,4),(12,'2026-02-16 14:21:43.224893',0.60,'ENTREE','Paiement dette client volonte','Espèces','DET-2',1,NULL,NULL),(13,'2026-02-16 14:31:51.177531',0.00,'ENTREE','Vente sortie #5 - USD (EN CRÉDIT - montant 0)','Crédit',NULL,1,NULL,5);
/*!40000 ALTER TABLE `stock_mouvementcaisse` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_paiementdette`
--

DROP TABLE IF EXISTS `stock_paiementdette`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_paiementdette` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `montant_paye` decimal(12,2) NOT NULL,
  `date_paiement` datetime(6) NOT NULL,
  `moyen` varchar(50) DEFAULT NULL,
  `dette_id` bigint NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `reference` varchar(100) DEFAULT NULL,
  `utilisateur_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_paiementdette_dette_id_11c70796_fk_stock_detteclient_id` (`dette_id`),
  KEY `stock_paiementdette_devise_id_37ca7a0d_fk_stock_devise_id` (`devise_id`),
  KEY `stock_paiementdette_utilisateur_id_0f570acb_fk_users_user_id` (`utilisateur_id`),
  CONSTRAINT `stock_paiementdette_dette_id_11c70796_fk_stock_detteclient_id` FOREIGN KEY (`dette_id`) REFERENCES `stock_detteclient` (`id`),
  CONSTRAINT `stock_paiementdette_devise_id_37ca7a0d_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_paiementdette_utilisateur_id_0f570acb_fk_users_user_id` FOREIGN KEY (`utilisateur_id`) REFERENCES `users_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_paiementdette`
--

LOCK TABLES `stock_paiementdette` WRITE;
/*!40000 ALTER TABLE `stock_paiementdette` DISABLE KEYS */;
INSERT INTO `stock_paiementdette` VALUES (1,2.00,'2026-02-12 13:22:53.107879','Espèces',1,1,NULL,1),(2,1.00,'2026-02-12 13:24:59.542776','Espèces',1,1,NULL,1),(3,0.60,'2026-02-16 14:21:42.845986','Espèces',2,1,NULL,1);
/*!40000 ALTER TABLE `stock_paiementdette` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_sortie`
--

DROP TABLE IF EXISTS `stock_sortie`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_sortie` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `motif` varchar(255) NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `statut` varchar(20) NOT NULL,
  `client_id` varchar(20) DEFAULT NULL,
  `date_creation` datetime(6) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_sortie_devise_id_e9eda902_fk_stock_devise_id` (`devise_id`),
  KEY `stock_sortie_client_id_10acccc9_fk_stock_client_id` (`client_id`),
  CONSTRAINT `stock_sortie_client_id_10acccc9_fk_stock_client_id` FOREIGN KEY (`client_id`) REFERENCES `stock_client` (`id`),
  CONSTRAINT `stock_sortie_devise_id_e9eda902_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_sortie`
--

LOCK TABLES `stock_sortie` WRITE;
/*!40000 ALTER TABLE `stock_sortie` DISABLE KEYS */;
INSERT INTO `stock_sortie` VALUES (1,'Vente au Client',NULL,'PAYEE','CLI0001','2026-02-12 13:13:26.073507'),(2,'Vente au Client',NULL,'EN_CREDIT','CLI0001','2026-02-12 13:21:01.850731'),(3,'Vente au Client',NULL,'PAYEE',NULL,'2026-02-16 14:07:41.053102'),(4,'Vente au Client',NULL,'EN_CREDIT','CLI0002','2026-02-16 14:16:38.780107'),(5,'Vente au Client',NULL,'EN_CREDIT','CLI0001','2026-02-16 14:31:51.146281');
/*!40000 ALTER TABLE `stock_sortie` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_soustypearticle`
--

DROP TABLE IF EXISTS `stock_soustypearticle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_soustypearticle` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `libelle` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  `type_article_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_soustypearticl_type_article_id_474c6f25_fk_stock_typ` (`type_article_id`),
  CONSTRAINT `stock_soustypearticl_type_article_id_474c6f25_fk_stock_typ` FOREIGN KEY (`type_article_id`) REFERENCES `stock_typearticle` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=35 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_soustypearticle`
--

LOCK TABLES `stock_soustypearticle` WRITE;
/*!40000 ALTER TABLE `stock_soustypearticle` DISABLE KEYS */;
INSERT INTO `stock_soustypearticle` VALUES (1,'Cahiers & papiers','',1),(2,'Stylos, crayons & écriture','',1),(3,'Papier spécial','',1),(4,'Classement & organisation','',1),(5,'Enveloppes & emballages','',1),(6,'Agrafage & collage','',2),(7,'Découpe & outils','',2),(8,'Produits de base','',3),(9,'roduits frais & naturels','',3),(10,'Biscuits & snacks','',3),(11,'Produits laitiers','',3),(12,'Boissons & jus','',3),(13,'Matières pour pâtisserie','',3),(14,'Ustensiles de cuisine','',4),(15,'Nettoyage & entretien','',4),(16,'Consommables ménage','',4),(17,'Savons','',5),(18,'Dentifrices & soins bouche','',5),(19,'Crèmes & lotions','',5),(20,'Pommades & gels','',5),(21,'Glycerines','',5),(22,'Parfums & poudres','',5),(23,'Serviettes hygiéniques','',6),(24,'Produits bébé','',6),(25,'Sous-vêtements','',7),(26,'Chaussettes & habits','',7),(27,'Chaussures & accessoires','',7),(28,'Bible','',8),(29,'Livre','',8),(30,'Stockage & accessoires','',9),(31,'Energie & connexion','',9),(32,'Piles','',9),(33,'Divers','',10),(34,'Pagne mifeme','',8);
/*!40000 ALTER TABLE `stock_soustypearticle` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_stock`
--

DROP TABLE IF EXISTS `stock_stock`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_stock` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `Qte` int unsigned NOT NULL,
  `seuilAlert` int unsigned NOT NULL,
  `article_id` varchar(10) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `article_id` (`article_id`),
  CONSTRAINT `stock_stock_article_id_7735da86_fk_stock_article_article_id` FOREIGN KEY (`article_id`) REFERENCES `stock_article` (`article_id`),
  CONSTRAINT `stock_stock_chk_1` CHECK ((`Qte` >= 0)),
  CONSTRAINT `stock_stock_chk_2` CHECK ((`seuilAlert` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=208 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_stock`
--

LOCK TABLES `stock_stock` WRITE;
/*!40000 ALTER TABLE `stock_stock` DISABLE KEYS */;
INSERT INTO `stock_stock` VALUES (1,0,0,'FOCA0001'),(2,0,0,'FOCA0002'),(3,0,0,'FOCA0003'),(4,0,0,'FOCA0004'),(5,0,0,'FOCA0005'),(6,0,0,'FOCA0006'),(7,0,0,'FOCA0007'),(8,0,0,'FOCA0008'),(9,0,0,'FOCA0009'),(10,0,0,'FOCA0010'),(11,0,0,'FOCA0011'),(12,0,0,'FOCA0012'),(13,0,0,'FOCA0013'),(14,0,0,'FOST0001'),(15,0,0,'FOST0002'),(16,0,0,'FOST0003'),(17,0,0,'FOST0004'),(18,0,0,'FOST0005'),(19,0,0,'FOST0006'),(20,0,0,'FOST0007'),(21,0,0,'FOST0008'),(22,0,0,'FOST0009'),(23,0,0,'FOCA0014'),(24,0,0,'FOCA0015'),(25,0,0,'FOCA0016'),(26,0,0,'FOCA0017'),(27,0,0,'FOCA0018'),(28,0,0,'FOCA0019'),(29,0,0,'FOCA0020'),(30,0,0,'FOCA0021'),(31,0,0,'FOCA0022'),(32,0,0,'FOCA0023'),(33,0,0,'FOCA0024'),(34,0,0,'FOCA0025'),(35,0,0,'FOCA0026'),(36,0,0,'FOCA0027'),(37,0,0,'FOCA0028'),(38,0,0,'FOCA0029'),(39,0,0,'FOCA0030'),(40,0,0,'FOCA0031'),(41,0,0,'FOCA0032'),(42,0,0,'FOAG0001'),(43,0,0,'FOAG0002'),(44,0,0,'FOAG0003'),(45,0,0,'FOAG0004'),(46,0,0,'FOAG0005'),(47,0,0,'FODÉ0001'),(48,0,0,'FODÉ0002'),(49,0,0,'FODÉ0003'),(50,0,0,'PRPR0001'),(51,0,0,'PRPR0002'),(52,0,0,'PRPR0003'),(53,0,0,'PRPR0004'),(54,0,0,'PRPR0005'),(55,0,0,'PRPR0006'),(56,0,0,'PRPR0007'),(57,0,0,'PRPR0008'),(58,0,0,'PRRO0001'),(59,0,0,'PRRO0002'),(60,0,0,'PRRO0003'),(61,0,0,'PRRO0004'),(62,0,0,'PRBI0001'),(63,0,0,'PRBI0002'),(64,0,0,'PRBI0003'),(65,0,0,'PRBI0004'),(66,0,0,'PRBI0005'),(67,0,0,'PRBI0006'),(68,0,0,'PRBI0007'),(69,0,0,'PRBI0008'),(70,0,0,'PRBI0009'),(71,0,0,'PRBI0010'),(72,0,0,'PRBO0001'),(73,0,0,'PRBO0002'),(74,0,0,'PRBO0003'),(75,0,0,'PRBO0004'),(76,0,0,'PRBO0005'),(77,0,0,'PRBO0006'),(78,0,0,'PRBO0007'),(79,0,0,'PRBO0008'),(80,0,0,'PRBO0009'),(81,0,0,'PRBO0010'),(82,0,0,'PRMA0001'),(83,0,0,'PRMA0002'),(84,0,0,'PRMA0003'),(85,0,0,'PRMA0004'),(86,0,0,'PRMA0005'),(87,0,0,'PRMA0006'),(88,0,0,'PRUS0001'),(89,0,0,'PRUS0002'),(90,0,0,'PRUS0003'),(91,10,10,'PRUS0004'),(92,2,10,'PRUS0005'),(93,0,0,'PRNE0001'),(94,0,0,'PRNE0002'),(95,0,0,'PRNE0003'),(96,0,0,'PRNE0004'),(97,0,0,'PRNE0005'),(98,0,0,'PRNE0006'),(99,0,0,'PRCO0001'),(100,0,0,'PRCO0002'),(101,0,0,'PRCO0003'),(102,0,0,'PRCO0004'),(103,0,0,'PRCO0005'),(104,0,0,'PRCO0006'),(105,0,0,'PRSA0001'),(106,0,0,'PRSA0002'),(107,0,0,'PRSA0003'),(108,0,0,'PRSA0004'),(109,0,0,'PRSA0005'),(110,0,0,'PRSA0006'),(111,0,0,'PRSA0007'),(112,0,0,'PRSA0008'),(113,0,0,'PRSA0009'),(114,0,0,'PRSA0010'),(115,0,0,'PRSA0011'),(116,0,0,'PRSA0012'),(117,0,0,'PRDE0001'),(118,0,0,'PRDE0002'),(119,0,0,'PRDE0003'),(120,0,0,'PRDE0004'),(121,0,0,'PRDE0005'),(122,0,0,'PRDE0006'),(123,0,0,'PRCR0001'),(124,0,0,'PRCR0002'),(125,0,0,'PRCR0003'),(126,0,0,'PRCR0004'),(127,0,0,'PRCR0005'),(128,0,0,'PRCR0006'),(129,0,0,'PRCR0007'),(130,0,0,'PRCR0008'),(131,0,0,'PRCR0009'),(132,0,0,'PRCR0010'),(133,0,0,'PRCR0011'),(134,0,0,'PRCR0012'),(135,0,0,'PRCR0013'),(136,0,0,'PRCR0014'),(137,0,0,'PRCR0015'),(138,0,0,'PRCR0016'),(139,0,0,'PRCR0017'),(140,0,0,'PRCR0018'),(141,0,0,'PRCR0019'),(142,0,0,'PRCR0020'),(143,0,0,'PRCR0021'),(144,0,0,'PRCR0022'),(145,0,0,'PRCR0023'),(146,0,0,'PRCR0024'),(147,0,0,'PRCR0025'),(148,0,0,'PRGL0001'),(149,0,0,'PRGL0002'),(150,0,0,'PRGL0003'),(151,0,0,'PRGL0004'),(152,0,0,'PRGL0005'),(153,0,0,'PRGL0006'),(154,0,0,'PRPA0001'),(155,0,0,'PRPA0002'),(156,0,0,'PRPA0003'),(157,0,0,'PRPA0004'),(158,0,0,'PRSE0001'),(159,0,0,'PRSE0002'),(160,0,0,'PRSE0003'),(161,0,0,'PRSE0004'),(162,0,0,'HASO0001'),(163,0,0,'HASO0002'),(164,0,0,'HASO0003'),(165,0,0,'HASO0004'),(166,0,0,'HASO0005'),(167,0,0,'HASO0006'),(168,0,0,'HASO0007'),(169,0,0,'HASO0008'),(170,0,0,'HASO0009'),(171,0,0,'HASO0010'),(172,0,0,'HASO0011'),(173,0,0,'HASO0012'),(174,0,0,'HACH0001'),(175,0,0,'HACH0002'),(176,0,0,'HACH0003'),(177,0,0,'HACH0004'),(178,0,0,'PRLI0001'),(179,0,0,'PRLI0002'),(180,0,0,'PRLI0003'),(181,0,0,'PRLI0004'),(182,0,0,'PRLI0005'),(183,0,0,'PRLI0006'),(184,0,0,'PREN0001'),(185,0,0,'PREN0002'),(186,0,0,'PREN0003'),(187,0,0,'PREN0004'),(188,0,0,'PRPI0001'),(189,0,0,'PRPI0002'),(190,0,0,'PRPI0003'),(191,0,0,'PRPI0004'),(192,0,0,'PRPI0005'),(193,0,0,'ARDI0001'),(194,0,0,'ARDI0002'),(195,0,0,'ARDI0003'),(196,0,0,'ARDI0004'),(197,0,0,'ARDI0005'),(198,0,0,'ARDI0006'),(199,0,0,'ARDI0007'),(200,0,0,'ARDI0008'),(201,0,0,'ARDI0009'),(202,0,0,'ARDI0010'),(203,0,0,'ARDI0011'),(204,0,0,'ARDI0012'),(205,0,0,'ARDI0013'),(206,0,0,'ARDI0014'),(207,100,15,'PRLI0007');
/*!40000 ALTER TABLE `stock_stock` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_typearticle`
--

DROP TABLE IF EXISTS `stock_typearticle`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_typearticle` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `libelle` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_typearticle`
--

LOCK TABLES `stock_typearticle` WRITE;
/*!40000 ALTER TABLE `stock_typearticle` DISABLE KEYS */;
INSERT INTO `stock_typearticle` VALUES (1,'FOURNITURES SCOLAIRES & DE BUREAU',''),(2,'FOURNITURES DE BUREAU & PAPETERIE DIVERSE',''),(3,'PRODUITS ALIMENTAIRES (NOURRITURE)',''),(4,'PRODUITS DE CUISINE & MENAGE',''),(5,'PRODUITS COSMETIQUES & HYGIENE CORPORELLE',''),(6,'PRODUITS FEMININS & BEBE',''),(7,'HABILLEMENT & ACCESSOIRES',''),(8,'PRODUITS RELIGIEUX',''),(9,'PRODUITS ELECTRONIQUES & ACCESSOIRES',''),(10,'ARTICLES DIVERS & QUINCAILLERIE LEGERE','');
/*!40000 ALTER TABLE `stock_typearticle` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_unite`
--

DROP TABLE IF EXISTS `stock_unite`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_unite` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `libelle` varchar(100) NOT NULL,
  `description` longtext NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_unite`
--

LOCK TABLES `stock_unite` WRITE;
/*!40000 ALTER TABLE `stock_unite` DISABLE KEYS */;
INSERT INTO `stock_unite` VALUES (1,'Pc / Pièce',''),(2,'Kg',''),(3,'Paquet',''),(4,'Boîte',''),(5,'Carton',''),(6,'Bouteille',''),(7,'Litre',''),(8,'Paire',''),(9,'Sachet',''),(10,'Bidon',''),(11,'Rouleau',''),(12,'Plaquette',''),(13,'sac','');
/*!40000 ALTER TABLE `stock_unite` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `token_blacklist_blacklistedtoken`
--

DROP TABLE IF EXISTS `token_blacklist_blacklistedtoken`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `token_blacklist_blacklistedtoken` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `blacklisted_at` datetime(6) NOT NULL,
  `token_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_id` (`token_id`),
  CONSTRAINT `token_blacklist_blacklistedtoken_token_id_3cc7fe56_fk` FOREIGN KEY (`token_id`) REFERENCES `token_blacklist_outstandingtoken` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `token_blacklist_blacklistedtoken`
--

LOCK TABLES `token_blacklist_blacklistedtoken` WRITE;
/*!40000 ALTER TABLE `token_blacklist_blacklistedtoken` DISABLE KEYS */;
/*!40000 ALTER TABLE `token_blacklist_blacklistedtoken` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `token_blacklist_outstandingtoken`
--

DROP TABLE IF EXISTS `token_blacklist_outstandingtoken`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `token_blacklist_outstandingtoken` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `token` longtext NOT NULL,
  `created_at` datetime(6) DEFAULT NULL,
  `expires_at` datetime(6) NOT NULL,
  `user_id` bigint DEFAULT NULL,
  `jti` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token_blacklist_outstandingtoken_jti_hex_d9bdf6f7_uniq` (`jti`),
  KEY `token_blacklist_outs_user_id_83bc629a_fk_users_use` (`user_id`),
  CONSTRAINT `token_blacklist_outs_user_id_83bc629a_fk_users_use` FOREIGN KEY (`user_id`) REFERENCES `users_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `token_blacklist_outstandingtoken`
--

LOCK TABLES `token_blacklist_outstandingtoken` WRITE;
/*!40000 ALTER TABLE `token_blacklist_outstandingtoken` DISABLE KEYS */;
INSERT INTO `token_blacklist_outstandingtoken` VALUES (1,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3MDc0MDI0NSwiaWF0IjoxNzcwNjUzODQ1LCJqdGkiOiJhZmQxMjhjMzNiOTM0ZWRkYWE5YTdmNGYxZmJkY2I2YiIsInVzZXJfaWQiOiIxIn0.K4HH1gH8jBfvzloEsizWHUHhTOJVsnid-8K3pTEtCwk','2026-02-09 16:17:25.120059','2026-02-10 16:17:25.000000',1,'afd128c33b934eddaa9a7f4f1fbdcb6b'),(2,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3MDc0MDM0NiwiaWF0IjoxNzcwNjUzOTQ2LCJqdGkiOiIyNTM1NDkzMzkzMTQ0YWFiYThkMTZhZjNiMWQxNjFkOSIsInVzZXJfaWQiOiIyIn0.4h-n0kCWnbHVsPaRkqx9HeNcDz_a-xjhkuUuxYe4RCE','2026-02-09 16:19:06.450007','2026-02-10 16:19:06.000000',2,'2535493393144aaba8d16af3b1d161d9'),(3,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3MDc0MDM3MSwiaWF0IjoxNzcwNjUzOTcxLCJqdGkiOiJkNDg2MTFmMzRiODM0ZDcxOWY3NzAzYjYzZDczOGQxMSIsInVzZXJfaWQiOiIxIn0.-Np5kx-eQ-wvXUn0vPKj2sSSd4PIRbpjccBIMneYYgw','2026-02-09 16:19:31.917141','2026-02-10 16:19:31.000000',1,'d48611f34b834d719f7703b63d738d11'),(4,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3MDc5NTU2MiwiaWF0IjoxNzcwNzA5MTYyLCJqdGkiOiJmYjYzOGQ4N2ZkMjM0Njg1OWM3NzhjNjQ2YzNjZGExMCIsInVzZXJfaWQiOiIxIn0.z0q9vGQVoowD6h0ByqvH7CukJHEhUqNwGa87GAnDSGo','2026-02-10 07:39:22.718743','2026-02-11 07:39:22.000000',1,'fb638d87fd2346859c778c646c3cda10'),(5,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3MDk4NzI3NSwiaWF0IjoxNzcwOTAwODc1LCJqdGkiOiJmMjFiMDBjOWZhNGY0ODAzYjZjYWE5MjNmMzllMzlmYSIsInVzZXJfaWQiOiIxIn0.PkdlOjoA9bTNtJ9P3t3dbDLjbG5xlR-LAHI33m_JMTA','2026-02-12 12:54:35.009981','2026-02-13 12:54:35.000000',1,'f21b00c9fa4f4803b6caa923f39e39fa'),(6,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3MTMzMTQyOSwiaWF0IjoxNzcxMjQ1MDI5LCJqdGkiOiI2NGJlM2I4MGJlZjQ0Nzc4OWQzYzhmOGEzYjg0ZTgzMiIsInVzZXJfaWQiOiIxIn0.cbBDDcXj782zLiHGOWK3hWV0fYbSv8nk0Uk9abdN6SI','2026-02-16 12:30:29.597552','2026-02-17 12:30:29.000000',1,'64be3b80bef447789d3c8f8a3b84e832'),(7,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3MTMzNTE2NywiaWF0IjoxNzcxMjQ4NzY3LCJqdGkiOiIxY2VkMGI3OTBkNzE0OWMxOTdjZTlhM2UwN2U0MjliNyIsInVzZXJfaWQiOiIxIn0.KAtt6an8VT_5XltzapuhUMvFXfwiblMveoHduiUGgkQ','2026-02-16 13:32:47.676429','2026-02-17 13:32:47.000000',1,'1ced0b790d7149c197ce9a3e07e429b7');
/*!40000 ALTER TABLE `token_blacklist_outstandingtoken` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users_user`
--

DROP TABLE IF EXISTS `users_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `role` varchar(20) NOT NULL,
  `entreprise_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  KEY `users_user_entreprise_id_a438dd69_fk_stock_entreprise_id` (`entreprise_id`),
  CONSTRAINT `users_user_entreprise_id_a438dd69_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_user`
--

LOCK TABLES `users_user` WRITE;
/*!40000 ALTER TABLE `users_user` DISABLE KEYS */;
INSERT INTO `users_user` VALUES (1,'pbkdf2_sha256$1000000$oga4QflMpMG4RMTD4ysQSH$+lREhPGNKS+Kc7twkNtJsQRT5cn36s3TYe2VLin2yeM=','2026-02-16 13:32:48.171217',0,'console','console','malambo','consolemalambo@gmail.com',0,1,'2026-02-09 16:13:47.381400','admin',1),(2,'pbkdf2_sha256$1000000$LAXQGfVtLVlkmzbuZv23Am$vA4sJRYsEoTLauqeH6H3wseaF4USr89DdtsZWoCa+fA=','2026-02-09 16:19:06.510390',1,'admin','','','admin@gmail.com',1,1,'2026-02-09 16:16:42.190353','superadmin',NULL);
/*!40000 ALTER TABLE `users_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users_user_groups`
--

DROP TABLE IF EXISTS `users_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `users_user_groups_user_id_group_id_b88eab82_uniq` (`user_id`,`group_id`),
  KEY `users_user_groups_group_id_9afc8d0e_fk_auth_group_id` (`group_id`),
  CONSTRAINT `users_user_groups_group_id_9afc8d0e_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `users_user_groups_user_id_5f6f5a90_fk_users_user_id` FOREIGN KEY (`user_id`) REFERENCES `users_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_user_groups`
--

LOCK TABLES `users_user_groups` WRITE;
/*!40000 ALTER TABLE `users_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `users_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users_user_user_permissions`
--

DROP TABLE IF EXISTS `users_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `users_user_user_permissions_user_id_permission_id_43338c45_uniq` (`user_id`,`permission_id`),
  KEY `users_user_user_perm_permission_id_0b93982e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `users_user_user_perm_permission_id_0b93982e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `users_user_user_permissions_user_id_20aca447_fk_users_user_id` FOREIGN KEY (`user_id`) REFERENCES `users_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_user_user_permissions`
--

LOCK TABLES `users_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `users_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `users_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Dumping events for database 'db_cantine'
--

--
-- Dumping routines for database 'db_cantine'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-02-17 13:52:24
