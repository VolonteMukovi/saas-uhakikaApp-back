CREATE DATABASE  IF NOT EXISTS `api_cantines` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `api_cantines`;
-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: api_cantines
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
) ENGINE=InnoDB AUTO_INCREMENT=153 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add Outstanding Token',6,'add_outstandingtoken'),(22,'Can change Outstanding Token',6,'change_outstandingtoken'),(23,'Can delete Outstanding Token',6,'delete_outstandingtoken'),(24,'Can view Outstanding Token',6,'view_outstandingtoken'),(25,'Can add Blacklisted Token',7,'add_blacklistedtoken'),(26,'Can change Blacklisted Token',7,'change_blacklistedtoken'),(27,'Can delete Blacklisted Token',7,'delete_blacklistedtoken'),(28,'Can view Blacklisted Token',7,'view_blacklistedtoken'),(29,'Can add user',8,'add_user'),(30,'Can change user',8,'change_user'),(31,'Can delete user',8,'delete_user'),(32,'Can view user',8,'view_user'),(33,'Can add membership',9,'add_membership'),(34,'Can change membership',9,'change_membership'),(35,'Can delete membership',9,'delete_membership'),(36,'Can view membership',9,'view_membership'),(37,'Can add user branch',10,'add_userbranch'),(38,'Can change user branch',10,'change_userbranch'),(39,'Can delete user branch',10,'delete_userbranch'),(40,'Can view user branch',10,'view_userbranch'),(41,'Can add entreprise',11,'add_entreprise'),(42,'Can change entreprise',11,'change_entreprise'),(43,'Can delete entreprise',11,'delete_entreprise'),(44,'Can view entreprise',11,'view_entreprise'),(45,'Can add succursale',12,'add_succursale'),(46,'Can change succursale',12,'change_succursale'),(47,'Can delete succursale',12,'delete_succursale'),(48,'Can view succursale',12,'view_succursale'),(49,'Can add unite',13,'add_unite'),(50,'Can change unite',13,'change_unite'),(51,'Can delete unite',13,'delete_unite'),(52,'Can view unite',13,'view_unite'),(53,'Can add type article',14,'add_typearticle'),(54,'Can change type article',14,'change_typearticle'),(55,'Can delete type article',14,'delete_typearticle'),(56,'Can view type article',14,'view_typearticle'),(57,'Can add sous type article',15,'add_soustypearticle'),(58,'Can change sous type article',15,'change_soustypearticle'),(59,'Can delete sous type article',15,'delete_soustypearticle'),(60,'Can view sous type article',15,'view_soustypearticle'),(61,'Can add article',16,'add_article'),(62,'Can change article',16,'change_article'),(63,'Can delete article',16,'delete_article'),(64,'Can view article',16,'view_article'),(65,'Can add entree',17,'add_entree'),(66,'Can change entree',17,'change_entree'),(67,'Can delete entree',17,'delete_entree'),(68,'Can view entree',17,'view_entree'),(69,'Can add ligne entree',18,'add_ligneentree'),(70,'Can change ligne entree',18,'change_ligneentree'),(71,'Can delete ligne entree',18,'delete_ligneentree'),(72,'Can view ligne entree',18,'view_ligneentree'),(73,'Can add stock',19,'add_stock'),(74,'Can change stock',19,'change_stock'),(75,'Can delete stock',19,'delete_stock'),(76,'Can view stock',19,'view_stock'),(77,'Can add sortie',20,'add_sortie'),(78,'Can change sortie',20,'change_sortie'),(79,'Can delete sortie',20,'delete_sortie'),(80,'Can view sortie',20,'view_sortie'),(81,'Can add client',21,'add_client'),(82,'Can change client',21,'change_client'),(83,'Can delete client',21,'delete_client'),(84,'Can view client',21,'view_client'),(85,'Can add Dette client',22,'add_detteclient'),(86,'Can change Dette client',22,'change_detteclient'),(87,'Can delete Dette client',22,'delete_detteclient'),(88,'Can view Dette client',22,'view_detteclient'),(89,'Can add Paiement de dette',23,'add_paiementdette'),(90,'Can change Paiement de dette',23,'change_paiementdette'),(91,'Can delete Paiement de dette',23,'delete_paiementdette'),(92,'Can view Paiement de dette',23,'view_paiementdette'),(93,'Can add ligne sortie',24,'add_lignesortie'),(94,'Can change ligne sortie',24,'change_lignesortie'),(95,'Can delete ligne sortie',24,'delete_lignesortie'),(96,'Can view ligne sortie',24,'view_lignesortie'),(97,'Can add Lot utilisé dans sortie',25,'add_lignesortielot'),(98,'Can change Lot utilisé dans sortie',25,'change_lignesortielot'),(99,'Can delete Lot utilisé dans sortie',25,'delete_lignesortielot'),(100,'Can view Lot utilisé dans sortie',25,'view_lignesortielot'),(101,'Can add Bénéfice par lot',26,'add_beneficelot'),(102,'Can change Bénéfice par lot',26,'change_beneficelot'),(103,'Can delete Bénéfice par lot',26,'delete_beneficelot'),(104,'Can view Bénéfice par lot',26,'view_beneficelot'),(105,'Can add mouvement caisse',27,'add_mouvementcaisse'),(106,'Can change mouvement caisse',27,'change_mouvementcaisse'),(107,'Can delete mouvement caisse',27,'delete_mouvementcaisse'),(108,'Can view mouvement caisse',27,'view_mouvementcaisse'),(109,'Can add Devise',28,'add_devise'),(110,'Can change Devise',28,'change_devise'),(111,'Can delete Devise',28,'delete_devise'),(112,'Can view Devise',28,'view_devise'),(113,'Can add Détail mouvement caisse',29,'add_detailmouvementcaisse'),(114,'Can change Détail mouvement caisse',29,'change_detailmouvementcaisse'),(115,'Can delete Détail mouvement caisse',29,'delete_detailmouvementcaisse'),(116,'Can view Détail mouvement caisse',29,'view_detailmouvementcaisse'),(117,'Can add Type de caisse',30,'add_typecaisse'),(118,'Can change Type de caisse',30,'change_typecaisse'),(119,'Can delete Type de caisse',30,'delete_typecaisse'),(120,'Can view Type de caisse',30,'view_typecaisse'),(121,'Can add client entreprise',31,'add_cliententreprise'),(122,'Can change client entreprise',31,'change_cliententreprise'),(123,'Can delete client entreprise',31,'delete_cliententreprise'),(124,'Can view client entreprise',31,'view_cliententreprise'),(125,'Can add lot',32,'add_lot'),(126,'Can change lot',32,'change_lot'),(127,'Can delete lot',32,'delete_lot'),(128,'Can view lot',32,'view_lot'),(129,'Can add frais lot',33,'add_fraislot'),(130,'Can change frais lot',33,'change_fraislot'),(131,'Can delete frais lot',33,'delete_fraislot'),(132,'Can view frais lot',33,'view_fraislot'),(133,'Can add lot item',34,'add_lotitem'),(134,'Can change lot item',34,'change_lotitem'),(135,'Can delete lot item',34,'delete_lotitem'),(136,'Can view lot item',34,'view_lotitem'),(137,'Can add Fournisseur',35,'add_fournisseur'),(138,'Can change Fournisseur',35,'change_fournisseur'),(139,'Can delete Fournisseur',35,'delete_fournisseur'),(140,'Can view Fournisseur',35,'view_fournisseur'),(141,'Can add commande',36,'add_commande'),(142,'Can change commande',36,'change_commande'),(143,'Can delete commande',36,'delete_commande'),(144,'Can view commande',36,'view_commande'),(145,'Can add commande item',37,'add_commandeitem'),(146,'Can change commande item',37,'change_commandeitem'),(147,'Can delete commande item',37,'delete_commandeitem'),(148,'Can view commande item',37,'view_commandeitem'),(149,'Can add commande response',38,'add_commanderesponse'),(150,'Can change commande response',38,'change_commanderesponse'),(151,'Can delete commande response',38,'delete_commanderesponse'),(152,'Can view commande response',38,'view_commanderesponse');
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
) ENGINE=InnoDB AUTO_INCREMENT=39 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(3,'auth','group'),(2,'auth','permission'),(4,'contenttypes','contenttype'),(36,'order','commande'),(37,'order','commandeitem'),(38,'order','commanderesponse'),(35,'order','fournisseur'),(33,'order','fraislot'),(32,'order','lot'),(34,'order','lotitem'),(5,'sessions','session'),(16,'stock','article'),(26,'stock','beneficelot'),(21,'stock','client'),(31,'stock','cliententreprise'),(29,'stock','detailmouvementcaisse'),(22,'stock','detteclient'),(28,'stock','devise'),(17,'stock','entree'),(11,'stock','entreprise'),(18,'stock','ligneentree'),(24,'stock','lignesortie'),(25,'stock','lignesortielot'),(27,'stock','mouvementcaisse'),(23,'stock','paiementdette'),(20,'stock','sortie'),(15,'stock','soustypearticle'),(19,'stock','stock'),(12,'stock','succursale'),(14,'stock','typearticle'),(30,'stock','typecaisse'),(13,'stock','unite'),(7,'token_blacklist','blacklistedtoken'),(6,'token_blacklist','outstandingtoken'),(9,'users','membership'),(8,'users','user'),(10,'users','userbranch');
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
) ENGINE=InnoDB AUTO_INCREMENT=71 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'stock','0001_initial','2026-03-22 04:20:30.195194'),(2,'contenttypes','0001_initial','2026-03-22 04:20:32.386269'),(3,'contenttypes','0002_remove_content_type_name','2026-03-22 04:20:43.556665'),(4,'auth','0001_initial','2026-03-22 04:21:02.154200'),(5,'auth','0002_alter_permission_name_max_length','2026-03-22 04:21:03.912806'),(6,'auth','0003_alter_user_email_max_length','2026-03-22 04:21:03.981837'),(7,'auth','0004_alter_user_username_opts','2026-03-22 04:21:04.075603'),(8,'auth','0005_alter_user_last_login_null','2026-03-22 04:21:04.282728'),(9,'auth','0006_require_contenttypes_0002','2026-03-22 04:21:04.345233'),(10,'auth','0007_alter_validators_add_error_messages','2026-03-22 04:21:04.461180'),(11,'auth','0008_alter_user_username_max_length','2026-03-22 04:21:04.583638'),(12,'auth','0009_alter_user_last_name_max_length','2026-03-22 04:21:04.777715'),(13,'auth','0010_alter_group_name_max_length','2026-03-22 04:21:05.178915'),(14,'auth','0011_update_proxy_permissions','2026-03-22 04:21:05.279191'),(15,'auth','0012_alter_user_first_name_max_length','2026-03-22 04:21:05.348256'),(16,'users','0001_initial','2026-03-22 04:21:18.002627'),(17,'admin','0001_initial','2026-03-22 04:21:26.450425'),(18,'admin','0002_logentry_remove_auto_add','2026-03-22 04:21:26.528565'),(19,'admin','0003_logentry_add_action_flag_choices','2026-03-22 04:21:26.613235'),(20,'sessions','0001_initial','2026-03-22 04:21:28.757394'),(21,'stock','0002_initial','2026-03-22 04:22:11.015684'),(22,'stock','0003_entreprise_logo','2026-03-22 04:22:13.492056'),(23,'stock','0004_add_entreprise_slogan','2026-03-22 04:22:15.776662'),(24,'stock','0005_entreprise_has_branches_succursale','2026-03-22 04:22:22.566236'),(25,'stock','0006_add_tenant_fields_to_models','2026-03-22 04:23:56.718374'),(26,'stock','0007_client_is_special','2026-03-22 04:24:00.846405'),(27,'token_blacklist','0001_initial','2026-03-22 04:24:08.701147'),(28,'token_blacklist','0002_outstandingtoken_jti_hex','2026-03-22 04:24:10.823048'),(29,'token_blacklist','0003_auto_20171017_2007','2026-03-22 04:24:10.992366'),(30,'token_blacklist','0004_auto_20171017_2013','2026-03-22 04:24:14.132933'),(31,'token_blacklist','0005_remove_outstandingtoken_jti','2026-03-22 04:24:16.979184'),(32,'token_blacklist','0006_auto_20171017_2113','2026-03-22 04:24:17.982192'),(33,'token_blacklist','0007_auto_20171017_2214','2026-03-22 04:24:25.404955'),(34,'token_blacklist','0008_migrate_to_bigautofield','2026-03-22 04:24:35.096580'),(35,'token_blacklist','0010_fix_migrate_to_bigautofield','2026-03-22 04:24:35.281567'),(36,'token_blacklist','0011_linearizes_history','2026-03-22 04:24:35.466515'),(37,'token_blacklist','0012_alter_outstandingtoken_user','2026-03-22 04:24:35.936689'),(38,'token_blacklist','0013_alter_blacklistedtoken_options_and_more','2026-03-22 04:24:36.137280'),(39,'users','0002_add_role_user_agent','2026-03-22 04:24:36.268829'),(40,'users','0003_membership_userbranch','2026-03-22 04:24:56.028542'),(41,'users','0004_backfill_memberships_from_user_entreprise','2026-03-22 04:24:56.182264'),(42,'users','0005_remove_user_entreprise','2026-03-22 04:24:58.404492'),(43,'stock','0008_detailmouvementcaisse_typecaisse_and_more','2026-04-13 08:33:25.892544'),(44,'stock','0009_article_fulltext_search','2026-04-13 08:33:28.285204'),(45,'stock','0010_ensure_mysql_article_fulltext','2026-04-13 08:33:28.477124'),(46,'stock','0011_client_search_indexes','2026-04-13 08:33:30.735934'),(47,'stock','0012_ensure_mysql_client_fulltext','2026-04-13 08:33:30.913932'),(48,'stock','0013_sortie_rename_libelle_to_motif','2026-04-13 08:33:32.157759'),(49,'stock','0014_mouvementcaisse_motif_moyen_remove_categorie','2026-04-13 08:33:33.638800'),(50,'stock','0015_ensure_mouvementcaisse_content_type_fields','2026-04-13 08:33:33.825160'),(51,'stock','0016_retry_ensure_mouvementcaisse_content_type','2026-04-13 08:33:34.056383'),(52,'stock','0017_fournisseur','2026-04-13 08:33:37.653460'),(53,'stock','0018_fournisseur_code_blank','2026-04-13 08:33:37.726680'),(54,'order','0001_initial','2026-04-13 08:33:48.746171'),(55,'order','0002_lot_fournisseur_model','2026-04-13 08:33:51.054237'),(56,'order','0003_rename_order_fraislots_entreprise_lot_type_frais_idx_order_frais_entrepr_cf6b25_idx_and_more','2026-04-13 08:33:52.188305'),(57,'order','0004_fournisseur_in_order_app','2026-04-13 08:33:57.205740'),(58,'stock','0019_remove_fournisseur_from_stock','2026-04-13 08:33:57.669022'),(59,'stock','0020_client_password','2026-04-13 08:34:05.160288'),(60,'stock','0021_client_entreprise_m2m','2026-04-13 08:34:33.477930'),(61,'stock','0022_alter_mouvementcaisse_motif_and_more','2026-04-13 08:34:34.349650'),(62,'order','0005_commande_commandeitem_commanderesponse','2026-04-13 08:34:54.916529'),(63,'order','0006_rename_order_commande_entreprise_client_statut_idx_order_comma_entrepr_c8fef6_idx_and_more','2026-04-13 08:34:57.838086'),(64,'order','0007_lot_closure_stock_fields','2026-04-13 08:35:01.053124'),(65,'order','0008_commande_nom','2026-04-13 08:35:04.630813'),(66,'order','0009_clear_entree_description_lot_closure','2026-04-13 08:35:04.979543'),(67,'order','0010_commande_sortie_livraison','2026-04-13 08:35:07.422064'),(68,'users','0006_alter_user_role','2026-04-13 08:35:07.539122'),(69,'order','0011_decimal_item_quantities','2026-04-29 07:12:26.145781'),(70,'stock','0023_decimal_quantities','2026-04-29 07:12:39.612936');
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
INSERT INTO `django_session` VALUES ('bzix65mt6201k0h6frrq5mk2m4tisc4g','.eJxVjDsOwyAQRO9CHSHDgoGU6X0GtMsnOIlAMnYV5e6xJRdJNdK8N_NmHre1-K2nxc-RXRmwy29HGJ6pHiA-sN4bD62uy0z8UPhJO59aTK_b6f4dFOxlX4dsiCIkO4zCJSMwgEouAypF1jorUJOxysEewlkpKQtwetBGyzhGYp8v5o03Ww:1wHzJu:NBfaPyaZcl8bkBQdBitLIPngB_yU8qiSTrCKOc7eCfc','2026-05-13 07:26:54.933197'),('wfi11vrmuuvg49rw884f1wm8vwsqghxj','.eJxVjDsOwyAQRO9CHSHDgoGU6X0GtMsnOIlAMnYV5e6xJRdJNdK8N_NmHre1-K2nxc-RXRmwy29HGJ6pHiA-sN4bD62uy0z8UPhJO59aTK_b6f4dFOxlX4dsiCIkO4zCJSMwgEouAypF1jorUJOxysEewlkpKQtwetBGyzhGYp8v5o03Ww:1wDfDc:l5V3r0xeL5gY4q2TNpIzKIJ0j41jA3oIdZVcOexyvDA','2026-05-01 09:10:32.303269');
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_commande`
--

DROP TABLE IF EXISTS `order_commande`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_commande` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `statut` varchar(20) NOT NULL,
  `reference` varchar(40) NOT NULL,
  `note_client` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `client_id` varchar(20) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  `succursale_id` bigint DEFAULT NULL,
  `nom` varchar(255) NOT NULL,
  `sortie_livraison_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `sortie_livraison_id` (`sortie_livraison_id`),
  KEY `order_comma_entrepr_c8fef6_idx` (`entreprise_id`,`client_id`,`statut`),
  KEY `order_comma_entrepr_6475a3_idx` (`entreprise_id`,`created_at`),
  KEY `order_comma_entrepr_a22c06_idx` (`entreprise_id`,`statut`,`created_at`),
  KEY `order_commande_client_id_ba860c8c_fk_stock_client_id` (`client_id`),
  KEY `order_commande_succursale_id_88314c52_fk_stock_succursale_id` (`succursale_id`),
  KEY `order_commande_statut_a9c58a8f` (`statut`),
  KEY `order_commande_reference_332add3f` (`reference`),
  CONSTRAINT `order_commande_client_id_ba860c8c_fk_stock_client_id` FOREIGN KEY (`client_id`) REFERENCES `stock_client` (`id`),
  CONSTRAINT `order_commande_entreprise_id_c64012b2_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `order_commande_sortie_livraison_id_39d9d34a_fk_stock_sortie_id` FOREIGN KEY (`sortie_livraison_id`) REFERENCES `stock_sortie` (`id`),
  CONSTRAINT `order_commande_succursale_id_88314c52_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_commande`
--

LOCK TABLES `order_commande` WRITE;
/*!40000 ALTER TABLE `order_commande` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_commande` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_commandeitem`
--

DROP TABLE IF EXISTS `order_commandeitem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_commandeitem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nom_article` varchar(255) NOT NULL,
  `quantite` decimal(12,3) NOT NULL,
  `article_id` varchar(10) DEFAULT NULL,
  `commande_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `order_comma_command_1a29b4_idx` (`commande_id`,`article_id`),
  KEY `order_commandeitem_article_id_0f6c6bb5_fk_stock_art` (`article_id`),
  CONSTRAINT `order_commandeitem_article_id_0f6c6bb5_fk_stock_art` FOREIGN KEY (`article_id`) REFERENCES `stock_article` (`article_id`),
  CONSTRAINT `order_commandeitem_commande_id_b849b712_fk_order_commande_id` FOREIGN KEY (`commande_id`) REFERENCES `order_commande` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_commandeitem`
--

LOCK TABLES `order_commandeitem` WRITE;
/*!40000 ALTER TABLE `order_commandeitem` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_commandeitem` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_commanderesponse`
--

DROP TABLE IF EXISTS `order_commanderesponse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_commanderesponse` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `commentaire` longtext NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `auteur_id` bigint DEFAULT NULL,
  `commande_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `order_comma_command_b24409_idx` (`commande_id`,`created_at`),
  KEY `order_commanderesponse_auteur_id_0290614a_fk_users_user_id` (`auteur_id`),
  CONSTRAINT `order_commanderesponse_auteur_id_0290614a_fk_users_user_id` FOREIGN KEY (`auteur_id`) REFERENCES `users_user` (`id`),
  CONSTRAINT `order_commanderesponse_commande_id_1a915c2e_fk_order_commande_id` FOREIGN KEY (`commande_id`) REFERENCES `order_commande` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_commanderesponse`
--

LOCK TABLES `order_commanderesponse` WRITE;
/*!40000 ALTER TABLE `order_commanderesponse` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_commanderesponse` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_fournisseur`
--

DROP TABLE IF EXISTS `order_fournisseur`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_fournisseur` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `code` varchar(40) NOT NULL,
  `nom` varchar(255) NOT NULL,
  `telephone` varchar(50) DEFAULT NULL,
  `email` varchar(254) DEFAULT NULL,
  `adresse` varchar(255) DEFAULT NULL,
  `ville` varchar(100) DEFAULT NULL,
  `pays` varchar(100) DEFAULT NULL,
  `nif` varchar(100) DEFAULT NULL,
  `notes` longtext NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_fournisseur_entreprise_id_code_4667e914_uniq` (`entreprise_id`,`code`),
  KEY `order_fourn_entrepr_40c3fc_idx` (`entreprise_id`,`nom`),
  KEY `order_fourn_entrepr_7944ce_idx` (`entreprise_id`,`is_active`),
  KEY `order_fourn_entrepr_464367_idx` (`entreprise_id`,`code`),
  KEY `order_fourn_entrepr_e4f51b_idx` (`entreprise_id`,`created_at`),
  KEY `order_fournisseur_succursale_id_9c1ba567_fk_stock_succursale_id` (`succursale_id`),
  CONSTRAINT `order_fournisseur_entreprise_id_15ed5ffb_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `order_fournisseur_succursale_id_9c1ba567_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_fournisseur`
--

LOCK TABLES `order_fournisseur` WRITE;
/*!40000 ALTER TABLE `order_fournisseur` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_fournisseur` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_fraislot`
--

DROP TABLE IF EXISTS `order_fraislot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_fraislot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `type_frais` varchar(20) NOT NULL,
  `montant` decimal(14,2) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  `succursale_id` bigint DEFAULT NULL,
  `lot_id` bigint NOT NULL,
  `devise_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `order_fraislot_succursale_id_aa81b987_fk_stock_succursale_id` (`succursale_id`),
  KEY `order_fraislot_lot_id_63c576e1_fk_order_lot_id` (`lot_id`),
  KEY `order_fraislot_devise_id_0a5e8ec8_fk_stock_devise_id` (`devise_id`),
  KEY `order_frais_entrepr_cf6b25_idx` (`entreprise_id`,`lot_id`,`type_frais`),
  CONSTRAINT `order_fraislot_devise_id_0a5e8ec8_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `order_fraislot_entreprise_id_b8ab12c3_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `order_fraislot_lot_id_63c576e1_fk_order_lot_id` FOREIGN KEY (`lot_id`) REFERENCES `order_lot` (`id`),
  CONSTRAINT `order_fraislot_succursale_id_aa81b987_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_fraislot`
--

LOCK TABLES `order_fraislot` WRITE;
/*!40000 ALTER TABLE `order_fraislot` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_fraislot` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_lot`
--

DROP TABLE IF EXISTS `order_lot`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_lot` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `reference` varchar(30) NOT NULL,
  `date_expedition` date NOT NULL,
  `date_arrivee_prevue` date DEFAULT NULL,
  `statut` varchar(20) NOT NULL,
  `date_cloture` date DEFAULT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  `succursale_id` bigint DEFAULT NULL,
  `fournisseur_id` bigint DEFAULT NULL,
  `entree_stock_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_lot_entreprise_id_reference_9ff88830_uniq` (`entreprise_id`,`reference`),
  KEY `order_lot_succursale_id_44716409_fk_stock_succursale_id` (`succursale_id`),
  KEY `order_lot_entrepr_b05243_idx` (`entreprise_id`,`statut`),
  KEY `order_lot_entrepr_986a9c_idx` (`entreprise_id`),
  KEY `order_lot_entrepr_3fc7fe_idx` (`entreprise_id`,`date_expedition`),
  KEY `order_lot_fournisseur_id_ffdd4543_fk_order_fournisseur_id` (`fournisseur_id`),
  KEY `order_lot_entree_stock_id_630952ce_fk_stock_entree_id` (`entree_stock_id`),
  CONSTRAINT `order_lot_entree_stock_id_630952ce_fk_stock_entree_id` FOREIGN KEY (`entree_stock_id`) REFERENCES `stock_entree` (`id`),
  CONSTRAINT `order_lot_entreprise_id_204fee8d_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `order_lot_fournisseur_id_ffdd4543_fk_order_fournisseur_id` FOREIGN KEY (`fournisseur_id`) REFERENCES `order_fournisseur` (`id`),
  CONSTRAINT `order_lot_succursale_id_44716409_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_lot`
--

LOCK TABLES `order_lot` WRITE;
/*!40000 ALTER TABLE `order_lot` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_lot` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `order_lotitem`
--

DROP TABLE IF EXISTS `order_lotitem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `order_lotitem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `quantite` decimal(12,3) NOT NULL,
  `prix_achat_unitaire` decimal(14,2) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `updated_at` datetime(6) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  `succursale_id` bigint DEFAULT NULL,
  `lot_id` bigint NOT NULL,
  `article_id` varchar(10) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `order_lotitem_lot_id_article_id_bdeedd77_uniq` (`lot_id`,`article_id`),
  KEY `order_lotitem_succursale_id_53d14fef_fk_stock_succursale_id` (`succursale_id`),
  KEY `order_lotitem_article_id_27fb4a7d_fk_stock_article_article_id` (`article_id`),
  KEY `order_lotit_entrepr_76e0c5_idx` (`entreprise_id`,`lot_id`,`article_id`),
  CONSTRAINT `order_lotitem_article_id_27fb4a7d_fk_stock_article_article_id` FOREIGN KEY (`article_id`) REFERENCES `stock_article` (`article_id`),
  CONSTRAINT `order_lotitem_entreprise_id_b6029aad_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `order_lotitem_lot_id_5d5af2c8_fk_order_lot_id` FOREIGN KEY (`lot_id`) REFERENCES `order_lot` (`id`),
  CONSTRAINT `order_lotitem_succursale_id_53d14fef_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `order_lotitem`
--

LOCK TABLES `order_lotitem` WRITE;
/*!40000 ALTER TABLE `order_lotitem` DISABLE KEYS */;
/*!40000 ALTER TABLE `order_lotitem` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_article`
--

DROP TABLE IF EXISTS `stock_article`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_article` (
  `nom_scientifique` varchar(100) NOT NULL,
  `nom_commercial` varchar(100) DEFAULT NULL,
  `article_id` varchar(10) NOT NULL,
  `emplacement` varchar(200) NOT NULL,
  `sous_type_article_id` bigint NOT NULL,
  `unite_id` bigint NOT NULL,
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`article_id`),
  KEY `stock_article_sous_type_article_id_d6c5b908_fk_stock_sou` (`sous_type_article_id`),
  KEY `stock_article_unite_id_d69fcfbd_fk_stock_unite_id` (`unite_id`),
  KEY `stock_artic_entrepr_3aa35b_idx` (`entreprise_id`),
  KEY `stock_artic_succurs_93f236_idx` (`succursale_id`),
  KEY `stock_artic_entrepr_92b06b_idx` (`entreprise_id`,`succursale_id`),
  FULLTEXT KEY `ft_article_search` (`nom_scientifique`,`nom_commercial`,`article_id`),
  CONSTRAINT `stock_article_entreprise_id_dd5bf6eb_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_article_sous_type_article_id_d6c5b908_fk_stock_sou` FOREIGN KEY (`sous_type_article_id`) REFERENCES `stock_soustypearticle` (`id`),
  CONSTRAINT `stock_article_succursale_id_6481df5a_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`),
  CONSTRAINT `stock_article_unite_id_d69fcfbd_fk_stock_unite_id` FOREIGN KEY (`unite_id`) REFERENCES `stock_unite` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_article`
--

LOCK TABLES `stock_article` WRITE;
/*!40000 ALTER TABLE `stock_article` DISABLE KEYS */;
INSERT INTO `stock_article` VALUES ('Cadenat MF',NULL,'ARCA0001','1',40,3,1,NULL),('Cadenat PF',NULL,'ARCA0002','1',40,3,1,NULL),('Colle elephant',NULL,'ARCO0001','1',45,3,1,NULL),('Colle liquide',NULL,'ARCO0002','1',45,3,1,NULL),('Colle liquide office',NULL,'ARCO0003','1',45,3,1,NULL),('isolent',NULL,'ARCO0004','1',45,3,1,NULL),('super glue',NULL,'ARCO0005','1',45,3,1,NULL),('tresolente/scotch GF',NULL,'ARCO0006','1',45,3,1,NULL),('tresolente/scotch MF',NULL,'ARCO0007','1',45,3,1,NULL),('tresolente/scotch PF',NULL,'ARCO0008','1',45,3,1,NULL),('Cadenat GF',NULL,'ARCO0009','1',45,3,1,NULL),('Gratoire GF',NULL,'ARCO0010','1',55,3,1,NULL),('Gratoire PF',NULL,'ARCO0011','1',55,3,1,NULL),('Fil a coudre',NULL,'ARCO0012','1',45,3,1,NULL),('Aiguille',NULL,'ARCO0013','1',49,3,1,NULL),('Ciseau',NULL,'ARCO0014','1',49,3,1,NULL),('Coup ongle',NULL,'ARDI0001','1',55,3,1,NULL),('Peignet tige',NULL,'ARDI0002','1',55,3,1,NULL),('Pélouse synthétique',NULL,'ARDI0003','1',55,3,1,NULL),('porte clé',NULL,'ARDI0004','1',55,3,1,NULL),('Porte mine',NULL,'ARDI0005','1',55,3,1,NULL),('Post it',NULL,'ARDI0006','1',55,3,1,NULL),('Agenda 25k GF',NULL,'FOAG0001','1',41,3,1,NULL),('Agenda A6 PF',NULL,'FOAG0002','1',41,3,1,NULL),('Agraphe kangaro 24/6',NULL,'FOAG0003','1',6,12,1,NULL),('Agrapheuse métallique',NULL,'FOAG0004','1',6,3,1,NULL),('Cahier calligraphie',NULL,'FOCA0001','1',1,3,1,NULL),('Cahier dessin',NULL,'FOCA0002','1',1,3,1,NULL),('Cahier ligné simple',NULL,'FOCA0003','1',1,3,1,NULL),('Cahier ligné 200 pages',NULL,'FOCA0004','1',1,3,1,NULL),('Cahier ligné 96 pages',NULL,'FOCA0005','1',1,3,1,NULL),('Cahier minustre GF',NULL,'FOCA0006','1',1,3,1,NULL),('Cahier minustre PF',NULL,'FOCA0007','1',1,3,1,NULL),('Cahier minustre A7',NULL,'FOCA0008','1',1,3,1,NULL),('Cahier quadrillé 200pages',NULL,'FOCA0009','1',1,3,1,NULL),('cahier quadrille 32 pages',NULL,'FOCA0010','1',1,3,1,NULL),('cahier quadrillé 96 pages',NULL,'FOCA0011','1',1,3,1,NULL),('Papier carbone',NULL,'FOCA0012','1',1,3,1,NULL),('crayon',NULL,'FOCA0013','1',1,3,1,NULL),('crayon couleur',NULL,'FOCA0014','1',1,3,1,NULL),('journal de classe',NULL,'FOCA0015','1',1,3,1,NULL),('Journaux',NULL,'FOCA0016','1',1,3,1,NULL),('Latte',NULL,'FOCA0017','1',1,3,1,NULL),('Machine scientifique',NULL,'FOCA0018','1',1,3,1,NULL),('note book',NULL,'FOCA0019','1',1,3,1,NULL),('perforateur',NULL,'FOCA0020','1',1,3,1,NULL),('stylon  bleu',NULL,'FOCA0021','1',1,3,1,NULL),('stylon rouge',NULL,'FOCA0022','1',1,3,1,NULL),('stylon noir',NULL,'FOCA0023','1',1,3,1,NULL),('tableau periodique',NULL,'FOCA0024','1',1,3,1,NULL),('Papier Maquette',NULL,'FOCA0026','1',1,3,1,NULL),('Papier bristole A1',NULL,'FOCA0027','1',1,3,1,NULL),('Ecritoire',NULL,'FOCA0028','1',1,3,1,NULL),('Boite d\'instrument',NULL,'FOCL0001','1',4,12,1,NULL),('Classeur',NULL,'FOCL0002','1',34,3,1,NULL),('Couteau maquette GF',NULL,'FODI0001','1',57,3,1,NULL),('Couteau maquette PF',NULL,'FODI0002','1',57,3,1,NULL),('encre correctrice',NULL,'FOEN0001','1',36,3,1,NULL),('Envellope sac A3',NULL,'FOEN0002','1',5,3,1,NULL),('Enveloppe ordinaire',NULL,'FOEN0003','1',5,3,1,NULL),('Enveloppe sac A4',NULL,'FOEN0004','1',5,3,1,NULL),('sac vide PF',NULL,'FOEN0005','1',5,3,1,NULL),('Sac vie GF (trompone)',NULL,'FOEN0006','1',5,3,1,NULL),('sachet noir #15',NULL,'FOEN0007','1',63,3,1,NULL),('sachet vert',NULL,'FOEN0008','1',5,3,1,NULL),('farde a plastic',NULL,'FOFA0001','1',35,3,1,NULL),('farde a traingle',NULL,'FOFA0002','1',35,3,1,NULL),('Bic marker Permanent',NULL,'FOMA0001','1',37,3,1,NULL),('Bic marker tableau blanc',NULL,'FOMA0002','1',37,3,1,NULL),('Bic Souligneur',NULL,'FOMA0003','1',37,3,1,NULL),('Envelloppe Chequier',NULL,'FOMA0004','1',37,3,1,NULL),('papier bristol A1',NULL,'FOPA0001','1',3,3,1,NULL),('Papier Bristol A4',NULL,'FOPA0002','1',3,3,1,NULL),('papier calque A3',NULL,'FOPA0003','1',3,3,1,NULL),('papier calque (roulon)',NULL,'FOPA0004','1',3,3,1,NULL),('papier A4',NULL,'FOPA0005','1',3,3,1,NULL),('papier maquette',NULL,'FOPA0006','1',3,3,1,NULL),('papier milimetrer A1',NULL,'FOPA0007','1',3,3,1,NULL),('Papier Milimétré A3',NULL,'FOPA0008','1',3,3,1,NULL),('Papier millimétré A4',NULL,'FOPA0009','1',3,3,1,NULL),('papier vitré',NULL,'FOPA0010','1',3,3,1,NULL),('Papier A4 detaille',NULL,'FOPA0011','1',3,3,1,NULL),('Ardoise',NULL,'FOST0001','1',2,1,1,NULL),('Bic compo 0,5mm Tip Top',NULL,'FOST0002','1',2,3,1,NULL),('Bic compo 0,5mm uni',NULL,'FOST0003','1',2,3,1,NULL),('Gome GF',NULL,'FOST0004','1',2,3,1,NULL),('gome PF',NULL,'FOST0005','1',2,3,1,NULL),('calculatrice',NULL,'FOST0006','1',2,3,1,NULL),('mine',NULL,'FOST0007','1',2,3,1,NULL),('Badge lux',NULL,'FOST0008','1',2,3,1,NULL),('Badge ordinaire',NULL,'FOST0009','1',2,3,1,NULL),('Bic Rasoire',NULL,'FOST0010','1',2,3,1,NULL),('Touche',NULL,'FOST0011','1',2,3,1,NULL),('chossete Gucci',NULL,'HACH0001','1',25,3,1,NULL),('chossete perpette',NULL,'HACH0002','1',25,3,1,NULL),('chossete Versace',NULL,'HACH0003','1',25,3,1,NULL),('chossete Homme',NULL,'HACH0004','1',25,3,1,NULL),('chaussete Longue',NULL,'HACH0005','1',25,3,1,NULL),('Chaussette Homme',NULL,'HACH0006','1',25,3,1,NULL),('Chaussette Perpette',NULL,'HACH0007','1',25,3,1,NULL),('Chaussette Versace',NULL,'HACH0008','1',25,3,1,NULL),('Chaussette Ferlando',NULL,'HACH0009','1',25,3,1,NULL),('Chemise Cavana',NULL,'HACH0010','1',38,3,1,NULL),('Chemise kotommele',NULL,'HACH0011','1',38,3,1,NULL),('Cirage liquide palc',NULL,'HADI0001','1',53,3,1,NULL),('Cirage liquide wolf',NULL,'HADI0002','1',53,3,1,NULL),('Pagne Petit olande',NULL,'HAPA0001','1',33,3,1,NULL),('Pagne wax vasco',NULL,'HAPA0002','1',33,3,1,NULL),('Pagne wax nouveau',NULL,'HAPA0003','1',33,3,1,NULL),('Pagne Wax Vilisco (Petit Super)',NULL,'HAPA0004','1',33,3,1,NULL),('Pagne dorcas',NULL,'HAPA0005','1',33,3,1,NULL),('Pagne I will go',NULL,'HAPA0006','1',33,3,1,NULL),('Pagne Mifem',NULL,'HAPA0007','1',33,3,1,NULL),('Cycliste femme long',NULL,'HASI0001','1',39,3,1,NULL),('singlet diana rose',NULL,'HASI0002','1',39,3,1,NULL),('singlet fille  fammy',NULL,'HASI0003','1',39,3,1,NULL),('singlet fille lux',NULL,'HASI0004','1',39,3,1,NULL),('singlet littlevictan(enfant)',NULL,'HASI0005','1',39,3,1,NULL),('singlet homme',NULL,'HASI0006','1',39,3,1,NULL),('Cycliste femme court',NULL,'HASO0001','1',24,3,1,NULL),('Sous vetement coton',NULL,'HASO0002','1',24,3,1,NULL),('sous-vetement jeune garçon',NULL,'HASO0003','1',24,3,1,NULL),('sous-vetement enfant(mixte)',NULL,'HASO0004','1',24,3,1,NULL),('sous-vetement de lux',NULL,'HASO0005','1',24,3,1,NULL),('sous-vetement homme',NULL,'HASO0006','1',24,3,1,NULL),('soutien gorge simple',NULL,'HASO0007','1',24,3,1,NULL),('soutien gorge de lux',NULL,'HASO0008','1',24,3,1,NULL),('Culotte Home',NULL,'HASO0009','1',24,3,1,NULL),('Babouche umoja',NULL,'HASO0010','1',50,3,1,NULL),('soulier classique',NULL,'HASO0011','1',50,3,1,NULL),('sous vetement sexy vilya',NULL,'HASO0012','1',24,3,1,NULL),('Tige coton',NULL,'NEDI0001','1',59,4,1,NULL),('Vim Gf',NULL,'NENE0001','1',47,3,1,NULL),('Blueband 100g',NULL,'PRBE0001','1',51,3,1,NULL),('Blueband 250g',NULL,'PRBE0002','1',51,12,1,NULL),('Blueband 500gr',NULL,'PRBE0003','1',51,12,1,NULL),('Bazoka bigg boss',NULL,'PRBI0001','1',9,3,1,NULL),('Biscuit BORA',NULL,'PRBI0002','1',9,4,1,NULL),('Biscuit chocolat PF',NULL,'PRBI0003','1',9,4,1,NULL),('Biscuit chocolat yum GF',NULL,'PRBI0004','1',9,4,1,NULL),('Biscuit cremica',NULL,'PRBI0005','1',9,4,1,NULL),('Biscuit FOOT',NULL,'PRBI0006','1',9,4,1,NULL),('Biscuit max',NULL,'PRBI0007','1',9,4,1,NULL),('Biscuit MILK PLUS',NULL,'PRBI0008','1',9,4,1,NULL),('Biscuit SOJA',NULL,'PRBI0009','1',9,4,1,NULL),('Bombon sifle',NULL,'PRBI0010','1',9,3,1,NULL),('Bombon hewa',NULL,'PRBI0011','1',9,3,1,NULL),('Bombon Tropical Milk','Bombon ivori','PRBI0012','1',9,3,1,NULL),('Bombon ordinaire',NULL,'PRBI0013','1',9,3,1,NULL),('Biscuit starBix 50g',NULL,'PRBI0014','1',9,9,1,NULL),('Bible louis segond',NULL,'PRBI0015','1',27,3,1,NULL),('Biblia kitabu cha mungu',NULL,'PRBI0016','1',27,3,1,NULL),('Biblia petit format',NULL,'PRBI0017','1',27,3,1,NULL),('Biscuit Parle-je','Biscuit sawa glucose','PRBI0018','1',9,3,1,NULL),('Biscuit TikTok','Biscuit TikTok','PRBI0019','1',9,3,1,NULL),('Biscuit Starbix 100g','Biscuit Starbix 100g','PRBI0020','1',9,9,1,NULL),('bonbon Mintol','Mintol','PRBI0021','1',9,3,1,NULL),('eau tamu 1000ml',NULL,'PRBO0001','1',11,3,1,NULL),('eau tamu 1500ml',NULL,'PRBO0002','1',11,3,1,NULL),('eau tamu 330ml',NULL,'PRBO0003','1',11,3,1,NULL),('eau tamu 550ml',NULL,'PRBO0004','1',11,3,1,NULL),('Jus afya',NULL,'PRBO0005','1',11,3,1,NULL),('jus embe GF',NULL,'PRBO0006','1',11,3,1,NULL),('jus embe PF',NULL,'PRBO0007','1',11,3,1,NULL),('jus fanta 330ml',NULL,'PRBO0008','1',11,3,1,NULL),('Jus mango',NULL,'PRBO0009','1',11,3,1,NULL),('jus naturel',NULL,'PRBO0010','1',11,3,1,NULL),('jus mirinda 2L',NULL,'PRBO0011','1',11,3,1,NULL),('jus mirinda 330ml',NULL,'PRBO0012','1',11,3,1,NULL),('jus rafiki 1l',NULL,'PRBO0013','1',11,3,1,NULL),('jus apple',NULL,'PRBO0014','1',11,3,1,NULL),('jus oner PF',NULL,'PRBO0015','1',11,3,1,NULL),('jus oner GF',NULL,'PRBO0016','1',11,3,1,NULL),('Jus novida 330ml',NULL,'PRBO0017','1',11,3,1,NULL),('jus novida GF',NULL,'PRBO0018','1',11,3,1,NULL),('sucre djino',NULL,'PRBO0020','1',11,2,1,NULL),('Jus a carton 330 ml',NULL,'PRBO0021','1',11,3,1,NULL),('jus a onerya 330 ml',NULL,'PRBO0022','1',11,3,1,NULL),('Jus Fanta 2l',NULL,'PRBO0023','1',11,3,1,NULL),('Jus gofrut 1l',NULL,'PRBO0024','1',11,3,1,NULL),('Jus oner 200ml','Jus Oner 200ml','PRBO0025','1',11,3,1,NULL),('Allumetes (waceshu)',NULL,'PRCO0001','1',15,4,1,NULL),('Allumetes PF',NULL,'PRCO0002','1',15,4,1,NULL),('Allumetes GF',NULL,'PRCO0003','1',15,4,1,NULL),('Lunch box Alminium GF',NULL,'PRCO0004','1',15,3,1,NULL),('Lunch box Alminium PF',NULL,'PRCO0005','1',15,3,1,NULL),('Lunch box Plastique',NULL,'PRCO0006','1',15,3,1,NULL),('Verre a usage unique PF',NULL,'PRCO0007','1',15,3,1,NULL),('Verre a usage unique GF',NULL,'PRCO0008','1',15,3,1,NULL),('Sissette',NULL,'PRCO0009','1',15,3,1,NULL),('creme top claire',NULL,'PRCR0001','1',18,3,1,NULL),('Creme Cocopulp',NULL,'PRCR0002','1',18,3,1,NULL),('creme budchou 300ml',NULL,'PRCR0003','1',18,3,1,NULL),('creme cocowhite 250ml',NULL,'PRCR0004','1',18,3,1,NULL),('creme cocowhite PF',NULL,'PRCR0005','1',18,3,1,NULL),('creme  cocoa',NULL,'PRCR0006','1',18,3,1,NULL),('creme  top lemon',NULL,'PRCR0007','1',18,3,1,NULL),('creme day by day 400ml',NULL,'PRCR0008','1',18,3,1,NULL),('creme day by day MF',NULL,'PRCR0009','1',18,3,1,NULL),('creme day by day 100ml',NULL,'PRCR0010','1',18,3,1,NULL),('creme nevia 70g',NULL,'PRCR0011','1',18,3,1,NULL),('creme silver GF',NULL,'PRCR0012','1',18,3,1,NULL),('creme silver PF',NULL,'PRCR0013','1',18,3,1,NULL),('creme skala aloe',NULL,'PRCR0014','1',18,3,1,NULL),('creme top lemon GF',NULL,'PRCR0015','1',18,3,1,NULL),('creme paw paw',NULL,'PRCR0016','1',18,3,1,NULL),('creme top line',NULL,'PRCR0017','1',18,3,1,NULL),('Lotion Amara for men',NULL,'PRCR0018','1',18,3,1,NULL),('Lotion skala homme',NULL,'PRCR0020','1',18,3,1,NULL),('Lotion rapide claire',NULL,'PRCR0021','1',18,3,1,NULL),('Lotion White express',NULL,'PRCR0022','1',18,3,1,NULL),('Lotion Revlo',NULL,'PRCR0023','1',18,3,1,NULL),('Lotion vestline',NULL,'PRCR0024','1',18,3,1,NULL),('creme boudchou GF 300ml',NULL,'PRCR0025','1',18,3,1,NULL),('Brosse a dent',NULL,'PRDE0001','1',17,3,1,NULL),('Brossse de toilette',NULL,'PRDE0002','1',17,3,1,NULL),('Brossse de Cuisine',NULL,'PRDE0003','1',17,3,1,NULL),('cure dent',NULL,'PRDE0004','1',54,3,1,NULL),('Dentifrice aloe',NULL,'PRDE0005','1',17,3,1,NULL),('Dentifrice colgate',NULL,'PRDE0006','1',17,3,1,NULL),('Dentifrice fresh up',NULL,'PRDE0007','1',17,3,1,NULL),('Dentifrice flodent',NULL,'PRDE0008','1',17,3,1,NULL),('Bross à dent Paris 51','Bross à dent','PRDE0009','1',17,3,1,NULL),('Bross à dent VIP Coco Doctor',NULL,'PRDE0010','1',17,3,1,NULL),('Bluetooth air pord',NULL,'PRDI0001','1',32,3,1,NULL),('Cable USB court',NULL,'PRDI0002','1',32,3,1,NULL),('Cable USB fantome court',NULL,'PRDI0003','1',32,3,1,NULL),('Cable USB fantome long',NULL,'PRDI0004','1',32,3,1,NULL),('Cable USB long',NULL,'PRDI0005','1',32,3,1,NULL),('chargeur AD',NULL,'PRDI0006','1',32,3,1,NULL),('chargeur 2.5 A',NULL,'PRDI0007','1',32,3,1,NULL),('chargeur Faster',NULL,'PRDI0008','1',32,3,1,NULL),('fil boul (TIF-TAQ)',NULL,'PRDI0009','1',32,3,1,NULL),('fil mahine a coudre',NULL,'PRDI0010','1',32,3,1,NULL),('ralonge',NULL,'PRDI0011','1',32,3,1,NULL),('ralonge safety',NULL,'PRDI0012','1',32,3,1,NULL),('Cable USB Iphone',NULL,'PRDI0013','1',32,3,1,NULL),('Cissete',NULL,'PRDI0014','1',54,4,1,NULL),('Couteau GF',NULL,'PRDI0015','1',56,3,1,NULL),('Couteau PF',NULL,'PRDI0016','1',56,3,1,NULL),('Parapluie GF',NULL,'PRDI0017','1',63,3,1,NULL),('Parapluie PF',NULL,'PRDI0018','1',63,3,1,NULL),('sachet noir #22',NULL,'PRDI0019','1',63,3,1,NULL),('emballage cadeau sac',NULL,'PREM0001','1',44,3,1,NULL),('emballage cadeau simple',NULL,'PREM0002','1',44,3,1,NULL),('emballage decalot',NULL,'PREM0003','1',44,3,1,NULL),('emballage sac',NULL,'PREM0004','1',44,3,1,NULL),('emballage sac (cavera)',NULL,'PREM0005','1',44,3,1,NULL),('emballage vert',NULL,'PREM0006','1',44,3,1,NULL),('Bouquet de fleur luxe',NULL,'PRFL0001','1',43,3,1,NULL),('Bouquet de fleur MF',NULL,'PRFL0002','1',43,3,1,NULL),('Bouquet de fleur PF',NULL,'PRFL0003','1',43,3,1,NULL),('Fleur couronne',NULL,'PRFL0004','1',43,3,1,NULL),('Fleur a gateau',NULL,'PRFL0005','1',43,12,1,NULL),('Fleur maquette',NULL,'PRFL0006','1',43,3,1,NULL),('Pomme',NULL,'PRFR0001','1',64,3,1,NULL),('glycerine botion',NULL,'PRGL0001','1',20,3,1,NULL),('glycerine carotte',NULL,'PRGL0002','1',20,3,1,NULL),('glycerine day by day',NULL,'PRGL0003','1',20,3,1,NULL),('glycerine Enfant et adulte',NULL,'PRGL0004','1',20,3,1,NULL),('glycerine kris 100ml',NULL,'PRGL0005','1',20,3,1,NULL),('glycerine movit',NULL,'PRGL0006','1',20,3,1,NULL),('glycerine pop GF',NULL,'PRGL0007','1',20,3,1,NULL),('glycerine pop PF',NULL,'PRGL0008','1',20,3,1,NULL),('glycerine pure medical',NULL,'PRGL0009','1',20,3,1,NULL),('glycerine skala',NULL,'PRGL0010','1',20,3,1,NULL),('glycerine suzana PF',NULL,'PRGL0011','1',20,3,1,NULL),('glycerine suzana 125g',NULL,'PRGL0012','1',20,3,1,NULL),('Glycerine Naomie',NULL,'PRGL0013','1',20,3,1,NULL),('Suzana',NULL,'PRGL0014','1',20,3,1,NULL),('Haricot pigeon vert',NULL,'PRHA0001','1',67,2,1,NULL),('Huile Nzuri 3L',NULL,'PRHU0001','1',58,15,1,NULL),('Huile Nzuri 5L',NULL,'PRHU0002','1',58,15,1,NULL),('Huile Olive 250 ml',NULL,'PRHU0003','1',58,7,1,NULL),('Huile Rina 2,5L',NULL,'PRHU0004','1',58,15,1,NULL),('Huile Rina 5l',NULL,'PRHU0005','1',58,15,1,NULL),('Huile Tourne sol 5l',NULL,'PRHU0006','1',58,7,1,NULL),('carte biblique',NULL,'PRLI0001','1',28,3,1,NULL),('Hymne et Louange',NULL,'PRLI0002','1',28,3,1,NULL),('Nyimbo za kristo',NULL,'PRLI0003','1',28,3,1,NULL),('Esyo nyimbo esya kristo',NULL,'PRLI0004','1',28,3,1,NULL),('Holy bible','New King James','PRLI0005','1',28,3,1,NULL),('Holy bible good news',NULL,'PRLI0006','1',28,3,1,NULL),('Bougie gateau',NULL,'PRMA0001','1',12,3,1,NULL),('Chapa mandazi',NULL,'PRMA0002','1',12,3,1,NULL),('colorant gateau',NULL,'PRMA0003','1',12,3,1,NULL),('Farine de Froment Azam',NULL,'PRMA0005','1',12,2,1,NULL),('fourchette',NULL,'PRMA0007','1',12,3,1,NULL),('Icing sugar',NULL,'PRMA0008','1',12,3,1,NULL),('Levure paquet',NULL,'PRMA0009','1',12,9,1,NULL),('Levure Cuillèur',NULL,'PRMA0010','1',12,14,1,NULL),('Lotion Amara for women',NULL,'PRMA0011','1',12,3,1,NULL),('prestige 500g',NULL,'PRMA0012','1',12,3,1,NULL),('prestige 250g',NULL,'PRMA0013','1',12,3,1,NULL),('vanilla liquide',NULL,'PRMA0014','1',12,3,1,NULL),('vanilla ruf',NULL,'PRMA0015','1',12,3,1,NULL),('vinaigre',NULL,'PRMA0016','1',12,3,1,NULL),('vitamine E',NULL,'PRMA0017','1',12,3,1,NULL),('Farine kaunga',NULL,'PRMA0018','1',12,2,1,NULL),('Bicarbonate de soude',NULL,'PRMA0020','1',12,3,1,NULL),('Mayonnaise GF',NULL,'PRMA0021','1',62,12,1,NULL),('Mayonnaise PF',NULL,'PRMA0022','1',62,12,1,NULL),('Sucre',NULL,'PRMA0023','1',12,2,1,NULL),('Attache',NULL,'PRNE0001','1',14,3,1,NULL),('Autocolant',NULL,'PRNE0002','1',14,3,1,NULL),('toss omo 1kg',NULL,'PRNE0003','1',14,3,1,NULL),('toss omo 500gr',NULL,'PRNE0004','1',14,3,1,NULL),('toss omo 5kg',NULL,'PRNE0005','1',14,3,1,NULL),('Raclette',NULL,'PRNE0006','1',14,3,1,NULL),('Balais Luxe',NULL,'PRNE0007','1',14,3,1,NULL),('Bross de lessive PF',NULL,'PRNE0008','1',14,3,1,NULL),('Bross de lessive GF',NULL,'PRNE0009','1',14,3,1,NULL),('Bross de lessive MF',NULL,'PRNE0010','1',14,3,1,NULL),('Bross à soulier',NULL,'PRNE0011','1',14,3,1,NULL),('Bross à WC',NULL,'PRNE0012','1',14,3,1,NULL),('Insectiscuide',NULL,'PRNE0013','1',59,3,1,NULL),('Parapluie à Tirette',NULL,'PRNE0014','1',63,3,1,NULL),('Boulle odora',NULL,'PRNE0015','1',14,3,1,NULL),('Lungette himide facial 7days 30pcs',NULL,'PRNE0016','1',14,3,1,NULL),('Lungette himide baby wips 80pcs',NULL,'PRNE0017','1',14,3,1,NULL),('Lungette himide MF',NULL,'PRNE0018','1',14,3,1,NULL),('Angel face',NULL,'PRPA0001','1',21,4,1,NULL),('Angel troos: soulier',NULL,'PRPA0002','1',21,3,1,NULL),('Cache nez',NULL,'PRPA0003','1',21,3,1,NULL),('Parfum (deodorant)',NULL,'PRPA0004','1',21,3,1,NULL),('Boule odorant',NULL,'PRPA0005','1',21,3,1,NULL),('parfum (deodorant) for men',NULL,'PRPA0006','1',21,3,1,NULL),('poudre 22 degre',NULL,'PRPA0007','1',21,3,1,NULL),('poudre my love',NULL,'PRPA0008','1',21,3,1,NULL),('poudre passion 25g',NULL,'PRPA0009','1',21,3,1,NULL),('poudre passion 90g',NULL,'PRPA0010','1',21,3,1,NULL),('Macaroni',NULL,'PRPA0011','1',61,9,1,NULL),('Spaguetti',NULL,'PRPA0012','1',61,9,1,NULL),('pile tiger GF',NULL,'PRPI0001','1',31,3,1,NULL),('pile tiger PF',NULL,'PRPI0002','1',31,3,1,NULL),('Pile Touche Toceba',NULL,'PRPI0003','1',31,3,1,NULL),('pile vinnic',NULL,'PRPI0004','1',31,3,1,NULL),('pile electra',NULL,'PRPI0005','1',31,3,1,NULL),('pile tiger',NULL,'PRPI0006','1',31,3,1,NULL),('pile electran GF',NULL,'PRPI0009','1',31,3,1,NULL),('Movit gel',NULL,'PRPO0001','1',19,3,1,NULL),('mycozema',NULL,'PRPO0002','1',19,3,1,NULL),('pommade afrocare GF',NULL,'PRPO0003','1',19,3,1,NULL),('Pommade Afrocare 100g',NULL,'PRPO0004','1',19,3,1,NULL),('pommade amla',NULL,'PRPO0005','1',19,3,1,NULL),('pommade body lux 100g',NULL,'PRPO0006','1',19,3,1,NULL),('pommade familia PF',NULL,'PRPO0007','1',19,3,1,NULL),('pommade movit 200g',NULL,'PRPO0008','1',19,3,1,NULL),('pommade movit 20g',NULL,'PRPO0009','1',19,3,1,NULL),('pommade movit 70g',NULL,'PRPO0010','1',19,3,1,NULL),('Pressol Gel 125g',NULL,'PRPO0011','1',19,3,1,NULL),('pommade presol PF',NULL,'PRPO0013','1',19,3,1,NULL),('pommade radian Hear creme',NULL,'PRPO0014','1',19,3,1,NULL),('pommade radian 200g',NULL,'PRPO0015','1',19,3,1,NULL),('pommade TOP LINE',NULL,'PRPO0016','1',19,3,1,NULL),('pommade skala 100g',NULL,'PRPO0017','1',19,3,1,NULL),('pommade skala 25g',NULL,'PRPO0018','1',19,3,1,NULL),('pommade vestiline PF',NULL,'PRPO0019','1',19,3,1,NULL),('pommade sulfur 8-plus',NULL,'PRPO0020','1',19,3,1,NULL),('pommade boudchu PF 150ml',NULL,'PRPO0021','1',19,3,1,NULL),('pommade baby junior 200g',NULL,'PRPO0022','1',19,3,1,NULL),('pommade baby junior 50g',NULL,'PRPO0023','1',19,3,1,NULL),('pommade baby junior 425g',NULL,'PRPO0024','1',19,3,1,NULL),('pommade vaseline blue 240g',NULL,'PRPO0025','1',19,3,1,NULL),('pommade vaseline 100gr',NULL,'PRPO0026','1',19,3,1,NULL),('pommade sleeping baby',NULL,'PRPO0027','1',19,3,1,NULL),('pommade UB',NULL,'PRPO0028','1',19,3,1,NULL),('vaseline blue seal GF',NULL,'PRPO0029','1',19,3,1,NULL),('vaseline blue seal PF',NULL,'PRPO0030','1',19,3,1,NULL),('vaseline medical GF',NULL,'PRPO0031','1',19,3,1,NULL),('vaseline medical PF',NULL,'PRPO0032','1',19,3,1,NULL),('Pommade Vestline garlic',NULL,'PRPO0033','1',19,3,1,NULL),('Pommade Afro extra',NULL,'PRPO0034','1',19,3,1,NULL),('pommade vest herbal 25g',NULL,'PRPO0035','1',19,3,1,NULL),('Pressol Gel 80g',NULL,'PRPO0036','1',19,3,1,NULL),('Produit defr UB',NULL,'PRPO0037','1',19,3,1,NULL),('Powerbank 30000mA',NULL,'PRPO0038','1',42,3,1,NULL),('Arrachide',NULL,'PRPR0001','1',8,2,1,NULL),('Huile Amla',NULL,'PRPR0002','1',46,3,1,NULL),('lait cowbel sachet',NULL,'PRPR0003','1',10,3,1,NULL),('Lait Jesa',NULL,'PRPR0004','1',10,3,1,NULL),('Lait nido 400g',NULL,'PRPR0005','1',10,12,1,NULL),('lait nido 800g',NULL,'PRPR0006','1',10,12,1,NULL),('Lotoba',NULL,'PRPR0007','1',8,12,1,NULL),('Noircissant',NULL,'PRPR0008','1',46,3,1,NULL),('Œuf(mayayi)',NULL,'PRPR0009','1',8,3,1,NULL),('Poisson',NULL,'PRPR0010','1',7,2,1,NULL),('produit def radiant 250g',NULL,'PRPR0011','1',46,3,1,NULL),('Riz onu',NULL,'PRPR0012','1',7,2,1,NULL),('Riz Ordinaire',NULL,'PRPR0013','1',7,3,1,NULL),('Sel medical GF',NULL,'PRPR0014','1',7,12,1,NULL),('Sel medical PF',NULL,'PRPR0015','1',7,12,1,NULL),('Sel ordinaire',NULL,'PRPR0016','1',7,3,1,NULL),('Cowbel',NULL,'PRPR0017','1',10,2,1,NULL),('cristaux de sel',NULL,'PRPR0018','1',7,9,1,NULL),('Lame de rasoir topaz',NULL,'PRRA0001','1',60,3,1,NULL),('savon fumbact PF 75g',NULL,'PRSA0001','1',16,3,1,NULL),('savon fumbact GF 125g',NULL,'PRSA0002','1',16,3,1,NULL),('savon germol 125g',NULL,'PRSA0003','1',16,3,1,NULL),('savon germol 75g',NULL,'PRSA0004','1',16,3,1,NULL),('savon imperial GF',NULL,'PRSA0005','1',16,3,1,NULL),('savon imperial PF',NULL,'PRSA0006','1',16,3,1,NULL),('savon liquide',NULL,'PRSA0007','1',16,3,1,NULL),('savon medi-soft',NULL,'PRSA0008','1',16,3,1,NULL),('savon monganga',NULL,'PRSA0009','1',16,3,1,NULL),('savon CYNTOL PF 60g',NULL,'PRSA0010','1',16,3,1,NULL),('savon CYNTOL MF125g',NULL,'PRSA0011','1',16,3,1,NULL),('savon CYNTOL GF175 g',NULL,'PRSA0012','1',16,3,1,NULL),('savon saibu',NULL,'PRSA0015','1',16,13,1,NULL),('savon sicovir',NULL,'PRSA0016','1',16,3,1,NULL),('savon lwanzo',NULL,'PRSA0017','1',16,3,1,NULL),('savon salama',NULL,'PRSA0018','1',16,3,1,NULL),('savon pigeon',NULL,'PRSA0019','1',16,3,1,NULL),('savon salama',NULL,'PRSA0020','1',16,3,1,NULL),('sceau plastic',NULL,'PRSA0021','1',16,3,1,NULL),('Sardine anny',NULL,'PRSA0022','1',65,3,1,NULL),('Savon cristal bebe',NULL,'PRSA0023','1',16,3,1,NULL),('savon Cynthol 175g',NULL,'PRSA0024','1',16,3,1,NULL),('savon Cynthol 60g',NULL,'PRSA0025','1',16,3,1,NULL),('papier hygienique',NULL,'PRSE0001','1',22,3,1,NULL),('papier mouchoir Tissus',NULL,'PRSE0002','1',22,3,1,NULL),('papier mouchoir',NULL,'PRSE0003','1',22,3,1,NULL),('papier serviette',NULL,'PRSE0004','1',22,3,1,NULL),('Vim Pf',NULL,'PRSE0005','1',47,3,1,NULL),('Cotex lavable',NULL,'PRSE0006','1',22,3,1,NULL),('Cotex usage unique Diva',NULL,'PRSE0007','1',22,3,1,NULL),('Cotex usage unique Softcare',NULL,'PRSE0008','1',22,3,1,NULL),('Cotex usage unique Naomi',NULL,'PRSE0009','1',22,3,1,NULL),('Mouchoire GF',NULL,'PRSE0010','1',22,3,1,NULL),('Mouchoire PF',NULL,'PRSE0011','1',22,3,1,NULL),('carte mémoire 1GB',NULL,'PRST0001','1',29,3,1,NULL),('carte mémoire 4GB',NULL,'PRST0002','1',29,3,1,NULL),('carte mémoire 8GB',NULL,'PRST0003','1',29,3,1,NULL),('ecouteurs',NULL,'PRST0004','1',29,3,1,NULL),('Flash Disk 16GB',NULL,'PRST0005','1',29,3,1,NULL),('Flash Disk 32GB',NULL,'PRST0006','1',29,3,1,NULL),('Flash Disk8GB',NULL,'PRST0007','1',29,3,1,NULL),('Cacao',NULL,'PRTH0001','1',52,9,1,NULL),('tomate salsa',NULL,'PRTO0001','1',66,3,1,NULL),('Mediven blanc',NULL,'PRTU0001','1',68,3,1,NULL),('Mediven noir',NULL,'PRTU0002','1',68,3,1,NULL),('Bol plastique',NULL,'PRUS0001','1',13,3,1,NULL),('Bol fero io',NULL,'PRUS0002','1',13,3,1,NULL),('Cuillère',NULL,'PRUS0003','1',13,3,1,NULL),('cullotte',NULL,'PRUS0004','1',13,3,1,NULL),('Gobelet melanime',NULL,'PRUS0006','1',13,3,1,NULL),('plat simple',NULL,'PRUS0008','1',13,3,1,NULL),('plastique',NULL,'PRUS0009','1',13,3,1,NULL),('thermos always 0,5l',NULL,'PRUS0010','1',13,3,1,NULL),('thermos always 0,75l',NULL,'PRUS0011','1',13,3,1,NULL),('thermos always 0,8l',NULL,'PRUS0012','1',13,3,1,NULL),('thermos always 2,5l',NULL,'PRUS0013','1',13,3,1,NULL),('thermos always 3,5l',NULL,'PRUS0014','1',13,3,1,NULL),('Verre Metallique',NULL,'PRUS0015','1',13,3,1,NULL),('Plat 22cm',NULL,'PRUS0016','1',13,3,1,NULL),('Plat divisé',NULL,'PRUS0017','1',13,3,1,NULL),('Plat porcelene',NULL,'PRUS0018','1',13,3,1,NULL),('Gourde 0,5l',NULL,'PRUS0019','1',13,3,1,NULL),('Gourde 1L',NULL,'PRUS0020','1',13,3,1,NULL),('thermos 3l',NULL,'PRUS0021','1',13,3,1,NULL);
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
  `quantite_vendue` decimal(12,3) NOT NULL,
  `prix_achat` decimal(10,2) NOT NULL,
  `prix_vente` decimal(10,2) NOT NULL,
  `benefice_unitaire` decimal(10,2) NOT NULL,
  `benefice_total` decimal(12,2) NOT NULL,
  `date_calcul` datetime(6) NOT NULL,
  `lot_entree_id` bigint NOT NULL,
  `ligne_sortie_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_beneficelot_lot_entree_id_9e1012b4_fk_stock_ligneentree_id` (`lot_entree_id`),
  KEY `stock_beneficelot_ligne_sortie_id_82bcff57_fk_stock_lig` (`ligne_sortie_id`),
  CONSTRAINT `stock_beneficelot_ligne_sortie_id_82bcff57_fk_stock_lig` FOREIGN KEY (`ligne_sortie_id`) REFERENCES `stock_lignesortie` (`id`),
  CONSTRAINT `stock_beneficelot_lot_entree_id_9e1012b4_fk_stock_ligneentree_id` FOREIGN KEY (`lot_entree_id`) REFERENCES `stock_ligneentree` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=116 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_beneficelot`
--

LOCK TABLES `stock_beneficelot` WRITE;
/*!40000 ALTER TABLE `stock_beneficelot` DISABLE KEYS */;
INSERT INTO `stock_beneficelot` VALUES (1,2.000,0.00,1.00,1.00,2.00,'2026-03-23 16:30:19.838142',2,1),(2,2.000,0.00,1.00,1.00,2.00,'2026-03-23 16:32:30.566160',3,2),(3,1.000,0.58,1.04,0.46,0.46,'2026-04-24 13:31:03.218951',121,3),(4,1.000,0.31,0.63,0.32,0.32,'2026-04-24 13:31:03.281433',310,4),(5,3.000,0.01,0.02,0.01,0.03,'2026-04-24 13:31:03.390801',359,5),(6,1.000,0.09,0.21,0.12,0.12,'2026-04-24 13:31:04.347958',213,6),(7,2.000,0.07,0.10,0.03,0.06,'2026-04-24 13:31:04.490668',248,7),(8,2.000,0.03,0.06,0.03,0.06,'2026-04-24 13:31:04.507296',46,8),(9,1.000,0.01,0.08,0.07,0.07,'2026-04-24 13:31:04.607413',34,9),(10,2.000,0.17,0.21,0.04,0.08,'2026-04-24 13:31:04.623041',69,10),(11,23.000,0.11,0.21,0.10,2.30,'2026-04-24 13:31:04.669910',339,11),(12,6.000,0.01,0.01,0.00,0.00,'2026-04-24 13:53:30.915076',44,12),(13,1.000,0.90,1.46,0.56,0.56,'2026-04-24 13:53:30.946231',342,13),(14,1.000,0.03,0.06,0.03,0.03,'2026-04-24 13:53:30.961855',46,14),(15,1.000,0.02,0.02,0.00,0.00,'2026-04-24 13:53:30.995161',45,15),(16,15.000,0.01,0.01,0.00,0.00,'2026-04-24 13:53:31.010787',44,16),(17,2.000,0.11,0.21,0.10,0.20,'2026-04-24 13:53:31.042031',36,17),(18,3.000,0.01,0.01,0.00,0.00,'2026-04-24 13:53:31.073281',44,18),(19,2.000,1.04,1.25,0.21,0.42,'2026-04-24 13:53:31.104531',312,19),(20,1.000,0.41,0.63,0.22,0.22,'2026-04-24 13:53:31.120151',119,20),(21,1.000,0.83,1.04,0.21,0.21,'2026-04-24 13:53:31.151407',305,21),(22,1.000,0.90,1.46,0.56,0.56,'2026-04-24 13:53:31.164224',342,22),(23,5.000,0.14,0.21,0.07,0.35,'2026-04-24 13:53:31.195463',218,23),(24,1.000,0.58,1.04,0.46,0.46,'2026-04-29 09:41:03.873328',121,24),(25,15.000,0.01,0.02,0.01,0.15,'2026-04-29 15:36:08.109501',359,25),(26,1.000,0.73,1.25,0.52,0.52,'2026-04-29 15:36:08.134754',297,26),(27,15.000,0.01,0.01,0.00,0.00,'2026-04-29 15:36:08.166001',44,27),(28,1.000,0.95,1.25,0.30,0.30,'2026-04-29 15:36:08.197253',37,28),(29,31.000,0.02,0.02,0.00,0.00,'2026-04-29 15:43:03.243798',45,29),(30,1.000,0.14,0.21,0.07,0.07,'2026-04-29 15:43:03.259421',218,30),(31,1.000,1.50,2.50,1.00,1.00,'2026-04-29 15:43:03.275061',198,31),(32,20.000,0.02,0.02,0.00,0.00,'2026-04-29 15:43:03.290683',45,32),(33,1.000,2.00,3.33,1.33,1.33,'2026-04-29 15:43:03.321930',205,33),(34,2.000,0.07,0.10,0.03,0.06,'2026-04-29 15:43:03.330103',248,34),(35,1.000,0.01,0.08,0.07,0.07,'2026-04-29 15:43:03.345745',34,35),(36,3.000,0.02,0.04,0.02,0.06,'2026-04-29 15:43:03.361368',133,36),(37,1.000,0.11,0.21,0.10,0.10,'2026-04-29 15:43:03.376992',36,37),(38,1.000,0.70,1.04,0.34,0.34,'2026-04-29 15:46:18.881161',186,38),(39,1.000,0.50,0.83,0.33,0.33,'2026-04-29 15:46:18.904393',123,39),(40,15.000,0.14,0.21,0.07,1.05,'2026-04-29 15:46:18.920018',218,40),(41,1.000,0.31,0.63,0.32,0.32,'2026-04-29 16:05:08.905202',310,41),(42,3.000,0.01,0.02,0.01,0.03,'2026-04-29 16:05:08.936438',359,42),(43,1.000,0.09,0.21,0.12,0.12,'2026-04-29 16:05:08.967683',213,43),(44,2.000,0.07,0.10,0.03,0.06,'2026-04-29 16:05:08.988219',248,44),(45,2.000,0.03,0.06,0.03,0.06,'2026-04-29 16:05:09.003852',46,45),(46,1.000,0.01,0.08,0.07,0.07,'2026-04-29 16:05:09.019483',34,46),(47,1.000,0.17,0.21,0.04,0.04,'2026-04-29 16:05:09.035108',69,47),(48,1.000,0.11,0.21,0.10,0.10,'2026-04-29 16:05:09.066339',339,48),(49,1.000,0.17,0.21,0.04,0.04,'2026-04-29 16:05:09.081979',69,49),(50,6.000,0.01,0.01,0.00,0.00,'2026-05-01 12:12:47.928773',44,50),(51,1.000,0.90,1.46,0.56,0.56,'2026-05-01 12:12:47.960028',342,51),(52,1.000,0.03,0.06,0.03,0.03,'2026-05-01 12:12:47.975647',46,52),(53,1.000,0.02,0.02,0.00,0.00,'2026-05-01 12:12:47.991270',45,53),(54,15.000,0.01,0.01,0.00,0.00,'2026-05-01 12:12:48.006890',44,54),(55,2.000,0.11,0.21,0.10,0.20,'2026-05-01 12:12:48.022512',36,55),(56,3.000,0.01,0.01,0.00,0.00,'2026-05-01 12:12:48.038141',44,56),(57,0.250,0.80,1.17,0.37,0.09,'2026-05-01 12:12:48.053761',311,57),(58,1.000,1.04,1.25,0.21,0.21,'2026-05-01 12:12:48.100649',312,58),(59,2.000,1.04,1.25,0.21,0.42,'2026-05-01 12:18:30.608538',312,59),(60,1.000,0.41,0.63,0.22,0.22,'2026-05-01 12:18:30.625118',119,60),(61,1.000,0.83,1.04,0.21,0.21,'2026-05-01 12:18:30.641825',305,61),(62,1.000,0.90,1.46,0.56,0.56,'2026-05-01 12:18:30.659628',342,62),(63,0.500,5.40,6.88,1.48,0.74,'2026-05-01 12:18:30.676738',108,63),(64,5.000,0.14,0.21,0.07,0.35,'2026-05-01 12:18:30.692382',218,64),(65,1.000,12.25,16.00,3.75,3.75,'2026-05-01 12:20:02.179591',170,65),(66,5.000,0.01,0.08,0.07,0.35,'2026-05-01 13:39:30.988757',34,66),(67,14.000,0.02,0.02,0.00,0.00,'2026-05-01 13:39:31.004422',45,67),(68,15.000,0.01,0.01,0.00,0.00,'2026-05-01 13:39:31.035633',44,68),(69,2.000,0.11,0.21,0.10,0.20,'2026-05-01 13:39:31.051260',36,69),(70,1.000,0.10,0.21,0.11,0.11,'2026-05-01 13:46:01.762268',31,70),(71,1.000,0.02,0.04,0.02,0.02,'2026-05-01 13:46:01.777857',133,71),(72,1.000,0.09,0.21,0.12,0.12,'2026-05-01 13:46:01.793482',213,72),(73,6.000,0.01,0.02,0.01,0.06,'2026-05-01 13:46:01.809120',359,73),(74,1.000,0.11,0.21,0.10,0.10,'2026-05-01 13:46:01.824745',36,74),(75,2.000,0.01,0.21,0.20,0.40,'2026-05-01 13:46:01.840355',181,75),(76,1.000,0.17,0.21,0.04,0.04,'2026-05-01 13:46:01.855993',69,76),(77,1.000,0.11,0.21,0.10,0.10,'2026-05-01 13:46:01.871617',36,77),(78,0.500,1.04,1.25,0.21,0.11,'2026-05-01 13:46:01.902851',312,78),(79,4.000,0.02,0.02,0.00,0.00,'2026-05-01 13:46:01.918475',45,79),(80,12.000,0.02,0.02,0.00,0.00,'2026-05-03 15:04:43.957446',45,80),(81,2.000,0.11,0.21,0.10,0.20,'2026-05-03 15:04:43.973057',36,81),(82,1.000,0.66,0.63,-0.03,-0.03,'2026-05-03 15:04:44.004305',103,82),(83,10.000,0.02,0.02,0.00,0.00,'2026-05-03 15:04:44.019929',45,83),(84,10.000,0.06,0.10,0.04,0.40,'2026-05-03 15:10:02.570727',290,84),(85,1.000,0.24,0.42,0.18,0.18,'2026-05-03 15:10:02.601992',79,85),(86,1.000,1.41,1.88,0.47,0.47,'2026-05-03 15:10:02.617592',39,86),(87,1.000,0.90,1.46,0.56,0.56,'2026-05-03 15:10:02.633216',342,87),(88,8.000,0.14,0.21,0.07,0.56,'2026-05-03 15:10:02.665213',218,88),(89,1.000,0.10,0.21,0.11,0.11,'2026-05-03 15:18:55.468261',31,89),(90,1.000,0.11,0.21,0.10,0.10,'2026-05-03 15:18:55.483888',36,90),(91,1.000,0.10,0.21,0.11,0.11,'2026-05-03 15:18:55.499507',31,91),(92,1.000,1.50,1.04,-0.46,-0.46,'2026-05-03 15:18:55.515147',238,92),(93,4.000,0.06,0.10,0.04,0.16,'2026-05-03 15:18:55.530756',290,93),(94,1.000,0.01,0.21,0.20,0.20,'2026-05-03 15:18:55.546379',181,94),(95,1.000,0.02,0.04,0.02,0.02,'2026-05-03 15:18:55.562002',30,95),(96,4.000,0.14,0.21,0.07,0.28,'2026-05-03 15:18:55.577625',218,96),(97,30.000,0.14,0.21,0.07,2.10,'2026-05-03 15:29:37.961250',218,97),(98,2.000,0.10,0.21,0.11,0.22,'2026-05-03 15:29:37.976876',31,98),(99,2.000,0.11,0.21,0.10,0.20,'2026-05-03 15:29:38.008121',36,99),(100,1.000,0.41,0.63,0.22,0.22,'2026-05-03 15:29:38.023747',216,100),(101,1.000,0.29,0.42,0.13,0.13,'2026-05-03 15:29:38.055010',92,101),(102,1.000,0.17,0.21,0.04,0.04,'2026-05-03 15:29:38.070631',69,102),(103,1.000,0.01,0.08,0.07,0.07,'2026-05-03 15:29:38.086242',34,103),(104,2.000,0.01,0.08,0.07,0.14,'2026-05-03 15:29:38.101876',34,104),(105,2.000,0.02,0.04,0.02,0.04,'2026-05-03 15:29:38.117505',30,105),(106,2.000,0.02,0.02,0.00,0.00,'2026-05-03 15:29:38.133121',45,106),(107,1.000,10.00,12.00,2.00,2.00,'2026-05-03 15:43:10.407142',281,107),(108,2.000,0.03,0.06,0.03,0.06,'2026-05-03 15:54:46.912705',46,108),(109,1.000,0.05,0.08,0.03,0.03,'2026-05-03 15:54:46.928327',134,109),(110,10.000,0.02,0.02,0.00,0.00,'2026-05-03 15:54:46.943971',45,110),(111,3.000,0.10,0.21,0.11,0.33,'2026-05-03 15:54:46.959590',291,111),(112,10.000,0.01,0.02,0.01,0.10,'2026-05-03 15:54:46.980138',11,112),(113,1.000,0.29,0.50,0.21,0.21,'2026-05-03 15:54:46.996790',177,113),(114,8.000,0.02,0.02,0.00,0.00,'2026-05-03 15:54:47.012416',45,114),(115,2.000,0.14,0.21,0.07,0.14,'2026-05-03 15:54:47.028039',218,115);
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
  `password` varchar(128) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_clien_email_b7739e_idx` (`email`),
  FULLTEXT KEY `ft_client_search` (`nom`,`telephone`,`adresse`,`email`,`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_client`
--

LOCK TABLES `stock_client` WRITE;
/*!40000 ALTER TABLE `stock_client` DISABLE KEYS */;
INSERT INTO `stock_client` VALUES ('CLI0001','Client inconnu','','',NULL,'2026-03-23 16:30:19.421233',NULL);
/*!40000 ALTER TABLE `stock_client` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_cliententreprise`
--

DROP TABLE IF EXISTS `stock_cliententreprise`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_cliententreprise` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_special` tinyint(1) NOT NULL,
  `client_id` varchar(20) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `stock_cliententreprise_client_id_entreprise_id_1178f60b_uniq` (`client_id`,`entreprise_id`),
  KEY `stock_clien_entrepr_405f31_idx` (`entreprise_id`,`client_id`),
  KEY `stock_clien_client__217599_idx` (`client_id`),
  KEY `stock_clien_entrepr_1b06f7_idx` (`entreprise_id`,`is_special`),
  KEY `stock_cliententrepri_succursale_id_74ed3b9e_fk_stock_suc` (`succursale_id`),
  CONSTRAINT `stock_cliententrepri_entreprise_id_ae4a9ef3_fk_stock_ent` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_cliententrepri_succursale_id_74ed3b9e_fk_stock_suc` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`),
  CONSTRAINT `stock_cliententreprise_client_id_d4cb7395_fk_stock_client_id` FOREIGN KEY (`client_id`) REFERENCES `stock_client` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_cliententreprise`
--

LOCK TABLES `stock_cliententreprise` WRITE;
/*!40000 ALTER TABLE `stock_cliententreprise` DISABLE KEYS */;
INSERT INTO `stock_cliententreprise` VALUES (1,0,'CLI0001',1,NULL);
/*!40000 ALTER TABLE `stock_cliententreprise` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_detailmouvementcaisse`
--

DROP TABLE IF EXISTS `stock_detailmouvementcaisse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_detailmouvementcaisse` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `montant` decimal(12,2) NOT NULL,
  `motif_explicite` longtext NOT NULL,
  `reference_piece` varchar(100) NOT NULL,
  `mouvement_id` bigint NOT NULL,
  `type_caisse_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_detailmouvemen_mouvement_id_bad96ba0_fk_stock_mou` (`mouvement_id`),
  KEY `stock_detailmouvemen_type_caisse_id_9c09512f_fk_stock_typ` (`type_caisse_id`),
  CONSTRAINT `stock_detailmouvemen_mouvement_id_bad96ba0_fk_stock_mou` FOREIGN KEY (`mouvement_id`) REFERENCES `stock_mouvementcaisse` (`id`),
  CONSTRAINT `stock_detailmouvemen_type_caisse_id_9c09512f_fk_stock_typ` FOREIGN KEY (`type_caisse_id`) REFERENCES `stock_typecaisse` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_detailmouvementcaisse`
--

LOCK TABLES `stock_detailmouvementcaisse` WRITE;
/*!40000 ALTER TABLE `stock_detailmouvementcaisse` DISABLE KEYS */;
/*!40000 ALTER TABLE `stock_detailmouvementcaisse` ENABLE KEYS */;
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
  `date_creation` datetime(6) NOT NULL,
  `date_echeance` date DEFAULT NULL,
  `statut` varchar(20) NOT NULL,
  `commentaire` longtext,
  `client_id` varchar(20) NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `sortie_id` bigint NOT NULL,
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `sortie_id` (`sortie_id`),
  KEY `stock_detteclient_client_id_70fee6c4_fk_stock_client_id` (`client_id`),
  KEY `stock_detteclient_devise_id_684fe1d6_fk_stock_devise_id` (`devise_id`),
  KEY `stock_detteclient_succursale_id_aa91fc5d_fk_stock_succursale_id` (`succursale_id`),
  KEY `stock_dette_entrepr_c39c0a_idx` (`entreprise_id`),
  KEY `stock_dette_entrepr_61d8e7_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_detteclient_client_id_70fee6c4_fk_stock_client_id` FOREIGN KEY (`client_id`) REFERENCES `stock_client` (`id`),
  CONSTRAINT `stock_detteclient_devise_id_684fe1d6_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_detteclient_entreprise_id_6a0e562c_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_detteclient_sortie_id_cb8d6fd0_fk_stock_sortie_id` FOREIGN KEY (`sortie_id`) REFERENCES `stock_sortie` (`id`),
  CONSTRAINT `stock_detteclient_succursale_id_aa91fc5d_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_detteclient`
--

LOCK TABLES `stock_detteclient` WRITE;
/*!40000 ALTER TABLE `stock_detteclient` DISABLE KEYS */;
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
INSERT INTO `stock_devise` VALUES (1,'USD','Dollars americais','$',1,1);
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
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_entre_entrepr_83a12f_idx` (`entreprise_id`),
  KEY `stock_entre_succurs_fd439a_idx` (`succursale_id`),
  KEY `stock_entre_entrepr_98cbc9_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_entree_entreprise_id_0fb54fa4_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_entree_succursale_id_c84ef07e_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_entree`
--

LOCK TABLES `stock_entree` WRITE;
/*!40000 ALTER TABLE `stock_entree` DISABLE KEYS */;
INSERT INTO `stock_entree` VALUES (1,'Inventaire','','2026-03-23 16:22:30.654283',1,NULL),(2,'Inventaire','','2026-03-23 16:29:29.610026',1,NULL),(3,'Approvisionnement  Inventaire','','2026-04-17 07:40:05.981574',1,NULL),(4,'Approvisionnement','','2026-04-24 13:18:24.077737',1,NULL);
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
  `email` varchar(254) NOT NULL,
  `nif` varchar(100) NOT NULL,
  `responsable` varchar(255) NOT NULL,
  `logo` varchar(100) DEFAULT NULL,
  `slogan` varchar(255) DEFAULT NULL,
  `has_branches` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_entreprise`
--

LOCK TABLES `stock_entreprise` WRITE;
/*!40000 ALTER TABLE `stock_entreprise` DISABLE KEYS */;
INSERT INTO `stock_entreprise` VALUES (1,'CANTINE UNILUK','commerce','Congo','Nord-Kivu/ butembo LUKANGA','+243976316454','uniluk@gmail.com','DC78900','Console Malambo','entreprises/logos/imgi_3_default.jpg','UNIVERSITE ADVENTISTE DE LUKANGA',0);
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
  `quantite` decimal(12,3) NOT NULL,
  `quantite_restante` decimal(12,3) NOT NULL,
  `prix_unitaire` decimal(10,2) NOT NULL,
  `prix_vente` decimal(10,2) NOT NULL,
  `date_expiration` date DEFAULT NULL,
  `date_entree` datetime(6) NOT NULL,
  `seuil_alerte` decimal(12,3) NOT NULL,
  `article_id` varchar(10) NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `entree_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_ligneentree_devise_id_2d1d5e04_fk_stock_devise_id` (`devise_id`),
  KEY `stock_ligneentree_entree_id_c3061fbb_fk_stock_entree_id` (`entree_id`),
  KEY `stock_ligne_article_e99d66_idx` (`article_id`,`date_entree`),
  CONSTRAINT `stock_ligneentree_article_id_5e64e8c1_fk_stock_art` FOREIGN KEY (`article_id`) REFERENCES `stock_article` (`article_id`),
  CONSTRAINT `stock_ligneentree_devise_id_2d1d5e04_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_ligneentree_entree_id_c3061fbb_fk_stock_entree_id` FOREIGN KEY (`entree_id`) REFERENCES `stock_entree` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=360 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_ligneentree`
--

LOCK TABLES `stock_ligneentree` WRITE;
/*!40000 ALTER TABLE `stock_ligneentree` DISABLE KEYS */;
INSERT INTO `stock_ligneentree` VALUES (2,10.000,8.000,0.00,1.00,NULL,'2026-03-23 16:25:29.117063',3.000,'PRSE0005',1,1),(3,20.000,18.000,0.00,1.00,NULL,'2026-03-23 16:29:29.618019',10.000,'PRUS0015',1,2),(4,14.000,14.000,1.50,3.13,NULL,'2026-04-17 07:40:06.023581',10.000,'FOAG0001',1,3),(5,10.000,10.000,1.00,1.46,NULL,'2026-04-17 07:40:06.120721',10.000,'FOAG0002',1,3),(6,620.000,620.000,0.37,0.63,NULL,'2026-04-17 07:40:06.199123',10.000,'FOAG0003',1,3),(7,7.000,7.000,6.00,7.50,NULL,'2026-04-17 07:40:06.270545',10.000,'FOAG0004',1,3),(8,288.000,288.000,0.00,0.04,NULL,'2026-04-17 07:40:06.333441',10.000,'ARCO0013',1,3),(9,13.000,13.000,2.00,3.50,NULL,'2026-04-17 07:40:06.396662',10.000,'PRDI0001',1,3),(10,1976.000,1976.000,0.02,0.04,NULL,'2026-04-17 07:40:06.626662',10.000,'PRCO0003',1,3),(11,740.000,730.000,0.01,0.02,NULL,'2026-04-17 07:40:06.720891',10.000,'PRCO0002',1,3),(12,10.000,10.000,1.58,2.50,NULL,'2026-04-17 07:40:06.787075',10.000,'PRCR0018',1,3),(13,16.000,16.000,2.83,3.33,NULL,'2026-04-17 07:40:06.865014',10.000,'PRPR0001',1,3),(14,30.000,30.000,0.58,0.83,NULL,'2026-04-17 07:40:06.938303',10.000,'FOST0001',1,3),(15,26.000,26.000,0.66,1.04,NULL,'2026-04-17 07:40:07.018946',10.000,'PRNE0001',1,3),(16,276.000,276.000,0.04,0.20,NULL,'2026-04-17 07:40:07.092905',10.000,'PRNE0002',1,3),(17,14.000,14.000,1.16,1.88,NULL,'2026-04-17 07:40:07.155997',10.000,'HASO0010',1,3),(18,20.000,20.000,0.50,0.63,NULL,'2026-04-17 07:40:07.226924',10.000,'FOST0008',1,3),(19,45.000,45.000,0.20,0.29,NULL,'2026-04-17 07:40:07.311913',10.000,'FOST0009',1,3),(20,11.000,11.000,1.08,3.13,NULL,'2026-04-17 07:40:07.374768',10.000,'PRNE0007',1,3),(21,20.000,20.000,2.08,1.67,NULL,'2026-04-17 07:40:07.437948',10.000,'PRUS0009',1,3),(22,1.000,1.000,10.00,12.00,NULL,'2026-04-17 07:40:07.509602',10.000,'PRLI0006',1,3),(23,5.000,5.000,11.00,13.50,NULL,'2026-04-17 07:40:07.584757',10.000,'PRLI0005',1,3),(24,11.000,11.000,9.00,11.00,NULL,'2026-04-17 07:40:07.657564',10.000,'PRBI0015',1,3),(25,4.000,4.000,15.00,17.50,NULL,'2026-04-17 07:40:07.721847',10.000,'PRBI0016',1,3),(26,3.000,3.000,12.00,17.50,NULL,'2026-04-17 07:40:07.788190',10.000,'PRBI0017',1,3),(27,26.000,26.000,0.02,0.21,NULL,'2026-04-17 07:40:07.853920',10.000,'FOMA0001',1,3),(28,23.000,23.000,0.83,0.42,NULL,'2026-04-17 07:40:07.910962',10.000,'FOST0010',1,3),(29,21.000,21.000,0.13,0.21,NULL,'2026-04-17 07:40:07.978047',10.000,'PRMA0020',1,3),(30,464.000,461.000,0.02,0.04,NULL,'2026-04-17 07:40:08.037351',10.000,'PRBI0001',1,3),(31,125.000,120.000,0.10,0.21,NULL,'2026-04-17 07:40:08.106247',10.000,'PRBI0002',1,3),(32,68.000,68.000,0.09,0.17,NULL,'2026-04-17 07:40:08.176943',10.000,'PRBI0003',1,3),(33,44.000,44.000,0.41,0.63,NULL,'2026-04-17 07:40:08.244858',10.000,'PRBI0004',1,3),(34,415.000,404.000,0.01,0.08,NULL,'2026-04-17 07:40:08.321352',10.000,'PRBI0005',1,3),(35,180.000,180.000,0.10,0.17,NULL,'2026-04-17 07:40:08.376499',10.000,'PRBI0007',1,3),(36,427.000,413.000,0.11,0.21,NULL,'2026-04-17 07:40:08.461010',10.000,'PRBI0008',1,3),(37,23.000,22.000,0.95,1.25,NULL,'2026-04-17 07:40:08.531889',10.000,'PRBI0009',1,3),(38,15.000,15.000,0.52,0.83,NULL,'2026-04-17 07:40:08.596348',10.000,'PRBE0001',1,3),(39,16.000,15.000,1.41,1.88,NULL,'2026-04-17 07:40:08.670741',10.000,'PRBE0002',1,3),(40,1.000,1.000,3.15,3.75,NULL,'2026-04-17 07:40:08.760539',10.000,'PRBE0003',1,3),(41,6.000,6.000,0.45,0.63,NULL,'2026-04-17 07:40:08.830885',10.000,'FOCL0001',1,3),(42,65.000,65.000,0.58,0.83,NULL,'2026-04-17 07:40:08.906448',10.000,'PRUS0002',1,3),(43,23.000,23.000,0.50,0.63,NULL,'2026-04-17 07:40:08.979565',10.000,'PRUS0001',1,3),(44,2597.000,2519.000,0.01,0.01,NULL,'2026-04-17 07:40:09.054918',10.000,'PRBI0011',1,3),(45,332.000,219.000,0.02,0.02,NULL,'2026-04-17 07:40:09.116033',10.000,'PRBI0012',1,3),(46,273.000,265.000,0.03,0.06,NULL,'2026-04-17 07:40:09.186941',10.000,'PRBI0010',1,3),(47,12.000,12.000,0.48,0.63,NULL,'2026-04-17 07:40:09.260570',10.000,'PRMA0001',1,3),(48,5.000,5.000,1.52,2.08,NULL,'2026-04-17 07:40:09.320109',10.000,'PRPA0005',1,3),(49,1.000,1.000,1.17,2.50,NULL,'2026-04-17 07:40:09.385666',10.000,'PRFL0003',1,3),(50,4.000,4.000,8.00,10.00,NULL,'2026-04-17 07:40:09.456747',10.000,'PRFL0001',1,3),(51,5.000,5.000,3.30,4.50,NULL,'2026-04-17 07:40:09.519986',10.000,'PRFL0002',1,3),(52,12.000,12.000,0.25,0.29,NULL,'2026-04-17 07:40:09.595405',10.000,'PRDE0009',1,3),(53,10.000,10.000,0.20,0.83,NULL,'2026-04-17 07:40:09.670448',10.000,'PRNE0011',1,3),(54,23.000,23.000,0.50,1.04,NULL,'2026-04-17 07:40:09.732619',10.000,'PRNE0009',1,3),(55,35.000,35.000,0.41,0.63,NULL,'2026-04-17 07:40:09.805484',10.000,'PRNE0008',1,3),(56,26.000,26.000,0.09,0.21,NULL,'2026-04-17 07:40:09.887302',10.000,'PRDE0010',1,3),(57,15.000,15.000,1.83,1.04,NULL,'2026-04-17 07:40:09.948894',10.000,'PRNE0012',1,3),(58,72.000,72.000,0.11,0.21,NULL,'2026-04-17 07:40:10.020022',10.000,'PRDE0003',1,3),(59,11.000,11.000,1.00,1.88,NULL,'2026-04-17 07:40:10.086518',10.000,'PRDI0013',1,3),(60,15.000,15.000,0.70,1.25,NULL,'2026-04-17 07:40:10.158748',10.000,'PRDI0005',1,3),(61,6.000,6.000,0.70,1.46,NULL,'2026-04-17 07:40:10.222682',10.000,'PRDI0004',1,3),(62,6.000,6.000,1.00,1.25,NULL,'2026-04-17 07:40:10.286401',10.000,'PRTH0001',1,3),(63,5.000,5.000,1.56,1.88,NULL,'2026-04-17 07:40:10.351814',10.000,'ARCO0009',1,3),(64,2.000,2.000,1.04,1.25,NULL,'2026-04-17 07:40:10.419953',10.000,'ARCA0001',1,3),(65,11.000,11.000,0.52,0.63,NULL,'2026-04-17 07:40:10.487808',10.000,'ARCA0002',1,3),(66,40.000,40.000,0.38,0.42,NULL,'2026-04-17 07:40:10.573278',10.000,'FOCA0004',1,3),(67,35.000,35.000,0.38,0.42,NULL,'2026-04-17 07:40:10.641928',10.000,'FOCA0009',1,3),(68,77.000,77.000,0.17,0.21,NULL,'2026-04-17 07:40:10.725047',10.000,'FOCA0005',1,3),(69,171.000,165.000,0.17,0.21,NULL,'2026-04-17 07:40:10.792815',10.000,'FOCA0011',1,3),(70,39.000,39.000,0.07,0.10,NULL,'2026-04-17 07:40:10.869725',10.000,'FOCA0002',1,3),(71,280.000,280.000,0.07,0.10,NULL,'2026-04-17 07:40:10.938194',10.000,'FOCA0001',1,3),(72,18.000,18.000,1.50,3.33,NULL,'2026-04-17 07:40:11.003212',10.000,'FOCA0006',1,3),(73,19.000,19.000,0.80,1.46,NULL,'2026-04-17 07:40:11.069641',10.000,'FOCA0007',1,3),(74,2367.000,2367.000,0.07,0.10,NULL,'2026-04-17 07:40:11.136075',10.000,'FOCA0010',1,3),(75,11.000,11.000,1.50,2.08,NULL,'2026-04-17 07:40:11.205557',10.000,'PRST0001',1,3),(76,10.000,10.000,2.10,2.71,NULL,'2026-04-17 07:40:11.286336',10.000,'PRST0002',1,3),(77,3.000,3.000,2.50,3.33,NULL,'2026-04-17 07:40:11.351354',10.000,'PRST0003',1,3),(78,182.000,182.000,0.02,0.21,NULL,'2026-04-17 07:40:11.424803',10.000,'PRPA0003',1,3),(79,65.000,64.000,0.24,0.42,NULL,'2026-04-17 07:40:11.491345',10.000,'PRMA0002',1,3),(80,4.000,4.000,0.90,1.88,NULL,'2026-04-17 07:40:11.558604',10.000,'PRDI0007',1,3),(81,42.000,42.000,0.90,1.88,NULL,'2026-04-17 07:40:11.643646',10.000,'PRDI0006',1,3),(82,16.000,16.000,2.00,2.71,NULL,'2026-04-17 07:40:11.715598',10.000,'PRDI0008',1,3),(83,30.000,30.000,0.21,0.63,NULL,'2026-04-17 07:40:11.797224',10.000,'HACH0005',1,3),(84,21.000,21.000,0.21,0.63,NULL,'2026-04-17 07:40:11.861829',10.000,'HACH0006',1,3),(85,30.000,30.000,0.21,0.42,NULL,'2026-04-17 07:40:11.934406',10.000,'HACH0007',1,3),(86,11.000,11.000,0.17,0.42,NULL,'2026-04-17 07:40:12.018070',10.000,'HACH0008',1,3),(87,4.000,4.000,14.00,15.00,NULL,'2026-04-17 07:40:12.084339',10.000,'HACH0009',1,3),(88,3.000,3.000,10.00,13.00,NULL,'2026-04-17 07:40:12.152522',10.000,'HACH0010',1,3),(89,2.000,2.000,12.00,16.00,NULL,'2026-04-17 07:40:12.218068',10.000,'HACH0011',1,3),(90,28.000,28.000,1.25,1.88,NULL,'2026-04-17 07:40:12.291885',10.000,'HADI0001',1,3),(91,8.000,8.000,1.16,1.46,NULL,'2026-04-17 07:40:12.354557',10.000,'HADI0002',1,3),(92,27.000,26.000,0.29,0.42,NULL,'2026-04-17 07:40:12.418563',10.000,'ARCO0014',1,3),(93,381.000,381.000,0.01,0.02,NULL,'2026-04-17 07:40:12.497070',10.000,'PRDI0014',1,3),(94,4.000,4.000,1.81,2.08,NULL,'2026-04-17 07:40:12.560234',10.000,'FOCL0002',1,3),(95,10.000,10.000,1.66,2.08,NULL,'2026-04-17 07:40:12.635523',10.000,'PRCR0002',1,3),(96,5.000,5.000,0.79,2.08,NULL,'2026-04-17 07:40:12.717537',10.000,'PRCR0004',1,3),(97,47.000,47.000,3.50,5.00,NULL,'2026-04-17 07:40:12.796983',10.000,'ARCO0001',1,3),(98,25.000,25.000,0.13,0.63,NULL,'2026-04-17 07:40:12.861411',10.000,'PRMA0003',1,3),(99,11.000,11.000,3.60,4.32,NULL,'2026-04-17 07:40:12.935104',10.000,'PRSE0007',1,3),(100,1.000,1.000,3.00,3.95,NULL,'2026-04-17 07:40:13.013097',10.000,'PRSE0006',1,3),(101,16.000,16.000,1.20,1.88,NULL,'2026-04-17 07:40:13.086478',10.000,'PRSE0009',1,3),(102,58.000,58.000,0.71,1.04,NULL,'2026-04-17 07:40:13.169196',10.000,'PRSE0008',1,3),(103,47.000,46.000,0.66,0.63,NULL,'2026-04-17 07:40:13.258613',10.000,'ARDI0001',1,3),(104,7.000,7.000,0.45,0.83,NULL,'2026-04-17 07:40:13.331368',10.000,'PRDI0015',1,3),(105,30.000,30.000,0.46,1.04,NULL,'2026-04-17 07:40:13.408921',10.000,'FODI0001',1,3),(106,43.000,43.000,0.25,0.63,NULL,'2026-04-17 07:40:13.484654',10.000,'FODI0002',1,3),(107,10.000,10.000,0.25,0.42,NULL,'2026-04-17 07:40:13.567207',10.000,'PRDI0016',1,3),(108,27.000,26.500,5.40,6.88,NULL,'2026-04-17 07:40:13.639196',10.000,'PRPR0017',1,3),(109,8.000,8.000,0.04,0.10,NULL,'2026-04-17 07:40:13.701807',10.000,'FOCA0013',1,3),(110,2.000,2.000,1.66,2.92,NULL,'2026-04-17 07:40:13.770114',10.000,'PRCR0025',1,3),(111,6.000,6.000,0.58,1.46,NULL,'2026-04-17 07:40:13.852248',10.000,'PRCR0010',1,3),(112,12.000,12.000,1.54,2.29,NULL,'2026-04-17 07:40:13.926159',10.000,'PRCR0008',1,3),(113,12.000,12.000,0.38,0.63,NULL,'2026-04-17 07:40:14.014528',10.000,'PRCR0011',1,3),(114,34.000,34.000,0.04,0.14,NULL,'2026-04-17 07:40:14.101140',10.000,'PRUS0003',1,3),(115,4.000,4.000,1.50,2.29,NULL,'2026-04-17 07:40:14.182174',10.000,'HASO0009',1,3),(116,1.000,1.000,0.25,0.42,NULL,'2026-04-17 07:40:14.252135',10.000,'PRDE0004',1,3),(117,9.000,9.000,1.00,1.46,NULL,'2026-04-17 07:40:14.334758',10.000,'HASI0001',1,3),(118,19.000,19.000,0.25,0.42,NULL,'2026-04-17 07:40:14.404678',10.000,'PREM0003',1,3),(119,12.000,10.000,0.41,0.63,'2026-06-01','2026-04-17 07:40:14.484309',10.000,'PRDE0005',1,3),(120,12.000,12.000,0.83,1.25,'2027-04-01','2026-04-17 07:40:14.550932',10.000,'PRDE0006',1,3),(121,6.000,4.000,0.58,1.04,'2027-10-01','2026-04-17 07:40:14.620098',10.000,'PRDE0008',1,3),(122,15.000,15.000,0.25,0.63,'2027-10-01','2026-04-17 07:40:14.684110',10.000,'PRDE0007',1,3),(123,48.000,47.000,0.50,0.83,NULL,'2026-04-17 07:40:14.758153',10.000,'PRBO0002',1,3),(124,276.000,276.000,0.16,0.25,NULL,'2026-04-17 07:40:14.849535',10.000,'PRBO0003',1,3),(125,314.000,314.000,0.21,0.42,NULL,'2026-04-17 07:40:14.926527',10.000,'PRBO0004',1,3),(126,17.000,17.000,0.50,1.46,NULL,'2026-04-17 07:40:14.990618',10.000,'PRST0004',1,3),(127,9.000,9.000,2.00,3.13,NULL,'2026-04-17 07:40:15.067820',10.000,'FOCA0028',1,3),(128,7.000,7.000,0.75,1.04,NULL,'2026-04-17 07:40:15.135538',10.000,'PREM0001',1,3),(129,42.000,42.000,0.08,0.21,NULL,'2026-04-17 07:40:15.203163',10.000,'PREM0002',1,3),(130,59.000,59.000,0.41,0.63,NULL,'2026-04-17 07:40:15.267641',10.000,'FOEN0001',1,3),(131,94.000,94.000,0.12,0.21,NULL,'2026-04-17 07:40:15.334185',10.000,'FOEN0002',1,3),(132,1000.000,1000.000,0.03,0.04,NULL,'2026-04-17 07:40:15.417208',10.000,'FOMA0004',1,3),(133,650.000,646.000,0.02,0.04,NULL,'2026-04-17 07:40:15.480784',10.000,'FOEN0003',1,3),(134,892.000,891.000,0.05,0.08,NULL,'2026-04-17 07:40:15.551230',10.000,'FOEN0004',1,3),(135,5.000,5.000,4.00,5.21,NULL,'2026-04-17 07:40:15.624400',10.000,'PRLI0004',1,3),(136,82.000,82.000,0.29,0.42,NULL,'2026-04-17 07:40:15.701828',10.000,'FOFA0001',1,3),(137,106.000,106.000,0.18,0.29,NULL,'2026-04-17 07:40:15.767052',10.000,'FOFA0002',1,3),(138,81.000,81.000,0.94,1.17,NULL,'2026-04-17 07:40:15.833781',10.000,'PRMA0005',1,3),(139,12.000,12.000,0.76,1.04,NULL,'2026-04-17 07:40:15.909001',10.000,'PRMA0018',1,3),(140,25.000,25.000,0.45,0.63,NULL,'2026-04-17 07:40:15.983784',10.000,'PRDI0009',1,3),(141,11.000,11.000,0.13,0.21,NULL,'2026-04-17 07:40:16.054619',10.000,'ARCO0012',1,3),(142,5.000,5.000,2.60,4.38,NULL,'2026-04-17 07:40:16.141251',10.000,'PRST0005',1,3),(143,13.000,13.000,3.00,5.21,NULL,'2026-04-17 07:40:16.200398',10.000,'PRST0006',1,3),(144,6.000,6.000,2.40,3.75,NULL,'2026-04-17 07:40:16.267618',10.000,'PRST0007',1,3),(145,103.000,103.000,0.75,1.04,NULL,'2026-04-17 07:40:16.360803',10.000,'PRFL0004',1,3),(146,20.000,20.000,0.16,0.25,NULL,'2026-04-17 07:40:16.423485',10.000,'PRFL0006',1,3),(147,13.000,13.000,0.80,1.88,NULL,'2026-04-17 07:40:16.496518',10.000,'PRFL0005',1,3),(148,2.000,2.000,0.04,0.39,NULL,'2026-04-17 07:40:16.569996',10.000,'PRMA0007',1,3),(149,3.000,3.000,0.38,0.63,NULL,'2026-04-17 07:40:16.644611',10.000,'PRGL0002',1,3),(150,15.000,15.000,1.09,1.46,NULL,'2026-04-17 07:40:16.723689',10.000,'PRGL0005',1,3),(151,1.000,1.000,0.46,0.63,NULL,'2026-04-17 07:40:16.798571',10.000,'PRGL0004',1,3),(152,6.000,6.000,0.50,0.66,NULL,'2026-04-17 07:40:16.866341',10.000,'PRGL0009',1,3),(153,6.000,6.000,1.66,2.50,NULL,'2026-04-17 07:40:16.935239',10.000,'PRGL0013',1,3),(154,23.000,23.000,0.83,1.04,NULL,'2026-04-17 07:40:17.007952',10.000,'PRGL0007',1,3),(155,17.000,17.000,0.41,0.63,NULL,'2026-04-17 07:40:17.092734',10.000,'PRGL0008',1,3),(156,7.000,7.000,0.83,1.04,NULL,'2026-04-17 07:40:17.149983',10.000,'PRGL0012',1,3),(157,32.000,32.000,0.83,1.04,NULL,'2026-04-17 07:40:17.216527',10.000,'PRUS0006',1,3),(158,3.000,3.000,0.16,0.21,NULL,'2026-04-17 07:40:17.291002',10.000,'FOST0004',1,3),(159,85.000,85.000,0.08,0.10,NULL,'2026-04-17 07:40:17.351499',10.000,'FOST0005',1,3),(160,2.000,2.000,4.00,6.25,NULL,'2026-04-17 07:40:17.423290',10.000,'PRUS0019',1,3),(161,4.000,4.000,6.00,8.33,NULL,'2026-04-17 07:40:17.498607',10.000,'PRUS0020',1,3),(162,8.000,8.000,0.33,0.63,NULL,'2026-04-17 07:40:17.566275',10.000,'ARCO0010',1,3),(163,2.000,2.000,0.13,0.21,NULL,'2026-04-17 07:40:17.632691',10.000,'ARCO0011',1,3),(164,7.000,7.000,1.08,1.46,NULL,'2026-04-17 07:40:17.699815',10.000,'PRPR0002',1,3),(165,11.000,11.000,4.37,8.00,NULL,'2026-04-17 07:40:17.768155',10.000,'PRHU0001',1,3),(166,9.000,9.000,9.00,12.00,NULL,'2026-04-17 07:40:17.832637',10.000,'PRHU0002',1,3),(167,10.000,10.000,3.75,5.21,NULL,'2026-04-17 07:40:17.901486',10.000,'PRHU0003',1,3),(168,7.000,7.000,5.18,7.50,NULL,'2026-04-17 07:40:17.966728',10.000,'PRHU0004',1,3),(169,6.000,6.000,11.00,14.00,NULL,'2026-04-17 07:40:18.034563',10.000,'PRHU0005',1,3),(170,3.000,2.000,12.25,16.00,NULL,'2026-04-17 07:40:18.101574',10.000,'PRHU0006',1,3),(171,7.000,7.000,13.00,15.00,NULL,'2026-04-17 07:40:18.191213',10.000,'PRLI0002',1,3),(172,17.000,17.000,1.16,1.88,NULL,'2026-04-17 07:40:18.275175',10.000,'PRMA0008',1,3),(173,10.000,10.000,1.83,3.13,NULL,'2026-04-17 07:40:18.348907',10.000,'PRNE0013',1,3),(174,27.000,27.000,0.07,0.63,NULL,'2026-04-17 07:40:18.431149',10.000,'ARCO0004',1,3),(175,33.000,33.000,0.35,0.63,NULL,'2026-04-17 07:40:18.507311',10.000,'FOCA0015',1,3),(176,5.000,5.000,0.29,0.50,'2026-06-01','2026-04-17 07:40:18.582742',10.000,'PRBO0014',1,3),(177,59.000,58.000,0.29,0.50,'2026-05-01','2026-04-17 07:40:18.650587',10.000,'PRBO0007',1,3),(178,8.000,8.000,1.61,2.50,NULL,'2026-04-17 07:40:18.732234',10.000,'PRBO0023',1,3),(179,65.000,65.000,0.33,0.50,NULL,'2026-04-17 07:40:18.799551',10.000,'PRBO0008',1,3),(180,11.000,11.000,1.67,2.08,NULL,'2026-04-17 07:40:18.872997',10.000,'PRBO0024',1,3),(181,13.000,10.000,0.01,0.21,NULL,'2026-04-17 07:40:18.948724',10.000,'PRBO0009',1,3),(182,12.000,12.000,1.66,2.50,NULL,'2026-04-17 07:40:19.032025',10.000,'PRBO0011',1,3),(183,38.000,38.000,0.33,0.50,NULL,'2026-04-17 07:40:19.103675',10.000,'PRBO0012',1,3),(184,38.000,38.000,0.50,0.63,NULL,'2026-04-17 07:40:19.168350',10.000,'PRBO0010',1,3),(185,32.000,32.000,0.33,0.50,NULL,'2026-04-17 07:40:19.232420',10.000,'PRBO0017',1,3),(186,16.000,15.000,0.70,1.04,'2026-07-01','2026-04-17 07:40:19.300387',10.000,'PRBO0016',1,3),(187,417.000,417.000,0.12,0.21,NULL,'2026-04-17 07:40:19.404003',10.000,'PRPR0003',1,3),(188,9.000,9.000,0.41,0.63,'2026-05-01','2026-04-17 07:40:19.480624',10.000,'PRPR0004',1,3),(189,4.000,4.000,5.00,6.50,NULL,'2026-04-17 07:40:19.552142',10.000,'PRPR0005',1,3),(190,8.000,8.000,10.00,12.50,NULL,'2026-04-17 07:40:19.633640',10.000,'PRPR0006',1,3),(191,270.000,270.000,0.02,0.04,NULL,'2026-04-17 07:40:19.734135',10.000,'PRRA0001',1,3),(192,1.000,1.000,0.20,0.29,NULL,'2026-04-17 07:40:19.798760',10.000,'FOCA0017',1,3),(193,17.000,17.000,1.70,2.04,NULL,'2026-04-17 07:40:19.869019',10.000,'PRMA0009',1,3),(194,10.000,10.000,1.58,2.50,NULL,'2026-04-17 07:40:19.939177',10.000,'PRCR0018',1,3),(195,12.000,12.000,3.33,4.38,NULL,'2026-04-17 07:40:20.020652',10.000,'PRCR0021',1,3),(196,12.000,12.000,3.75,5.21,NULL,'2026-04-17 07:40:20.086432',10.000,'PRCR0023',1,3),(197,3.000,3.000,1.38,2.92,NULL,'2026-04-17 07:40:20.156809',10.000,'PRCR0020',1,3),(198,13.000,12.000,1.50,2.50,NULL,'2026-04-17 07:40:20.231459',10.000,'PRCR0024',1,3),(199,1.000,1.000,4.50,6.25,NULL,'2026-04-17 07:40:20.298172',10.000,'PRPR0007',1,3),(200,100.000,100.000,0.07,0.14,NULL,'2026-04-17 07:40:20.372055',10.000,'PRCO0004',1,3),(201,180.000,180.000,0.02,0.29,NULL,'2026-04-17 07:40:20.431175',10.000,'PRCO0006',1,3),(202,9.000,9.000,1.50,2.08,NULL,'2026-04-17 07:40:20.505186',10.000,'PRNE0016',1,3),(203,8.000,8.000,1.50,2.71,NULL,'2026-04-17 07:40:20.582496',10.000,'PRNE0017',1,3),(204,6.000,6.000,0.90,1.46,NULL,'2026-04-17 07:40:20.660550',10.000,'PRPA0011',1,3),(205,17.000,16.000,2.00,3.33,NULL,'2026-04-17 07:40:20.747972',10.000,'FOCA0018',1,3),(206,77.000,77.000,0.33,0.83,NULL,'2026-04-17 07:40:20.809742',10.000,'FOMA0002',1,3),(207,7.000,7.000,5.50,7.92,NULL,'2026-04-17 07:40:20.879885',10.000,'PRMA0021',1,3),(208,7.000,7.000,3.75,5.00,NULL,'2026-04-17 07:40:20.955539',10.000,'PRMA0022',1,3),(209,12.000,12.000,0.50,0.75,NULL,'2026-04-17 07:40:21.028748',10.000,'PRTU0001',1,3),(210,12.000,12.000,0.50,0.75,NULL,'2026-04-17 07:40:21.101012',10.000,'PRTU0002',1,3),(211,13.000,13.000,0.25,0.42,NULL,'2026-04-17 07:40:21.165004',10.000,'FOST0007',1,3),(212,72.000,72.000,0.29,0.63,NULL,'2026-04-17 07:40:21.233205',10.000,'PRSE0010',1,3),(213,88.000,85.000,0.09,0.21,NULL,'2026-04-17 07:40:21.321248',10.000,'PRSE0011',1,3),(214,1.000,1.000,1.25,1.88,NULL,'2026-04-17 07:40:21.391363',10.000,'PRPO0001',1,3),(215,5.000,5.000,0.58,0.83,NULL,'2026-04-17 07:40:21.456272',10.000,'PRPR0008',1,3),(216,31.000,30.000,0.41,0.63,NULL,'2026-04-17 07:40:21.789634',10.000,'FOCA0019',1,3),(217,4.000,4.000,4.00,5.21,NULL,'2026-04-17 07:40:23.788350',10.000,'PRLI0003',1,3),(218,210.000,140.000,0.14,0.21,NULL,'2026-04-17 07:40:38.127265',10.000,'PRPR0009',1,3),(219,9.000,9.000,1.29,1.67,NULL,'2026-04-17 07:40:43.327140',10.000,'PRNE0004',1,3),(220,5.000,5.000,2.58,3.33,NULL,'2026-04-17 07:40:43.391617',10.000,'PRNE0003',1,3),(221,10.000,10.000,9.00,11.00,NULL,'2026-04-17 07:40:43.455723',10.000,'PRNE0005',1,3),(222,4.000,4.000,13.00,15.00,NULL,'2026-04-17 07:40:43.522033',10.000,'HAPA0005',1,3),(223,2.000,2.000,12.50,15.00,NULL,'2026-04-17 07:40:43.602520',10.000,'HAPA0006',1,3),(224,3.000,3.000,14.00,15.00,NULL,'2026-04-17 07:40:43.674263',10.000,'HAPA0007',1,3),(225,4.000,4.000,11.50,15.00,NULL,'2026-04-17 07:40:43.737378',10.000,'HAPA0003',1,3),(226,5.000,5.000,11.50,12.50,NULL,'2026-04-17 07:40:43.811081',10.000,'HAPA0001',1,3),(227,6.000,6.000,11.50,15.00,NULL,'2026-04-17 07:40:43.879922',10.000,'HAPA0002',1,3),(228,5.000,5.000,18.00,20.00,NULL,'2026-04-17 07:40:43.938482',10.000,'HAPA0004',1,3),(229,1.000,1.000,4.20,5.83,NULL,'2026-04-17 07:40:44.010252',10.000,'FOPA0005',1,3),(230,11.000,11.000,0.80,1.13,NULL,'2026-04-17 07:40:44.070156',10.000,'FOPA0001',1,3),(231,820.000,820.000,0.03,0.08,NULL,'2026-04-17 07:40:44.152848',10.000,'FOPA0002',1,3),(232,685.000,685.000,0.04,0.42,NULL,'2026-04-17 07:40:44.218302',10.000,'FOCA0012',1,3),(233,182.000,182.000,0.35,0.42,NULL,'2026-04-17 07:40:44.345732',10.000,'PRSE0001',1,3),(234,210.000,210.000,0.10,0.13,NULL,'2026-04-17 07:40:44.474392',10.000,'FOPA0006',1,3),(235,35.000,35.000,0.06,0.21,NULL,'2026-04-17 07:40:44.587330',10.000,'FOPA0008',1,3),(236,150.000,150.000,0.04,0.10,NULL,'2026-04-17 07:40:44.684417',10.000,'FOPA0009',1,3),(237,72.000,72.000,0.09,0.21,NULL,'2026-04-17 07:40:44.804996',10.000,'PRSE0003',1,3),(238,222.000,221.000,1.50,1.04,NULL,'2026-04-17 07:40:44.914028',10.000,'PRSE0004',1,3),(239,1149.000,1149.000,0.06,0.08,NULL,'2026-04-17 07:40:45.028452',10.000,'FOPA0010',1,3),(240,7.000,7.000,1.08,1.46,NULL,'2026-04-17 07:40:45.137617',10.000,'PRNE0014',1,3),(241,8.000,8.000,2.33,4.17,NULL,'2026-04-17 07:40:45.257088',10.000,'PRDI0017',1,3),(242,2.000,2.000,2.41,3.75,NULL,'2026-04-17 07:40:45.353031',10.000,'PRDI0018',1,3),(243,22.000,22.000,2.50,3.75,NULL,'2026-04-17 07:40:45.462366',10.000,'PRPA0004',1,3),(244,5.000,5.000,1.53,2.29,NULL,'2026-04-17 07:40:45.576809',10.000,'PRPA0006',1,3),(245,22.000,22.000,0.16,0.21,NULL,'2026-04-17 07:40:45.657270',10.000,'ARDI0002',1,3),(246,2.000,2.000,1.25,1.46,NULL,'2026-04-17 07:40:45.727374',10.000,'ARDI0003',1,3),(247,2.000,2.000,5.00,6.50,NULL,'2026-04-17 07:40:45.802796',10.000,'FOCA0020',1,3),(248,122.000,116.000,0.07,0.10,NULL,'2026-04-17 07:40:45.880112',10.000,'PRPI0002',1,3),(249,446.000,446.000,0.07,0.08,NULL,'2026-04-17 07:40:45.943162',10.000,'PRPI0003',1,3),(250,275.000,275.000,0.13,0.19,NULL,'2026-04-17 07:40:46.020242',10.000,'PRPI0004',1,3),(251,18.000,18.000,0.83,1.04,NULL,'2026-04-17 07:40:46.096998',10.000,'PRUS0016',1,3),(252,1.000,1.000,1.00,1.25,NULL,'2026-04-17 07:40:46.166176',10.000,'PRUS0017',1,3),(253,18.000,18.000,1.25,1.67,NULL,'2026-04-17 07:40:46.245610',10.000,'PRUS0018',1,3),(254,12.000,12.000,0.75,1.04,NULL,'2026-04-17 07:40:46.313830',10.000,'PRUS0008',1,3),(255,11.000,11.000,8.69,10.42,NULL,'2026-04-17 07:40:46.370509',10.000,'PRPR0010',1,3),(256,14.000,14.000,0.50,0.75,NULL,'2026-04-17 07:40:46.434162',10.000,'PRPO0004',1,3),(257,7.000,7.000,0.83,1.46,NULL,'2026-04-17 07:40:46.489960',10.000,'PRPO0034',1,3),(258,11.000,11.000,2.83,4.17,NULL,'2026-04-17 07:40:46.569743',10.000,'PRPO0024',1,3),(259,17.000,17.000,0.38,0.42,NULL,'2026-04-17 07:40:46.643593',10.000,'PRPO0023',1,3),(260,8.000,8.000,0.50,0.75,NULL,'2026-04-17 07:40:46.708453',10.000,'PRPO0006',1,3),(261,6.000,6.000,1.67,1.46,NULL,'2026-04-17 07:40:46.786109',10.000,'PRPO0021',1,3),(262,16.000,16.000,1.08,1.46,NULL,'2026-04-17 07:40:46.871821',10.000,'PRPO0008',1,3),(263,13.000,13.000,0.13,0.21,NULL,'2026-04-17 07:40:46.937018',10.000,'PRPO0009',1,3),(264,3.000,3.000,0.00,0.63,NULL,'2026-04-17 07:40:47.017524',10.000,'PRPO0010',1,3),(265,7.000,7.000,0.41,0.83,NULL,'2026-04-17 07:40:47.094600',10.000,'PRPO0014',1,3),(266,4.000,4.000,1.16,1.46,NULL,'2026-04-17 07:40:47.169240',10.000,'PRPO0015',1,3),(267,7.000,7.000,0.50,0.75,NULL,'2026-04-17 07:40:47.236288',10.000,'PRPO0017',1,3),(268,9.000,9.000,0.83,1.04,NULL,'2026-04-17 07:40:47.309866',10.000,'PRPO0020',1,3),(269,2.000,2.000,0.92,1.25,NULL,'2026-04-17 07:40:47.386373',10.000,'PRPO0016',1,3),(270,5.000,5.000,0.92,1.46,NULL,'2026-04-17 07:40:47.466168',10.000,'PRPO0028',1,3),(271,12.000,12.000,1.08,1.46,NULL,'2026-04-17 07:40:47.534873',10.000,'PRPO0026',1,3),(272,12.000,12.000,0.08,2.92,NULL,'2026-04-17 07:40:47.605716',10.000,'PRPO0025',1,3),(273,18.000,18.000,0.12,0.21,NULL,'2026-04-17 07:40:47.669842',10.000,'PRPO0035',1,3),(274,16.000,16.000,0.12,0.21,NULL,'2026-04-17 07:40:47.740475',10.000,'PRPO0033',1,3),(275,12.000,12.000,0.32,0.42,NULL,'2026-04-17 07:40:47.813886',10.000,'PRFR0001',1,3),(276,53.000,53.000,0.33,0.63,NULL,'2026-04-17 07:40:47.900181',10.000,'ARDI0004',1,3),(277,4.000,4.000,0.54,1.04,NULL,'2026-04-17 07:40:47.985576',10.000,'ARDI0005',1,3),(278,18.000,18.000,1.87,2.92,NULL,'2026-04-17 07:40:48.065077',10.000,'ARDI0006',1,3),(279,7.000,7.000,1.08,1.67,NULL,'2026-04-17 07:40:48.166714',10.000,'PRPA0007',1,3),(280,31.000,31.000,0.38,0.54,NULL,'2026-04-17 07:40:48.243191',10.000,'PRPA0009',1,3),(281,12.000,11.000,10.00,12.00,NULL,'2026-04-17 07:40:48.306561',10.000,'PRPO0038',1,3),(282,7.000,7.000,0.83,1.46,NULL,'2026-04-17 07:40:48.386726',10.000,'PRPO0011',1,3),(283,4.000,4.000,0.38,0.83,NULL,'2026-04-17 07:40:48.452072',10.000,'PRPO0036',1,3),(284,5.000,5.000,1.50,1.88,NULL,'2026-04-17 07:40:48.525517',10.000,'PRPR0011',1,3),(285,14.000,14.000,1.50,1.88,NULL,'2026-04-17 07:40:48.619167',10.000,'PRPO0037',1,3),(286,23.000,23.000,2.29,2.92,NULL,'2026-04-17 07:40:48.698822',10.000,'PRNE0006',1,3),(287,2.000,2.000,3.80,5.21,NULL,'2026-04-17 07:40:48.770077',10.000,'PRDI0011',1,3),(288,12.000,12.000,0.78,1.17,NULL,'2026-04-17 07:40:48.837497',10.000,'PRPR0012',1,3),(289,121.000,121.000,1.52,1.75,NULL,'2026-04-17 07:40:48.907140',10.000,'PRPR0013',1,3),(290,217.000,203.000,0.06,0.10,'2026-11-01','2026-04-17 07:40:48.971715',10.000,'PRMA0015',1,3),(291,31.000,28.000,0.10,0.21,NULL,'2026-04-17 07:40:49.062988',10.000,'PREM0005',1,3),(292,61.000,61.000,0.27,0.42,NULL,'2026-04-17 07:40:49.134053',10.000,'FOEN0005',1,3),(293,20.000,20.000,0.50,0.63,NULL,'2026-04-17 07:40:49.188227',10.000,'FOEN0006',1,3),(294,4000.000,4000.000,0.01,0.01,NULL,'2026-04-17 07:40:49.271734',10.000,'FOEN0007',1,3),(295,3800.000,3800.000,0.01,0.02,NULL,'2026-04-17 07:40:49.353206',10.000,'PRDI0019',1,3),(296,400.000,400.000,0.03,0.08,NULL,'2026-04-17 07:40:49.416925',10.000,'FOEN0008',1,3),(297,6.000,5.000,0.73,1.25,NULL,'2026-04-17 07:40:49.489878',10.000,'PRSA0022',1,3),(298,10.000,10.000,0.50,0.63,NULL,'2026-04-17 07:40:49.578528',10.000,'PRSA0023',1,3),(299,9.000,9.000,1.00,1.46,NULL,'2026-04-17 07:40:49.650166',10.000,'PRSA0024',1,3),(300,3.000,3.000,0.75,0.63,NULL,'2026-04-17 07:40:49.715861',10.000,'PRSA0025',1,3),(301,9.000,9.000,1.25,2.08,NULL,'2026-04-17 07:40:49.785229',10.000,'PRSA0002',1,3),(302,11.000,11.000,0.45,1.25,NULL,'2026-04-17 07:40:49.852251',10.000,'PRSA0001',1,3),(303,11.000,11.000,0.75,1.04,NULL,'2026-04-17 07:40:49.950006',10.000,'PRSA0003',1,3),(304,9.000,9.000,0.50,0.63,NULL,'2026-04-17 07:40:50.029120',10.000,'PRSA0004',1,3),(305,33.000,31.000,0.83,1.04,NULL,'2026-04-17 07:40:50.100493',10.000,'PRSA0005',1,3),(306,7.000,7.000,0.33,0.63,NULL,'2026-04-17 07:40:50.163113',10.000,'PRSA0006',1,3),(307,63.000,63.000,1.41,2.08,NULL,'2026-04-17 07:40:50.231605',10.000,'PRSA0007',1,3),(308,65.000,65.000,0.64,1.04,NULL,'2026-04-17 07:40:50.298551',10.000,'PRSA0017',1,3),(309,8.000,8.000,0.38,0.63,NULL,'2026-04-17 07:40:50.365130',10.000,'PRSA0008',1,3),(310,63.000,61.000,0.31,0.63,NULL,'2026-04-17 07:40:50.438433',10.000,'PRSA0009',1,3),(311,14.000,13.750,0.80,1.17,NULL,'2026-04-17 07:40:50.499706',10.000,'PRSA0019',1,3),(312,75.000,69.500,1.04,1.25,NULL,'2026-04-17 07:40:50.596714',10.000,'PRSA0015',1,3),(313,133.000,133.000,0.98,1.25,NULL,'2026-04-17 07:40:50.694832',10.000,'PRSA0016',1,3),(314,5.000,5.000,1.58,2.50,NULL,'2026-04-17 07:40:50.759696',10.000,'PRSA0021',1,3),(315,4.000,4.000,0.58,1.25,NULL,'2026-04-17 07:40:50.849497',10.000,'ARCO0006',1,3),(316,5.000,5.000,0.43,0.63,NULL,'2026-04-17 07:40:50.949238',10.000,'ARCO0007',1,3),(317,39.000,39.000,0.08,0.21,NULL,'2026-04-17 07:40:51.023656',10.000,'ARCO0008',1,3),(318,12.000,12.000,2.00,2.50,NULL,'2026-04-17 07:40:51.090434',10.000,'PRPR0014',1,3),(319,12.000,12.000,0.96,1.15,NULL,'2026-04-17 07:40:51.172882',10.000,'PRPR0015',1,3),(320,149.000,149.000,0.25,0.33,NULL,'2026-04-17 07:40:51.253229',10.000,'PRPR0016',1,3),(321,1.000,1.000,1.67,2.29,NULL,'2026-04-17 07:40:51.331395',10.000,'PRCR0012',1,3),(322,8.000,8.000,1.21,1.88,NULL,'2026-04-17 07:40:51.417155',10.000,'PRCR0013',1,3),(323,21.000,21.000,0.71,0.83,NULL,'2026-04-17 07:40:51.486643',10.000,'HASI0003',1,3),(324,1.000,1.000,5.00,2.92,NULL,'2026-04-17 07:40:51.551397',10.000,'HASI0004',1,3),(325,36.000,36.000,1.42,2.08,NULL,'2026-04-17 07:40:51.637440',10.000,'HASI0006',1,3),(326,12.000,12.000,1.07,1.75,NULL,'2026-04-17 07:40:51.718816',10.000,'HASI0005',1,3),(327,10.000,10.000,0.33,0.63,NULL,'2026-04-17 07:40:51.789360',10.000,'PRPO0027',1,3),(328,16.000,16.000,3.04,4.38,NULL,'2026-04-17 07:40:51.849226',10.000,'HASO0011',1,3),(329,21.000,21.000,0.29,0.63,NULL,'2026-04-17 07:40:51.922090',10.000,'FOMA0003',1,3),(330,18.000,18.000,1.08,1.46,NULL,'2026-04-17 07:40:52.007433',10.000,'HASO0002',1,3),(331,9.000,9.000,1.17,1.67,NULL,'2026-04-17 07:40:52.082552',10.000,'HASO0005',1,3),(332,49.000,49.000,0.16,0.21,NULL,'2026-04-17 07:40:52.197500',10.000,'HASO0004',1,3),(333,13.000,13.000,1.17,1.46,NULL,'2026-04-17 07:40:52.285577',10.000,'HASO0006',1,3),(334,16.000,16.000,0.50,0.63,NULL,'2026-04-17 07:40:52.365907',10.000,'HASO0003',1,3),(335,2.000,2.000,1.20,1.67,NULL,'2026-04-17 07:40:52.432061',10.000,'HASO0012',1,3),(336,10.000,10.000,2.98,3.33,NULL,'2026-04-17 07:40:52.528716',10.000,'HASO0008',1,3),(337,1.000,1.000,0.75,1.04,NULL,'2026-04-17 07:40:52.623416',10.000,'HASO0007',1,3),(338,18.000,18.000,0.78,1.04,NULL,'2026-04-17 07:40:52.705022',10.000,'PRPA0012',1,3),(339,740.000,716.000,0.11,0.21,NULL,'2026-04-17 07:40:52.774794',10.000,'FOCA0021',1,3),(340,548.000,548.000,0.11,0.21,NULL,'2026-04-17 07:40:52.863842',10.000,'FOCA0023',1,3),(341,660.000,660.000,0.11,0.21,NULL,'2026-04-17 07:40:52.943669',10.000,'FOCA0022',1,3),(342,76.000,71.000,0.90,1.46,NULL,'2026-04-17 07:40:53.017098',10.000,'PRMA0023',1,3),(343,37.000,37.000,0.45,0.54,NULL,'2026-04-17 07:40:53.082744',10.000,'PRBO0020',1,3),(344,19.000,19.000,0.13,0.21,NULL,'2026-04-17 07:40:53.167295',10.000,'ARCO0005',1,3),(345,12.000,12.000,0.13,0.42,NULL,'2026-04-17 07:40:53.248126',10.000,'FOCA0024',1,3),(346,4.000,4.000,12.50,15.00,NULL,'2026-04-17 07:40:53.323196',10.000,'PRUS0021',1,3),(347,118.000,118.000,0.09,0.10,NULL,'2026-04-17 07:40:53.385608',10.000,'NEDI0001',1,3),(348,43.000,43.000,0.21,0.33,NULL,'2026-04-17 07:40:53.448201',10.000,'PRTO0001',1,3),(349,1.000,1.000,0.79,2.08,NULL,'2026-04-17 07:40:53.520199',10.000,'PRCR0001',1,3),(350,498.000,498.000,0.11,0.04,NULL,'2026-04-17 07:40:53.627707',10.000,'FOST0011',1,3),(351,2.000,2.000,1.08,1.46,NULL,'2026-04-17 07:40:53.700255',10.000,'PRMA0014',1,3),(352,7.000,7.000,0.83,1.00,NULL,'2026-04-17 07:40:53.765341',10.000,'PRUS0015',1,3),(353,100.000,100.000,0.03,0.17,NULL,'2026-04-17 07:40:53.829309',10.000,'PRCO0008',1,3),(354,125.000,125.000,0.01,0.08,NULL,'2026-04-17 07:40:53.904416',10.000,'PRCO0007',1,3),(355,5.000,5.000,0.79,1.04,NULL,'2026-04-17 07:40:53.964488',10.000,'PRSE0005',1,3),(356,41.000,41.000,1.58,2.50,NULL,'2026-04-17 07:40:54.041314',10.000,'NENE0001',1,3),(357,5.000,5.000,0.75,1.04,NULL,'2026-04-17 07:40:54.116360',10.000,'PRMA0016',1,3),(358,5.000,5.000,9.00,10.00,NULL,'2026-04-17 07:40:54.181272',10.000,'PRCR0022',1,3),(359,500.000,473.000,0.01,0.02,NULL,'2026-04-24 13:18:24.093820',10.000,'FOPA0011',1,4);
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
  `quantite` decimal(12,3) NOT NULL,
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
  CONSTRAINT `stock_lignesortie_sortie_id_71da70c4_fk_stock_sortie_id` FOREIGN KEY (`sortie_id`) REFERENCES `stock_sortie` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=116 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_lignesortie`
--

LOCK TABLES `stock_lignesortie` WRITE;
/*!40000 ALTER TABLE `stock_lignesortie` DISABLE KEYS */;
INSERT INTO `stock_lignesortie` VALUES (1,2.000,1.00,'2026-03-23 16:30:19.814153','PRSE0005',1,1),(2,2.000,1.00,'2026-03-23 16:32:30.558161','PRUS0015',1,2),(3,1.000,1.04,'2026-04-24 13:31:03.124148','PRDE0008',1,3),(4,1.000,0.63,'2026-04-24 13:31:03.281433','PRSA0009',1,3),(5,3.000,0.02,'2026-04-24 13:31:03.297056','FOPA0011',1,3),(6,1.000,0.21,'2026-04-24 13:31:03.706416','PRSE0011',1,3),(7,2.000,0.10,'2026-04-24 13:31:04.407325','PRPI0002',1,3),(8,2.000,0.06,'2026-04-24 13:31:04.507296','PRBI0010',1,3),(9,1.000,0.08,'2026-04-24 13:31:04.607413','PRBI0005',1,3),(10,2.000,0.21,'2026-04-24 13:31:04.623041','FOCA0011',1,3),(11,23.000,0.21,'2026-04-24 13:31:04.669910','FOCA0021',1,3),(12,6.000,0.01,'2026-04-24 13:53:30.915076','PRBI0011',1,4),(13,1.000,1.46,'2026-04-24 13:53:30.946231','PRMA0023',1,4),(14,1.000,0.06,'2026-04-24 13:53:30.961855','PRBI0010',1,4),(15,1.000,0.02,'2026-04-24 13:53:30.995161','PRBI0012',1,4),(16,15.000,0.01,'2026-04-24 13:53:31.010787','PRBI0011',1,4),(17,2.000,0.21,'2026-04-24 13:53:31.042031','PRBI0008',1,4),(18,3.000,0.01,'2026-04-24 13:53:31.073281','PRBI0011',1,4),(19,2.000,1.25,'2026-04-24 13:53:31.088904','PRSA0015',1,4),(20,1.000,0.63,'2026-04-24 13:53:31.120151','PRDE0005',1,4),(21,1.000,1.04,'2026-04-24 13:53:31.135789','PRSA0005',1,4),(22,1.000,1.46,'2026-04-24 13:53:31.164224','PRMA0023',1,4),(23,5.000,0.21,'2026-04-24 13:53:31.179839','PRPR0009',1,4),(24,1.000,1.04,'2026-04-29 09:41:03.871189','PRDE0008',1,5),(25,15.000,0.02,'2026-04-29 15:36:08.109501','FOPA0011',1,6),(26,1.000,1.25,'2026-04-29 15:36:08.134754','PRSA0022',1,6),(27,15.000,0.01,'2026-04-29 15:36:08.150377','PRBI0011',1,6),(28,1.000,1.25,'2026-04-29 15:36:08.181626','PRBI0009',1,6),(29,31.000,0.02,'2026-04-29 15:43:03.228174','PRBI0012',1,7),(30,1.000,0.21,'2026-04-29 15:43:03.259421','PRPR0009',1,7),(31,1.000,2.50,'2026-04-29 15:43:03.275061','PRCR0024',1,7),(32,20.000,0.02,'2026-04-29 15:43:03.290683','PRBI0012',1,7),(33,1.000,3.33,'2026-04-29 15:43:03.306290','FOCA0018',1,7),(34,2.000,0.10,'2026-04-29 15:43:03.330103','PRPI0002',1,7),(35,1.000,0.08,'2026-04-29 15:43:03.345745','PRBI0005',1,7),(36,3.000,0.04,'2026-04-29 15:43:03.361368','FOEN0003',1,7),(37,1.000,0.21,'2026-04-29 15:43:03.376992','PRBI0008',1,7),(38,1.000,1.04,'2026-04-29 15:46:18.881161','PRBO0016',1,8),(39,1.000,0.83,'2026-04-29 15:46:18.904393','PRBO0002',1,8),(40,15.000,0.21,'2026-04-29 15:46:18.920018','PRPR0009',1,8),(41,1.000,0.63,'2026-04-29 16:05:08.905202','PRSA0009',1,9),(42,3.000,0.02,'2026-04-29 16:05:08.936438','FOPA0011',1,9),(43,1.000,0.21,'2026-04-29 16:05:08.952061','PRSE0011',1,9),(44,2.000,0.10,'2026-04-29 16:05:08.972594','PRPI0002',1,9),(45,2.000,0.06,'2026-04-29 16:05:09.003852','PRBI0010',1,9),(46,1.000,0.08,'2026-04-29 16:05:09.019483','PRBI0005',1,9),(47,1.000,0.21,'2026-04-29 16:05:09.035108','FOCA0011',1,9),(48,1.000,0.21,'2026-04-29 16:05:09.050719','FOCA0021',1,9),(49,1.000,0.21,'2026-04-29 16:05:09.081979','FOCA0011',1,9),(50,6.000,0.01,'2026-05-01 12:12:47.928773','PRBI0011',1,10),(51,1.000,1.46,'2026-05-01 12:12:47.960028','PRMA0023',1,10),(52,1.000,0.06,'2026-05-01 12:12:47.975647','PRBI0010',1,10),(53,1.000,0.02,'2026-05-01 12:12:47.991270','PRBI0012',1,10),(54,15.000,0.01,'2026-05-01 12:12:48.006890','PRBI0011',1,10),(55,2.000,0.21,'2026-05-01 12:12:48.022512','PRBI0008',1,10),(56,3.000,0.01,'2026-05-01 12:12:48.038141','PRBI0011',1,10),(57,0.250,1.17,'2026-05-01 12:12:48.053761','PRSA0019',1,10),(58,1.000,1.25,'2026-05-01 12:12:48.100649','PRSA0015',1,10),(59,2.000,1.25,'2026-05-01 12:18:30.608538','PRSA0015',1,11),(60,1.000,0.63,'2026-05-01 12:18:30.625118','PRDE0005',1,11),(61,1.000,1.04,'2026-05-01 12:18:30.641825','PRSA0005',1,11),(62,1.000,1.46,'2026-05-01 12:18:30.659628','PRMA0023',1,11),(63,0.500,6.88,'2026-05-01 12:18:30.659628','PRPR0017',1,11),(64,5.000,0.21,'2026-05-01 12:18:30.676738','PRPR0009',1,11),(65,1.000,16.00,'2026-05-01 12:20:02.179591','PRHU0006',1,12),(66,5.000,0.08,'2026-05-01 13:39:30.988757','PRBI0005',1,13),(67,14.000,0.02,'2026-05-01 13:39:31.004422','PRBI0012',1,13),(68,15.000,0.01,'2026-05-01 13:39:31.035633','PRBI0011',1,13),(69,2.000,0.21,'2026-05-01 13:39:31.051260','PRBI0008',1,13),(70,1.000,0.21,'2026-05-01 13:46:01.762268','PRBI0002',1,14),(71,1.000,0.04,'2026-05-01 13:46:01.777857','FOEN0003',1,14),(72,1.000,0.21,'2026-05-01 13:46:01.793482','PRSE0011',1,14),(73,6.000,0.02,'2026-05-01 13:46:01.809120','FOPA0011',1,14),(74,1.000,0.21,'2026-05-01 13:46:01.824745','PRBI0008',1,14),(75,2.000,0.21,'2026-05-01 13:46:01.840355','PRBO0009',1,14),(76,1.000,0.21,'2026-05-01 13:46:01.855993','FOCA0011',1,14),(77,1.000,0.21,'2026-05-01 13:46:01.871617','PRBI0008',1,14),(78,0.500,1.25,'2026-05-01 13:46:01.887227','PRSA0015',1,14),(79,4.000,0.02,'2026-05-01 13:46:01.902851','PRBI0012',1,14),(80,12.000,0.02,'2026-05-03 15:04:43.957446','PRBI0012',1,15),(81,2.000,0.21,'2026-05-03 15:04:43.973057','PRBI0008',1,15),(82,1.000,0.63,'2026-05-03 15:04:44.004305','ARDI0001',1,15),(83,10.000,0.02,'2026-05-03 15:04:44.019929','PRBI0012',1,15),(84,10.000,0.10,'2026-05-03 15:10:02.570727','PRMA0015',1,16),(85,1.000,0.42,'2026-05-03 15:10:02.601992','PRMA0002',1,16),(86,1.000,1.88,'2026-05-03 15:10:02.617592','PRBE0002',1,16),(87,1.000,1.46,'2026-05-03 15:10:02.633216','PRMA0023',1,16),(88,8.000,0.21,'2026-05-03 15:10:02.665213','PRPR0009',1,16),(89,1.000,0.21,'2026-05-03 15:18:55.468261','PRBI0002',1,17),(90,1.000,0.21,'2026-05-03 15:18:55.483888','PRBI0008',1,17),(91,1.000,0.21,'2026-05-03 15:18:55.499507','PRBI0002',1,17),(92,1.000,1.04,'2026-05-03 15:18:55.515147','PRSE0004',1,17),(93,4.000,0.10,'2026-05-03 15:18:55.530756','PRMA0015',1,17),(94,1.000,0.21,'2026-05-03 15:18:55.546379','PRBO0009',1,17),(95,1.000,0.04,'2026-05-03 15:18:55.562002','PRBI0001',1,17),(96,4.000,0.21,'2026-05-03 15:18:55.577625','PRPR0009',1,17),(97,30.000,0.21,'2026-05-03 15:29:37.961250','PRPR0009',1,18),(98,2.000,0.21,'2026-05-03 15:29:37.976876','PRBI0002',1,18),(99,2.000,0.21,'2026-05-03 15:29:38.008121','PRBI0008',1,18),(100,1.000,0.63,'2026-05-03 15:29:38.023747','FOCA0019',1,18),(101,1.000,0.42,'2026-05-03 15:29:38.039370','ARCO0014',1,18),(102,1.000,0.21,'2026-05-03 15:29:38.055010','FOCA0011',1,18),(103,1.000,0.08,'2026-05-03 15:29:38.086242','PRBI0005',1,18),(104,2.000,0.08,'2026-05-03 15:29:38.101876','PRBI0005',1,18),(105,2.000,0.04,'2026-05-03 15:29:38.117505','PRBI0001',1,18),(106,2.000,0.02,'2026-05-03 15:29:38.133121','PRBI0012',1,18),(107,1.000,12.00,'2026-05-03 15:43:10.407142','PRPO0038',1,19),(108,2.000,0.06,'2026-05-03 15:54:46.897080','PRBI0010',1,20),(109,1.000,0.08,'2026-05-03 15:54:46.928327','FOEN0004',1,20),(110,10.000,0.02,'2026-05-03 15:54:46.943971','PRBI0012',1,20),(111,3.000,0.21,'2026-05-03 15:54:46.959590','PREM0005',1,20),(112,10.000,0.02,'2026-05-03 15:54:46.975199','PRCO0002',1,20),(113,1.000,0.50,'2026-05-03 15:54:46.980138','PRBO0007',1,20),(114,8.000,0.02,'2026-05-03 15:54:47.012416','PRBI0012',1,20),(115,2.000,0.21,'2026-05-03 15:54:47.028039','PRPR0009',1,20);
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
  `quantite` decimal(12,3) NOT NULL,
  `prix_achat` decimal(10,2) NOT NULL,
  `prix_vente` decimal(10,2) NOT NULL,
  `ligne_sortie_id` bigint NOT NULL,
  `lot_entree_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_lignesortielot_lot_entree_id_46ef78be_fk_stock_lig` (`lot_entree_id`),
  KEY `stock_ligne_ligne_s_c7f781_idx` (`ligne_sortie_id`,`lot_entree_id`),
  CONSTRAINT `stock_lignesortielot_ligne_sortie_id_aa9087ab_fk_stock_lig` FOREIGN KEY (`ligne_sortie_id`) REFERENCES `stock_lignesortie` (`id`),
  CONSTRAINT `stock_lignesortielot_lot_entree_id_46ef78be_fk_stock_lig` FOREIGN KEY (`lot_entree_id`) REFERENCES `stock_ligneentree` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=116 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_lignesortielot`
--

LOCK TABLES `stock_lignesortielot` WRITE;
/*!40000 ALTER TABLE `stock_lignesortielot` DISABLE KEYS */;
INSERT INTO `stock_lignesortielot` VALUES (1,2.000,0.00,1.00,1,2),(2,2.000,0.00,1.00,2,3),(3,1.000,0.58,1.04,3,121),(4,1.000,0.31,0.63,4,310),(5,3.000,0.01,0.02,5,359),(6,1.000,0.09,0.21,6,213),(7,2.000,0.07,0.10,7,248),(8,2.000,0.03,0.06,8,46),(9,1.000,0.01,0.08,9,34),(10,2.000,0.17,0.21,10,69),(11,23.000,0.11,0.21,11,339),(12,6.000,0.01,0.01,12,44),(13,1.000,0.90,1.46,13,342),(14,1.000,0.03,0.06,14,46),(15,1.000,0.02,0.02,15,45),(16,15.000,0.01,0.01,16,44),(17,2.000,0.11,0.21,17,36),(18,3.000,0.01,0.01,18,44),(19,2.000,1.04,1.25,19,312),(20,1.000,0.41,0.63,20,119),(21,1.000,0.83,1.04,21,305),(22,1.000,0.90,1.46,22,342),(23,5.000,0.14,0.21,23,218),(24,1.000,0.58,1.04,24,121),(25,15.000,0.01,0.02,25,359),(26,1.000,0.73,1.25,26,297),(27,15.000,0.01,0.01,27,44),(28,1.000,0.95,1.25,28,37),(29,31.000,0.02,0.02,29,45),(30,1.000,0.14,0.21,30,218),(31,1.000,1.50,2.50,31,198),(32,20.000,0.02,0.02,32,45),(33,1.000,2.00,3.33,33,205),(34,2.000,0.07,0.10,34,248),(35,1.000,0.01,0.08,35,34),(36,3.000,0.02,0.04,36,133),(37,1.000,0.11,0.21,37,36),(38,1.000,0.70,1.04,38,186),(39,1.000,0.50,0.83,39,123),(40,15.000,0.14,0.21,40,218),(41,1.000,0.31,0.63,41,310),(42,3.000,0.01,0.02,42,359),(43,1.000,0.09,0.21,43,213),(44,2.000,0.07,0.10,44,248),(45,2.000,0.03,0.06,45,46),(46,1.000,0.01,0.08,46,34),(47,1.000,0.17,0.21,47,69),(48,1.000,0.11,0.21,48,339),(49,1.000,0.17,0.21,49,69),(50,6.000,0.01,0.01,50,44),(51,1.000,0.90,1.46,51,342),(52,1.000,0.03,0.06,52,46),(53,1.000,0.02,0.02,53,45),(54,15.000,0.01,0.01,54,44),(55,2.000,0.11,0.21,55,36),(56,3.000,0.01,0.01,56,44),(57,0.250,0.80,1.17,57,311),(58,1.000,1.04,1.25,58,312),(59,2.000,1.04,1.25,59,312),(60,1.000,0.41,0.63,60,119),(61,1.000,0.83,1.04,61,305),(62,1.000,0.90,1.46,62,342),(63,0.500,5.40,6.88,63,108),(64,5.000,0.14,0.21,64,218),(65,1.000,12.25,16.00,65,170),(66,5.000,0.01,0.08,66,34),(67,14.000,0.02,0.02,67,45),(68,15.000,0.01,0.01,68,44),(69,2.000,0.11,0.21,69,36),(70,1.000,0.10,0.21,70,31),(71,1.000,0.02,0.04,71,133),(72,1.000,0.09,0.21,72,213),(73,6.000,0.01,0.02,73,359),(74,1.000,0.11,0.21,74,36),(75,2.000,0.01,0.21,75,181),(76,1.000,0.17,0.21,76,69),(77,1.000,0.11,0.21,77,36),(78,0.500,1.04,1.25,78,312),(79,4.000,0.02,0.02,79,45),(80,12.000,0.02,0.02,80,45),(81,2.000,0.11,0.21,81,36),(82,1.000,0.66,0.63,82,103),(83,10.000,0.02,0.02,83,45),(84,10.000,0.06,0.10,84,290),(85,1.000,0.24,0.42,85,79),(86,1.000,1.41,1.88,86,39),(87,1.000,0.90,1.46,87,342),(88,8.000,0.14,0.21,88,218),(89,1.000,0.10,0.21,89,31),(90,1.000,0.11,0.21,90,36),(91,1.000,0.10,0.21,91,31),(92,1.000,1.50,1.04,92,238),(93,4.000,0.06,0.10,93,290),(94,1.000,0.01,0.21,94,181),(95,1.000,0.02,0.04,95,30),(96,4.000,0.14,0.21,96,218),(97,30.000,0.14,0.21,97,218),(98,2.000,0.10,0.21,98,31),(99,2.000,0.11,0.21,99,36),(100,1.000,0.41,0.63,100,216),(101,1.000,0.29,0.42,101,92),(102,1.000,0.17,0.21,102,69),(103,1.000,0.01,0.08,103,34),(104,2.000,0.01,0.08,104,34),(105,2.000,0.02,0.04,105,30),(106,2.000,0.02,0.02,106,45),(107,1.000,10.00,12.00,107,281),(108,2.000,0.03,0.06,108,46),(109,1.000,0.05,0.08,109,134),(110,10.000,0.02,0.02,110,45),(111,3.000,0.10,0.21,111,291),(112,10.000,0.01,0.02,112,11),(113,1.000,0.29,0.50,113,177),(114,8.000,0.02,0.02,114,45),(115,2.000,0.14,0.21,115,218);
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
  `reference_piece` varchar(100) NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `entree_id` bigint DEFAULT NULL,
  `sortie_id` bigint DEFAULT NULL,
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  `content_type_id` int DEFAULT NULL,
  `object_id` int unsigned DEFAULT NULL,
  `utilisateur_id` bigint DEFAULT NULL,
  `motif` longtext,
  `moyen` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_mouvementcaisse_devise_id_338fdfd8_fk_stock_devise_id` (`devise_id`),
  KEY `stock_mouvementcaisse_entree_id_e4bddbfa_fk_stock_entree_id` (`entree_id`),
  KEY `stock_mouvementcaisse_sortie_id_a52a187c_fk_stock_sortie_id` (`sortie_id`),
  KEY `stock_mouve_entrepr_bd2459_idx` (`entreprise_id`),
  KEY `stock_mouve_succurs_0d3ad9_idx` (`succursale_id`),
  KEY `stock_mouve_entrepr_c4f4c1_idx` (`entreprise_id`,`succursale_id`),
  KEY `stock_mouvementcaisse_utilisateur_id_75557a2a_fk_users_user_id` (`utilisateur_id`),
  KEY `stock_mouve_content_354bb1_idx` (`content_type_id`,`object_id`),
  CONSTRAINT `stock_mouvementcaiss_content_type_id_ad2b8e25_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `stock_mouvementcaiss_entreprise_id_3e634145_fk_stock_ent` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_mouvementcaiss_succursale_id_d90c42e9_fk_stock_suc` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`),
  CONSTRAINT `stock_mouvementcaisse_devise_id_338fdfd8_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_mouvementcaisse_entree_id_e4bddbfa_fk_stock_entree_id` FOREIGN KEY (`entree_id`) REFERENCES `stock_entree` (`id`),
  CONSTRAINT `stock_mouvementcaisse_sortie_id_a52a187c_fk_stock_sortie_id` FOREIGN KEY (`sortie_id`) REFERENCES `stock_sortie` (`id`),
  CONSTRAINT `stock_mouvementcaisse_utilisateur_id_75557a2a_fk_users_user_id` FOREIGN KEY (`utilisateur_id`) REFERENCES `users_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_mouvementcaisse`
--

LOCK TABLES `stock_mouvementcaisse` WRITE;
/*!40000 ALTER TABLE `stock_mouvementcaisse` DISABLE KEYS */;
INSERT INTO `stock_mouvementcaisse` VALUES (1,'2026-03-23 16:30:19.838142',2.00,'ENTREE','',1,NULL,1,1,NULL,NULL,NULL,NULL,'[MANUEL]',NULL),(2,'2026-03-23 16:32:30.574160',2.00,'ENTREE','',1,NULL,2,1,NULL,NULL,NULL,NULL,'[MANUEL]',NULL),(3,'2026-04-17 06:51:20.556056',617.75,'ENTREE','',1,NULL,NULL,1,NULL,NULL,NULL,1,'Capital','Cash'),(4,'2026-04-17 07:00:25.224189',7274.88,'ENTREE','',1,NULL,NULL,1,NULL,NULL,NULL,1,'ajout capital','Cash'),(5,'2026-04-17 07:38:51.956395',27.02,'ENTREE','',1,NULL,NULL,1,NULL,NULL,NULL,1,'capitale ajout','Cash'),(6,'2026-04-17 07:40:54.260727',7923.65,'SORTIE','',1,3,NULL,1,NULL,NULL,NULL,1,'Approvisionnement entrée #3 — 7923.65',NULL),(7,'2026-04-24 12:36:23.994211',4.20,'ENTREE','',1,NULL,NULL,1,NULL,NULL,NULL,1,'ADD CAPITAL PAPIER','Cash'),(8,'2026-04-24 13:16:44.801944',0.80,'ENTREE','',1,NULL,NULL,1,NULL,NULL,NULL,1,'cap','Cash'),(9,'2026-04-24 13:18:24.274746',5.00,'SORTIE','APPRO-4-USD',1,4,NULL,1,NULL,17,4,NULL,'Approvisionnement entrée #4 — 5.00',NULL),(10,'2026-04-24 13:31:04.669910',7.59,'ENTREE','VENT-3-USD',1,NULL,3,1,NULL,20,3,NULL,'Vente sortie #3 — 7.59',NULL),(11,'2026-04-24 13:53:31.197540',8.88,'ENTREE','VENT-4-USD',1,NULL,4,1,NULL,20,4,NULL,'Vente sortie #4 — 8.88',NULL),(12,'2026-04-29 09:41:03.884984',1.04,'ENTREE','VENT-5-USD',1,NULL,5,1,NULL,20,5,NULL,'Vente sortie #5 — 1.04',NULL),(13,'2026-04-29 15:36:08.197253',2.95,'ENTREE','VENT-6-USD',1,NULL,6,1,NULL,20,6,NULL,'Vente sortie #6 — 2.95',NULL),(14,'2026-04-29 15:43:03.392600',7.67,'ENTREE','VENT-7-USD',1,NULL,7,1,NULL,20,7,NULL,'Vente sortie #7 — 7.67',NULL),(15,'2026-04-29 15:46:18.920018',5.02,'ENTREE','VENT-8-USD',1,NULL,8,1,NULL,20,8,NULL,'Vente sortie #8 — 5.02',NULL),(16,'2026-04-29 16:05:09.081979',1.93,'ENTREE','VENT-9-USD',1,NULL,9,1,NULL,20,9,NULL,'Vente sortie #9 — 1.93',NULL),(17,'2026-05-01 12:12:48.100649',3.74,'ENTREE','VENT-10-USD',1,NULL,10,1,NULL,20,10,NULL,'Vente sortie #10 — 3.74',NULL),(18,'2026-05-01 12:18:30.692382',10.12,'ENTREE','VENT-11-USD',1,NULL,11,1,NULL,20,11,NULL,'Vente sortie #11 — 10.12',NULL),(19,'2026-05-01 12:20:02.179591',16.00,'ENTREE','VENT-12-USD',1,NULL,12,1,NULL,20,12,NULL,'Vente sortie #12 — 16.00',NULL),(20,'2026-05-01 13:39:31.066873',1.25,'ENTREE','VENT-13-USD',1,NULL,13,1,NULL,20,13,NULL,'Vente sortie #13 — 1.25',NULL),(21,'2026-05-01 13:46:01.918475',2.34,'ENTREE','VENT-14-USD',1,NULL,14,1,NULL,20,14,NULL,'Vente sortie #14 — 2.34',NULL),(22,'2026-05-03 15:04:44.035551',1.49,'ENTREE','VENT-15-USD',1,NULL,15,1,NULL,20,15,NULL,'Vente sortie #15 — 1.49',NULL),(23,'2026-05-03 15:10:02.665213',6.44,'ENTREE','VENT-16-USD',1,NULL,16,1,NULL,20,16,NULL,'Vente sortie #16 — 6.44',NULL),(24,'2026-05-03 15:18:55.577625',3.16,'ENTREE','VENT-17-USD',1,NULL,17,1,NULL,20,17,NULL,'Vente sortie #17 — 3.16',NULL),(25,'2026-05-03 15:29:38.133121',8.76,'ENTREE','VENT-18-USD',1,NULL,18,1,NULL,20,18,NULL,'Vente sortie #18 — 8.76',NULL),(26,'2026-05-03 15:43:10.421685',12.00,'ENTREE','VENT-19-USD',1,NULL,19,1,NULL,20,19,NULL,'Vente sortie #19 — 12.00',NULL),(27,'2026-05-03 15:54:47.028039',2.31,'ENTREE','VENT-20-USD',1,NULL,20,1,NULL,20,20,NULL,'Vente sortie #20 — 2.31',NULL),(28,'2026-05-05 12:54:05.470732',3000.00,'ENTREE','',1,NULL,NULL,1,NULL,NULL,NULL,1,'capital',NULL);
/*!40000 ALTER TABLE `stock_mouvementcaisse` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_sortie`
--

DROP TABLE IF EXISTS `stock_sortie`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_sortie` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `statut` varchar(20) NOT NULL,
  `date_creation` datetime(6) NOT NULL,
  `client_id` varchar(20) DEFAULT NULL,
  `devise_id` bigint DEFAULT NULL,
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  `motif` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_sortie_client_id_10acccc9_fk_stock_client_id` (`client_id`),
  KEY `stock_sortie_devise_id_e9eda902_fk_stock_devise_id` (`devise_id`),
  KEY `stock_sorti_entrepr_479496_idx` (`entreprise_id`),
  KEY `stock_sorti_succurs_55beb9_idx` (`succursale_id`),
  KEY `stock_sorti_entrepr_ac624b_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_sortie_client_id_10acccc9_fk_stock_client_id` FOREIGN KEY (`client_id`) REFERENCES `stock_client` (`id`),
  CONSTRAINT `stock_sortie_devise_id_e9eda902_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_sortie_entreprise_id_271a4697_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_sortie_succursale_id_f46bb102_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=21 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_sortie`
--

LOCK TABLES `stock_sortie` WRITE;
/*!40000 ALTER TABLE `stock_sortie` DISABLE KEYS */;
INSERT INTO `stock_sortie` VALUES (1,'PAYEE','2026-03-23 16:30:19.718161','CLI0001',NULL,1,NULL,'Vente au Client'),(2,'PAYEE','2026-03-23 16:32:30.534163','CLI0001',NULL,1,NULL,'Vente au Client'),(3,'PAYEE','2026-04-24 13:31:03.060295','CLI0001',NULL,1,NULL,'Vente au Client'),(4,'PAYEE','2026-04-24 13:53:30.879610','CLI0001',NULL,1,NULL,'Vente au Client'),(5,'PAYEE','2026-04-29 09:41:03.813806','CLI0001',NULL,1,NULL,'Vente au Client'),(6,'PAYEE','2026-04-29 15:36:08.078245','CLI0001',NULL,1,NULL,'Vente au Client'),(7,'PAYEE','2026-04-29 15:43:03.134432','CLI0001',NULL,1,NULL,'Vente au Client'),(8,'PAYEE','2026-04-29 15:46:18.865537','CLI0001',NULL,1,NULL,'Vente au Client'),(9,'PAYEE','2026-04-29 16:05:08.873940','CLI0001',NULL,1,NULL,'Vente au Client'),(10,'PAYEE','2026-05-01 12:12:47.881897','CLI0001',NULL,1,NULL,'Vente au Client'),(11,'PAYEE','2026-05-01 12:18:30.607006','CLI0001',NULL,1,NULL,'Vente au Client'),(12,'PAYEE','2026-05-01 12:20:02.163876','CLI0001',NULL,1,NULL,'Vente au Client'),(13,'PAYEE','2026-05-01 13:39:30.973124','CLI0001',NULL,1,NULL,'Vente au Client'),(14,'PAYEE','2026-05-01 13:46:01.746609','CLI0001',NULL,1,NULL,'Vente au Client'),(15,'PAYEE','2026-05-03 15:04:43.926183','CLI0001',NULL,1,NULL,'Vente au Client'),(16,'PAYEE','2026-05-03 15:10:02.555098','CLI0001',NULL,1,NULL,'Vente au Client'),(17,'PAYEE','2026-05-03 15:18:55.452658','CLI0001',NULL,1,NULL,'Vente au Client'),(18,'PAYEE','2026-05-03 15:29:37.945626','CLI0001',NULL,1,NULL,'Vente au Client'),(19,'PAYEE','2026-05-03 15:43:10.375863','CLI0001',NULL,1,NULL,'Vente au Client'),(20,'PAYEE','2026-05-03 15:54:46.897080','CLI0001',NULL,1,NULL,'Vente au Client');
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
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_soustypearticl_type_article_id_474c6f25_fk_stock_typ` (`type_article_id`),
  KEY `stock_soustypearticl_succursale_id_2853cd41_fk_stock_suc` (`succursale_id`),
  KEY `stock_soust_entrepr_c99e44_idx` (`entreprise_id`),
  KEY `stock_soust_entrepr_bb2684_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_soustypearticl_entreprise_id_e39f4686_fk_stock_ent` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_soustypearticl_succursale_id_2853cd41_fk_stock_suc` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`),
  CONSTRAINT `stock_soustypearticl_type_article_id_474c6f25_fk_stock_typ` FOREIGN KEY (`type_article_id`) REFERENCES `stock_typearticle` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=70 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_soustypearticle`
--

LOCK TABLES `stock_soustypearticle` WRITE;
/*!40000 ALTER TABLE `stock_soustypearticle` DISABLE KEYS */;
INSERT INTO `stock_soustypearticle` VALUES (1,'Cahiers & papiers','',1,1,NULL),(2,'Stylos, crayons & écriture','',1,1,NULL),(3,'Papier','',1,1,NULL),(4,'Classement & organisation','',1,1,NULL),(5,'Enveloppes & emballages','',1,1,NULL),(6,'Agrafage & collage','',1,1,NULL),(7,'Produits de base','',3,1,NULL),(8,'Produits frais & naturels','',3,1,NULL),(9,'Biscuits & snacks','',3,1,NULL),(10,'Produits laitiers','',3,1,NULL),(11,'Boissons & jus','',3,1,NULL),(12,'Matières pour pâtisserie','',3,1,NULL),(13,'Ustensiles de cuisine','',4,1,NULL),(14,'Nettoyage & entretien','',4,1,NULL),(15,'Consommables ménage','',4,1,NULL),(16,'Savons','',5,1,NULL),(17,'Dentifrices & soins bouche','',5,1,NULL),(18,'Crèmes & lotions','',5,1,NULL),(19,'Pommades & gels','',5,1,NULL),(20,'Glycerines','',5,1,NULL),(21,'Parfums & poudres','',5,1,NULL),(22,'Serviettes hygiéniques','',6,1,NULL),(23,'Produits bébé','',6,1,NULL),(24,'Sous-vêtements','',8,1,NULL),(25,'Chaussettes & habits','',8,1,NULL),(26,'Chaussures & accessoires','',8,1,NULL),(27,'Bible','',9,1,NULL),(28,'Livre','',9,1,NULL),(29,'Stockage & accessoires','',10,1,NULL),(30,'Energie & connexion','',10,1,NULL),(31,'Piles','',10,1,NULL),(32,'Divers','',10,1,NULL),(33,'Pagne','',8,1,NULL),(34,'Classeurs','',1,1,NULL),(35,'Fardes','',1,1,NULL),(36,'Encre','',1,1,NULL),(37,'Marqueur','',1,1,NULL),(38,'Chemise','',8,1,NULL),(39,'Singlet','',8,1,NULL),(40,'Cadenat','',11,1,NULL),(41,'Agenda','',1,1,NULL),(42,'PowerBank','',10,1,NULL),(43,'Fleurs','',12,1,NULL),(44,'Emballage Cadeau','',12,1,NULL),(45,'Colle','',11,1,NULL),(46,'Produit pour Cheveux','',5,1,NULL),(47,'Nettoyage toilette','',13,1,NULL),(48,'Agraphe','',1,1,NULL),(49,'couture','',11,1,NULL),(50,'Soulier','',8,1,NULL),(51,'Beurre','',3,1,NULL),(52,'Thé & Café','',3,1,NULL),(53,'Divers','',8,1,NULL),(54,'Divers','',4,1,NULL),(55,'Divers','',11,1,NULL),(56,'Couteau','',4,1,NULL),(57,'Divers','',1,1,NULL),(58,'Huile Vegetale','',3,1,NULL),(59,'Divers','',13,1,NULL),(60,'Rasoirs','',5,1,NULL),(61,'Patte Alimentaire','',3,1,NULL),(62,'Mayonnaise','',3,1,NULL),(63,'Divers','',12,1,NULL),(64,'Fruits','',3,1,NULL),(65,'Sardine','',3,1,NULL),(66,'Tomate','',3,1,NULL),(67,'Haricot','',3,1,NULL),(68,'Tube','',5,1,NULL),(69,'Powerbank','',10,1,NULL);
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
  `Qte` decimal(12,3) NOT NULL,
  `seuilAlert` decimal(12,3) NOT NULL,
  `article_id` varchar(10) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `article_id` (`article_id`),
  CONSTRAINT `stock_stock_article_id_7735da86_fk_stock_article_article_id` FOREIGN KEY (`article_id`) REFERENCES `stock_article` (`article_id`)
) ENGINE=InnoDB AUTO_INCREMENT=474 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_stock`
--

LOCK TABLES `stock_stock` WRITE;
/*!40000 ALTER TABLE `stock_stock` DISABLE KEYS */;
INSERT INTO `stock_stock` VALUES (1,14.000,0.000,'FOAG0001'),(2,10.000,0.000,'FOAG0002'),(3,0.000,0.000,'PRCO0001'),(4,730.000,0.000,'PRCO0002'),(5,1976.000,0.000,'PRCO0003'),(6,0.000,0.000,'PRPA0001'),(7,0.000,0.000,'PRPA0002'),(8,30.000,0.000,'FOST0001'),(9,16.000,0.000,'PRPR0001'),(10,26.000,0.000,'PRNE0001'),(11,276.000,0.000,'PRNE0002'),(12,461.000,0.000,'PRBI0001'),(13,0.000,0.000,'FOST0002'),(14,0.000,0.000,'FOST0003'),(15,26.000,0.000,'FOMA0001'),(16,77.000,0.000,'FOMA0002'),(17,120.000,0.000,'PRBI0002'),(18,68.000,0.000,'PRBI0003'),(19,44.000,0.000,'PRBI0004'),(20,404.000,0.000,'PRBI0005'),(21,0.000,0.000,'PRBI0006'),(22,180.000,0.000,'PRBI0007'),(23,413.000,0.000,'PRBI0008'),(24,22.000,0.000,'PRBI0009'),(25,13.000,0.000,'PRDI0001'),(26,6.000,0.000,'FOCL0001'),(27,23.000,0.000,'PRUS0001'),(28,65.000,0.000,'PRUS0002'),(29,265.000,0.000,'PRBI0010'),(30,2519.000,0.000,'PRBI0011'),(31,219.000,0.000,'PRBI0012'),(32,0.000,0.000,'PRBI0013'),(33,12.000,0.000,'PRMA0001'),(34,4.000,0.000,'PRFL0001'),(35,5.000,0.000,'PRFL0002'),(36,1.000,0.000,'PRFL0003'),(37,0.000,0.000,'PRDE0001'),(38,0.000,0.000,'PRDE0002'),(39,72.000,0.000,'PRDE0003'),(40,0.000,0.000,'PRDI0002'),(41,0.000,0.000,'PRDI0003'),(42,6.000,0.000,'PRDI0004'),(43,15.000,0.000,'PRDI0005'),(44,182.000,0.000,'PRPA0003'),(45,280.000,0.000,'FOCA0001'),(46,39.000,0.000,'FOCA0002'),(47,0.000,0.000,'FOCA0003'),(48,40.000,0.000,'FOCA0004'),(49,77.000,0.000,'FOCA0005'),(50,18.000,0.000,'FOCA0006'),(51,19.000,0.000,'FOCA0007'),(52,0.000,0.000,'FOCA0008'),(53,35.000,0.000,'FOCA0009'),(54,2367.000,0.000,'FOCA0010'),(55,165.000,0.000,'FOCA0011'),(56,685.000,0.000,'FOCA0012'),(57,0.000,0.000,'PRLI0001'),(58,11.000,0.000,'PRST0001'),(59,10.000,0.000,'PRST0002'),(60,3.000,0.000,'PRST0003'),(61,64.000,0.000,'PRMA0002'),(62,42.000,0.000,'PRDI0006'),(63,4.000,0.000,'PRDI0007'),(64,16.000,0.000,'PRDI0008'),(65,0.000,0.000,'HACH0001'),(66,0.000,0.000,'HACH0002'),(67,0.000,0.000,'HACH0003'),(68,0.000,0.000,'HACH0004'),(69,30.000,0.000,'HACH0005'),(70,47.000,0.000,'ARCO0001'),(71,0.000,0.000,'ARCO0002'),(72,0.000,0.000,'ARCO0003'),(73,25.000,0.000,'PRMA0003'),(74,103.000,0.000,'PRFL0004'),(75,8.000,0.000,'FOCA0013'),(76,0.000,0.000,'FOCA0014'),(77,1.000,0.000,'PRCR0001'),(78,10.000,0.000,'PRCR0002'),(79,0.000,0.000,'PRCR0003'),(80,5.000,0.000,'PRCR0004'),(81,0.000,0.000,'PRCR0005'),(82,0.000,0.000,'PRCR0006'),(83,0.000,0.000,'PRCR0007'),(84,12.000,0.000,'PRCR0008'),(85,0.000,0.000,'PRCR0009'),(86,6.000,0.000,'PRCR0010'),(87,12.000,0.000,'PRCR0011'),(88,1.000,0.000,'PRCR0012'),(89,8.000,0.000,'PRCR0013'),(90,0.000,0.000,'PRCR0014'),(91,0.000,0.000,'PRCR0015'),(92,0.000,0.000,'PRCR0016'),(93,0.000,0.000,'PRCR0017'),(94,1.000,0.000,'PRDE0004'),(95,34.000,0.000,'PRUS0003'),(96,0.000,0.000,'PRUS0004'),(97,10.000,0.000,'PRDE0005'),(98,12.000,0.000,'PRDE0006'),(99,15.000,0.000,'PRDE0007'),(100,4.000,0.000,'PRDE0008'),(101,0.000,0.000,'PRBO0001'),(102,47.000,0.000,'PRBO0002'),(103,276.000,0.000,'PRBO0003'),(104,314.000,0.000,'PRBO0004'),(106,17.000,0.000,'PRST0004'),(107,7.000,0.000,'PREM0001'),(108,42.000,0.000,'PREM0002'),(109,19.000,0.000,'PREM0003'),(110,0.000,0.000,'PREM0004'),(111,28.000,0.000,'PREM0005'),(112,0.000,0.000,'PREM0006'),(113,59.000,0.000,'FOEN0001'),(114,82.000,0.000,'FOFA0001'),(115,106.000,0.000,'FOFA0002'),(116,81.000,0.000,'PRMA0005'),(118,25.000,0.000,'PRDI0009'),(119,0.000,0.000,'PRDI0010'),(120,5.000,0.000,'PRST0005'),(121,13.000,0.000,'PRST0006'),(122,6.000,0.000,'PRST0007'),(123,2.000,0.000,'PRMA0007'),(124,13.000,0.000,'PRFL0005'),(125,20.000,0.000,'PRFL0006'),(126,0.000,0.000,'PRGL0001'),(127,3.000,0.000,'PRGL0002'),(128,0.000,0.000,'PRGL0003'),(129,1.000,0.000,'PRGL0004'),(130,15.000,0.000,'PRGL0005'),(131,0.000,0.000,'PRGL0006'),(132,23.000,0.000,'PRGL0007'),(133,17.000,0.000,'PRGL0008'),(134,6.000,0.000,'PRGL0009'),(135,0.000,0.000,'PRGL0010'),(136,0.000,0.000,'PRGL0011'),(137,7.000,0.000,'PRGL0012'),(139,32.000,0.000,'PRUS0006'),(141,3.000,0.000,'FOST0004'),(142,85.000,0.000,'FOST0005'),(143,17.000,0.000,'PRMA0008'),(144,27.000,0.000,'ARCO0004'),(145,33.000,0.000,'FOCA0015'),(146,0.000,0.000,'FOCA0016'),(147,0.000,0.000,'PRBO0005'),(148,0.000,0.000,'PRBO0006'),(149,58.000,0.000,'PRBO0007'),(150,65.000,0.000,'PRBO0008'),(151,10.000,0.000,'PRBO0009'),(152,38.000,0.000,'PRBO0010'),(153,12.000,0.000,'PRBO0011'),(154,38.000,0.000,'PRBO0012'),(155,0.000,0.000,'PRBO0013'),(156,5.000,0.000,'PRBO0014'),(157,0.000,0.000,'PRBO0015'),(158,15.000,0.000,'PRBO0016'),(159,32.000,0.000,'PRBO0017'),(160,0.000,0.000,'PRBO0018'),(162,1.000,0.000,'FOCA0017'),(163,17.000,0.000,'PRMA0009'),(164,0.000,0.000,'PRMA0010'),(165,0.000,0.000,'PRMA0011'),(166,20.000,0.000,'PRCR0018'),(168,3.000,0.000,'PRCR0020'),(169,12.000,0.000,'PRCR0021'),(170,5.000,0.000,'PRCR0022'),(171,12.000,0.000,'PRCR0023'),(172,12.000,0.000,'PRCR0024'),(173,100.000,0.000,'PRCO0004'),(174,0.000,0.000,'PRCO0005'),(175,16.000,0.000,'FOCA0018'),(176,0.000,0.000,'FOST0006'),(177,13.000,0.000,'FOST0007'),(178,1.000,0.000,'PRPO0001'),(179,0.000,0.000,'PRPO0002'),(180,30.000,0.000,'FOCA0019'),(181,11.000,0.000,'FOPA0001'),(182,820.000,0.000,'FOPA0002'),(183,0.000,0.000,'FOPA0003'),(184,0.000,0.000,'FOPA0004'),(185,1.000,0.000,'FOPA0005'),(186,182.000,0.000,'PRSE0001'),(187,210.000,0.000,'FOPA0006'),(188,0.000,0.000,'FOPA0007'),(189,35.000,0.000,'FOPA0008'),(190,150.000,0.000,'FOPA0009'),(191,0.000,0.000,'PRSE0002'),(192,72.000,0.000,'PRSE0003'),(193,221.000,0.000,'PRSE0004'),(194,1149.000,0.000,'FOPA0010'),(195,22.000,0.000,'PRPA0004'),(196,5.000,0.000,'PRPA0005'),(197,5.000,0.000,'PRPA0006'),(198,2.000,0.000,'FOCA0020'),(199,0.000,0.000,'PRPI0001'),(200,116.000,0.000,'PRPI0002'),(201,446.000,0.000,'PRPI0003'),(202,275.000,0.000,'PRPI0004'),(203,0.000,0.000,'PRPI0005'),(204,12.000,0.000,'PRUS0008'),(205,20.000,0.000,'PRUS0009'),(206,0.000,0.000,'PRPO0003'),(207,14.000,0.000,'PRPO0004'),(208,0.000,0.000,'PRPO0005'),(209,8.000,0.000,'PRPO0006'),(210,0.000,0.000,'PRPO0007'),(211,16.000,0.000,'PRPO0008'),(212,13.000,0.000,'PRPO0009'),(213,3.000,0.000,'PRPO0010'),(214,7.000,0.000,'PRPO0011'),(216,0.000,0.000,'PRPO0013'),(217,7.000,0.000,'PRPO0014'),(218,4.000,0.000,'PRPO0015'),(219,2.000,0.000,'PRPO0016'),(220,7.000,0.000,'PRPO0017'),(221,0.000,0.000,'PRPO0018'),(222,0.000,0.000,'PRPO0019'),(223,9.000,0.000,'PRPO0020'),(224,6.000,0.000,'PRPO0021'),(225,0.000,0.000,'PRPO0022'),(226,17.000,0.000,'PRPO0023'),(227,11.000,0.000,'PRPO0024'),(228,12.000,0.000,'PRPO0025'),(229,12.000,0.000,'PRPO0026'),(230,10.000,0.000,'PRPO0027'),(231,5.000,0.000,'PRPO0028'),(232,7.000,0.000,'PRPA0007'),(233,0.000,0.000,'PRPA0008'),(234,31.000,0.000,'PRPA0009'),(235,0.000,0.000,'PRPA0010'),(236,0.000,0.000,'PRMA0012'),(237,0.000,0.000,'PRMA0013'),(238,2.000,0.000,'PRDI0011'),(239,0.000,0.000,'PRDI0012'),(240,11.000,0.000,'PRSA0001'),(241,9.000,0.000,'PRSA0002'),(242,11.000,0.000,'PRSA0003'),(243,9.000,0.000,'PRSA0004'),(244,31.000,0.000,'PRSA0005'),(245,7.000,0.000,'PRSA0006'),(246,63.000,0.000,'PRSA0007'),(247,8.000,0.000,'PRSA0008'),(248,61.000,0.000,'PRSA0009'),(249,0.000,0.000,'PRSA0010'),(250,0.000,0.000,'PRSA0011'),(251,0.000,0.000,'PRSA0012'),(254,69.500,0.000,'PRSA0015'),(255,133.000,0.000,'PRSA0016'),(256,65.000,0.000,'PRSA0017'),(257,0.000,0.000,'PRSA0018'),(258,13.750,0.000,'PRSA0019'),(259,0.000,0.000,'PRSA0020'),(260,5.000,0.000,'PRSA0021'),(261,0.000,0.000,'HASO0001'),(262,9.000,0.000,'HASI0001'),(263,0.000,0.000,'HASI0002'),(264,21.000,0.000,'HASI0003'),(265,1.000,0.000,'HASI0004'),(266,12.000,0.000,'HASI0005'),(267,36.000,0.000,'HASI0006'),(268,18.000,0.000,'HASO0002'),(269,16.000,0.000,'HASO0003'),(270,49.000,0.000,'HASO0004'),(271,9.000,0.000,'HASO0005'),(272,13.000,0.000,'HASO0006'),(273,1.000,0.000,'HASO0007'),(274,10.000,0.000,'HASO0008'),(275,716.000,0.000,'FOCA0021'),(276,660.000,0.000,'FOCA0022'),(277,548.000,0.000,'FOCA0023'),(278,37.000,0.000,'PRBO0020'),(279,19.000,0.000,'ARCO0005'),(280,12.000,0.000,'FOCA0024'),(281,0.000,0.000,'PRUS0010'),(282,0.000,0.000,'PRUS0011'),(283,0.000,0.000,'PRUS0012'),(284,0.000,0.000,'PRUS0013'),(285,0.000,0.000,'PRUS0014'),(286,5.000,0.000,'PRNE0003'),(287,9.000,0.000,'PRNE0004'),(288,10.000,0.000,'PRNE0005'),(290,4.000,0.000,'ARCO0006'),(291,5.000,0.000,'ARCO0007'),(292,39.000,0.000,'ARCO0008'),(293,2.000,0.000,'PRMA0014'),(294,203.000,0.000,'PRMA0015'),(295,0.000,0.000,'PRPO0029'),(296,0.000,0.000,'PRPO0030'),(297,0.000,0.000,'PRPO0031'),(298,0.000,0.000,'PRPO0032'),(299,16.000,0.000,'PRPO0033'),(300,13.000,3.000,'PRSE0005'),(301,5.000,0.000,'PRMA0016'),(302,0.000,0.000,'PRMA0017'),(303,5.000,0.000,'ARCO0009'),(304,8.000,0.000,'ARCO0010'),(305,2.000,0.000,'ARCO0011'),(306,21.000,0.000,'FOMA0003'),(307,1000.000,0.000,'FOMA0004'),(308,11.000,0.000,'ARCO0012'),(309,6.000,0.000,'PRGL0013'),(310,0.000,0.000,'PRGL0014'),(311,0.000,0.000,'PRBI0014'),(312,7.000,0.000,'PRLI0002'),(313,4.000,0.000,'PRLI0003'),(314,5.000,0.000,'PRLI0004'),(315,5.000,0.000,'PRLI0005'),(316,23.000,0.000,'PRNE0006'),(317,11.000,0.000,'PRNE0007'),(318,1.000,0.000,'PRLI0006'),(319,35.000,0.000,'PRNE0008'),(320,23.000,0.000,'PRNE0009'),(321,0.000,0.000,'PRNE0010'),(322,10.000,0.000,'PRNE0011'),(323,12.000,0.000,'PRDE0009'),(324,26.000,0.000,'PRDE0010'),(325,15.000,0.000,'PRNE0012'),(326,25.000,10.000,'PRUS0015'),(327,180.000,0.000,'PRCO0006'),(328,125.000,0.000,'PRCO0007'),(329,100.000,0.000,'PRCO0008'),(330,0.000,0.000,'PRCO0009'),(331,10.000,0.000,'PRNE0013'),(332,7.000,0.000,'PRNE0014'),(333,20.000,0.000,'FOST0008'),(334,45.000,0.000,'FOST0009'),(335,5.000,0.000,'HAPA0001'),(336,6.000,0.000,'HAPA0002'),(337,4.000,0.000,'HAPA0003'),(338,5.000,0.000,'HAPA0004'),(339,23.000,0.000,'FOST0010'),(340,0.000,0.000,'PRNE0015'),(341,0.000,0.000,'FOCA0026'),(342,0.000,0.000,'FOCA0027'),(343,9.000,0.000,'FOCA0028'),(344,9.000,0.000,'PRNE0016'),(345,8.000,0.000,'PRNE0017'),(346,0.000,0.000,'PRNE0018'),(347,1.000,0.000,'PRSE0006'),(348,11.000,0.000,'PRSE0007'),(349,58.000,0.000,'PRSE0008'),(350,16.000,0.000,'PRSE0009'),(351,72.000,0.000,'PRSE0010'),(352,85.000,0.000,'PRSE0011'),(353,12.000,0.000,'PRMA0018'),(355,0.000,0.000,'PRBO0021'),(356,0.000,0.000,'PRBO0022'),(357,0.000,0.000,'PRPI0006'),(360,0.000,0.000,'PRPI0009'),(361,4.000,0.000,'HASO0009'),(362,620.000,0.000,'FOAG0003'),(363,7.000,0.000,'FOAG0004'),(364,288.000,0.000,'ARCO0013'),(365,14.000,0.000,'HASO0010'),(366,11.000,0.000,'PRBI0015'),(367,4.000,0.000,'PRBI0016'),(368,3.000,0.000,'PRBI0017'),(369,21.000,0.000,'PRMA0020'),(370,15.000,0.000,'PRBE0001'),(371,15.000,0.000,'PRBE0002'),(372,1.000,0.000,'PRBE0003'),(373,11.000,0.000,'PRDI0013'),(374,6.000,0.000,'PRTH0001'),(375,2.000,0.000,'ARCA0001'),(376,11.000,0.000,'ARCA0002'),(377,21.000,0.000,'HACH0006'),(378,30.000,0.000,'HACH0007'),(379,11.000,0.000,'HACH0008'),(380,4.000,0.000,'HACH0009'),(381,3.000,0.000,'HACH0010'),(382,2.000,0.000,'HACH0011'),(383,28.000,0.000,'HADI0001'),(384,8.000,0.000,'HADI0002'),(385,26.000,0.000,'ARCO0014'),(386,381.000,0.000,'PRDI0014'),(387,4.000,0.000,'FOCL0002'),(388,46.000,0.000,'ARDI0001'),(389,7.000,0.000,'PRDI0015'),(390,10.000,0.000,'PRDI0016'),(391,30.000,0.000,'FODI0001'),(392,43.000,0.000,'FODI0002'),(393,94.000,0.000,'FOEN0002'),(394,646.000,0.000,'FOEN0003'),(395,891.000,0.000,'FOEN0004'),(396,11.000,0.000,'PRHU0001'),(397,9.000,0.000,'PRHU0002'),(398,10.000,0.000,'PRHU0003'),(399,7.000,0.000,'PRHU0004'),(400,6.000,0.000,'PRHU0005'),(401,2.000,0.000,'PRHU0006'),(402,7.000,0.000,'PRPR0002'),(403,8.000,0.000,'PRBO0023'),(404,11.000,0.000,'PRBO0024'),(405,417.000,0.000,'PRPR0003'),(406,9.000,0.000,'PRPR0004'),(407,4.000,0.000,'PRPR0005'),(408,8.000,0.000,'PRPR0006'),(409,270.000,0.000,'PRRA0001'),(410,1.000,0.000,'PRPR0007'),(411,6.000,0.000,'PRPA0011'),(412,7.000,0.000,'PRMA0021'),(413,7.000,0.000,'PRMA0022'),(414,5.000,0.000,'PRPR0008'),(415,140.000,0.000,'PRPR0009'),(416,4.000,0.000,'HAPA0005'),(417,2.000,0.000,'HAPA0006'),(418,3.000,0.000,'HAPA0007'),(419,8.000,0.000,'PRDI0017'),(420,2.000,0.000,'PRDI0018'),(421,22.000,0.000,'ARDI0002'),(422,2.000,0.000,'ARDI0003'),(423,18.000,0.000,'PRUS0016'),(424,1.000,0.000,'PRUS0017'),(425,18.000,0.000,'PRUS0018'),(426,11.000,0.000,'PRPR0010'),(427,7.000,0.000,'PRPO0034'),(428,18.000,0.000,'PRPO0035'),(429,12.000,0.000,'PRFR0001'),(430,53.000,0.000,'ARDI0004'),(431,4.000,0.000,'ARDI0005'),(432,18.000,0.000,'ARDI0006'),(433,4.000,0.000,'PRPO0036'),(434,5.000,0.000,'PRPR0011'),(435,14.000,0.000,'PRPO0037'),(436,12.000,0.000,'PRPR0012'),(437,121.000,0.000,'PRPR0013'),(438,61.000,0.000,'FOEN0005'),(439,20.000,0.000,'FOEN0006'),(440,4000.000,0.000,'FOEN0007'),(441,400.000,0.000,'FOEN0008'),(442,5.000,0.000,'PRSA0022'),(443,10.000,0.000,'PRSA0023'),(444,9.000,0.000,'PRSA0024'),(445,12.000,0.000,'PRPR0014'),(446,12.000,0.000,'PRPR0015'),(447,149.000,0.000,'PRPR0016'),(448,16.000,0.000,'HASO0011'),(449,18.000,0.000,'PRPA0012'),(450,71.000,0.000,'PRMA0023'),(451,118.000,0.000,'NEDI0001'),(452,43.000,0.000,'PRTO0001'),(453,26.500,0.000,'PRPR0017'),(454,2.000,0.000,'PRCR0025'),(455,0.000,0.000,'PRPR0018'),(456,2.000,0.000,'PRUS0019'),(457,4.000,0.000,'PRUS0020'),(458,0.000,0.000,'PRHA0001'),(459,12.000,0.000,'PRTU0001'),(460,12.000,0.000,'PRTU0002'),(461,11.000,0.000,'PRPO0038'),(462,3800.000,0.000,'PRDI0019'),(463,3.000,0.000,'PRSA0025'),(464,2.000,0.000,'HASO0012'),(465,4.000,0.000,'PRUS0021'),(466,498.000,0.000,'FOST0011'),(467,41.000,0.000,'NENE0001'),(468,473.000,10.000,'FOPA0011'),(469,0.000,0.000,'PRBI0018'),(470,0.000,0.000,'PRBI0019'),(471,0.000,0.000,'PRBI0020'),(472,0.000,0.000,'PRBO0025'),(473,0.000,0.000,'PRBI0021');
/*!40000 ALTER TABLE `stock_stock` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_succursale`
--

DROP TABLE IF EXISTS `stock_succursale`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_succursale` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nom` varchar(255) NOT NULL,
  `adresse` varchar(255) DEFAULT NULL,
  `telephone` varchar(50) DEFAULT NULL,
  `email` varchar(254) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `stock_succursale_entreprise_id_nom_2d37998f_uniq` (`entreprise_id`,`nom`),
  CONSTRAINT `stock_succursale_entreprise_id_f4f88690_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_succursale`
--

LOCK TABLES `stock_succursale` WRITE;
/*!40000 ALTER TABLE `stock_succursale` DISABLE KEYS */;
/*!40000 ALTER TABLE `stock_succursale` ENABLE KEYS */;
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
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_typearticle_succursale_id_0a6befb1_fk_stock_succursale_id` (`succursale_id`),
  KEY `stock_typea_entrepr_0a6efa_idx` (`entreprise_id`),
  KEY `stock_typea_entrepr_9c07da_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_typearticle_entreprise_id_afcd0f6a_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_typearticle_succursale_id_0a6befb1_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_typearticle`
--

LOCK TABLES `stock_typearticle` WRITE;
/*!40000 ALTER TABLE `stock_typearticle` DISABLE KEYS */;
INSERT INTO `stock_typearticle` VALUES (1,'FOURNITURES SCOLAIRES & DE BUREAU','',1,NULL),(3,'PRODUITS ALIMENTAIRES (NOURRITURE)','',1,NULL),(4,'PRODUITS DE CUISINE & MENAGE','',1,NULL),(5,'PRODUITS COSMETIQUES & HYGIENE CORPORELLE','',1,NULL),(6,'PRODUITS FEMININS & BEBE','',1,NULL),(8,'HABILLEMENT & ACCESSOIRES','',1,NULL),(9,'PRODUITS RELIGIEUX','',1,NULL),(10,'PRODUITS ELECTRONIQUES & ACCESSOIRES','',1,NULL),(11,'ARTICLES DIVERS & QUINCAILLERIE LEGERE','',1,NULL),(12,'PRODUITS EVENEMENTIELS','',1,NULL),(13,'NETTOYAGE ET ENTRETIEN MENAGER','',1,NULL),(14,'divers','',1,NULL);
/*!40000 ALTER TABLE `stock_typearticle` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `stock_typecaisse`
--

DROP TABLE IF EXISTS `stock_typecaisse`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `stock_typecaisse` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `libelle` varchar(120) NOT NULL,
  `description` longtext NOT NULL,
  `image` varchar(100) DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `entreprise_id` bigint NOT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_typecaisse_succursale_id_8ddbed50_fk_stock_succursale_id` (`succursale_id`),
  KEY `stock_typec_entrepr_4f8295_idx` (`entreprise_id`),
  KEY `stock_typec_entrepr_abb535_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_typecaisse_entreprise_id_2d650062_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_typecaisse_succursale_id_8ddbed50_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_typecaisse`
--

LOCK TABLES `stock_typecaisse` WRITE;
/*!40000 ALTER TABLE `stock_typecaisse` DISABLE KEYS */;
/*!40000 ALTER TABLE `stock_typecaisse` ENABLE KEYS */;
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
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_unite_succursale_id_4f96accc_fk_stock_succursale_id` (`succursale_id`),
  KEY `stock_unite_entrepr_550fdb_idx` (`entreprise_id`),
  KEY `stock_unite_entrepr_40ae77_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_unite_entreprise_id_0b1f0036_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_unite_succursale_id_4f96accc_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=16 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_unite`
--

LOCK TABLES `stock_unite` WRITE;
/*!40000 ALTER TABLE `stock_unite` DISABLE KEYS */;
INSERT INTO `stock_unite` VALUES (1,'Litres','',1,NULL),(2,'Kilogramme','',1,NULL),(3,'Pc \\ Pieces','',1,NULL),(4,'Boxes','',1,NULL),(5,'Rame','',1,NULL),(6,'Sac','',1,NULL),(7,'Bouteille','',1,NULL),(8,'Cartons','',1,NULL),(9,'Paquet','',1,NULL),(10,'Plaquettes','',1,NULL),(11,'Rouleau','',1,NULL),(12,'Boite','',1,NULL),(13,'Bar','',1,NULL),(14,'Cuilleur','',1,NULL),(15,'Bindon','',1,NULL);
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
) ENGINE=InnoDB AUTO_INCREMENT=129 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `token_blacklist_outstandingtoken`
--

LOCK TABLES `token_blacklist_outstandingtoken` WRITE;
/*!40000 ALTER TABLE `token_blacklist_outstandingtoken` DISABLE KEYS */;
INSERT INTO `token_blacklist_outstandingtoken` VALUES (1,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MTQ5NywiaWF0IjoxNzc0MTg3ODk3LCJqdGkiOiI5ZTg5OGRjYTIxNjM0NDNjOTlmZTQ2NjAwNTI4Mzg0NSIsInVzZXJfaWQiOiIxIn0.fY3fV-oW0ZM82ZXenk1dXk8oAJpjPMdNWiaGCztTecI','2026-03-22 13:58:17.623444','2026-03-22 14:58:17.000000',1,'9e898dca2163443c99fe466005283845'),(2,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MTg5MSwiaWF0IjoxNzc0MTg4MjkxLCJqdGkiOiIyNzlhZjUzYmY2MGI0MWU3YjZjMzQyZTExZGYxMWI3NyIsInVzZXJfaWQiOiIxIn0.mRT9p-jUeyClktEujOn8KILtm9utORe_JMgr6Br26kE','2026-03-22 14:04:51.772454','2026-03-22 15:04:51.000000',1,'279af53bf60b41e7b6c342e11df11b77'),(3,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MjA5MiwiaWF0IjoxNzc0MTg4NDkyLCJqdGkiOiIxNTIzOGZiYWYxNzc0MmUzYmRjMDczNDYxYjQ0NThiNiIsInVzZXJfaWQiOiIyIn0.TC22ls_jJV6d9awV7tXZrlk_1qSxEwVjuNKmQEl2jig','2026-03-22 14:08:12.762754','2026-03-22 15:08:12.000000',2,'15238fbaf17742e3bdc073461b4458b6'),(4,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MjA5MywiaWF0IjoxNzc0MTg4NDkzLCJqdGkiOiJhMmQxNzdlNzkxNDM0YTE4ODYyYTY3MTk2MGJmMjA5OCIsInVzZXJfaWQiOiIyIn0.L_rngrIiDMFTbnPZMFDHwEBbuC4QDOXdloOiJV3VGfc','2026-03-22 14:08:13.395680','2026-03-22 15:08:13.000000',2,'a2d177e791434a18862a671960bf2098'),(5,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MjExNSwiaWF0IjoxNzc0MTg4NTE1LCJqdGkiOiJhNDhmNzY4MTZkYzM0YWMwOTY4ZGEzZDUxYjYxMmQwNyIsInVzZXJfaWQiOiIxIn0.NzmC1sASVW_AOX9j_GUD9-1jy_aDFOzlBwpZMv-sfO4','2026-03-22 14:08:35.239807','2026-03-22 15:08:35.000000',1,'a48f76816dc34ac0968da3d51b612d07'),(6,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MjExNSwiaWF0IjoxNzc0MTg4NTE1LCJqdGkiOiIxMjY0NzI0MTIxMWI0NWFlYTgwZDJkMTY4MWVhYjdhYyIsInVzZXJfaWQiOiIxIn0._TsL8jlv7g5A0bkI7guGp6Nbo58Kqd4XOG2Gdol1LBE','2026-03-22 14:08:35.440363','2026-03-22 15:08:35.000000',1,'12647241211b45aea80d2d1681eab7ac'),(7,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5NTgxMCwiaWF0IjoxNzc0MTkyMjEwLCJqdGkiOiJiNzkzYTcyMGQyMGY0YzI5OWFhMjBlYmNlZjVlNjI4OCIsInVzZXJfaWQiOiIxIn0.SWfSOSPWHE6zwJpfyoeaHutQibAqKRfJ_v09HI1Y6bM','2026-03-22 15:10:10.722815','2026-03-22 16:10:10.000000',1,'b793a720d20f4c299aa20ebcef5e6288'),(8,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5NTgxMCwiaWF0IjoxNzc0MTkyMjEwLCJqdGkiOiI0MWMyOGVkODhkN2Y0NWFhOWI0NDFlYWI4ODk2MGE5NCIsInVzZXJfaWQiOiIxIn0.VlpWDrei-jGF_BsZ8h7UTxbB5Z1B3Wzz28qELX4zeuQ','2026-03-22 15:10:10.976756','2026-03-22 16:10:10.000000',1,'41c28ed88d7f45aa9b441eab88960a94'),(9,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDIwNDU1MiwiaWF0IjoxNzc0MjAwOTUyLCJqdGkiOiI4OGM1NThkMmJhOTY0ZjM5OTUwOWEwYTBhNDJhYTViNCIsInVzZXJfaWQiOiIxIn0.IahkcGytNDTXTFDoS0eVW_p7PhGNuEBCDZR00dLZHp8','2026-03-22 17:35:52.087883','2026-03-22 18:35:52.000000',1,'88c558d2ba964f399509a0a0a42aa5b4'),(10,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDIwNDU1MiwiaWF0IjoxNzc0MjAwOTUyLCJqdGkiOiJiMTNmYjFmZTkxYWI0YzM2YTY2MGYyZmIyODQyNjk3ZSIsInVzZXJfaWQiOiIxIn0.vz-7kh6BVlVXr5Guf3SZck2tHEWQ8cSOnmzBtO6KAk4','2026-03-22 17:35:52.444280','2026-03-22 18:35:52.000000',1,'b13fb1fe91ab4c36a660f2fb2842697e'),(11,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI1NzQ0NSwiaWF0IjoxNzc0MjUzODQ1LCJqdGkiOiI2YjIzNjg0ZTI5NDU0MmRiYjA1NzllZTNhM2JmZDMyYyIsInVzZXJfaWQiOiIxIn0.h0V2Gi9PPiHDebaYOwuObX_qE_MTiS1T5AQ-Ac3uI8A','2026-03-23 08:17:25.695797','2026-03-23 09:17:25.000000',1,'6b23684e294542dbb0579ee3a3bfd32c'),(12,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI1NzQ0NiwiaWF0IjoxNzc0MjUzODQ2LCJqdGkiOiJkMDU4M2M5OWE0Zjg0ZmFmODFkZjRhMWI4N2MyMjcxYSIsInVzZXJfaWQiOiIxIn0.1ExzTOYlXoqowcF1k3a0hZjtq_zAbKQGEKoe1R9hqpg','2026-03-23 08:17:26.366125','2026-03-23 09:17:26.000000',1,'d0583c99a4f84faf81df4a1b87c2271a'),(13,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI2MTM4MSwiaWF0IjoxNzc0MjU3NzgxLCJqdGkiOiI4YjU4NzI5YjUzODE0MDQ3OWZhMTBmOTIwNjZiYTRhYyIsInVzZXJfaWQiOiIxIn0.a_2vAw2vpWhKv7nhLXAo2YouTcaDzTDoe68zGz_Df74','2026-03-23 09:23:01.549583','2026-03-23 10:23:01.000000',1,'8b58729b538140479fa10f92066ba4ac'),(14,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI2MTM4MSwiaWF0IjoxNzc0MjU3NzgxLCJqdGkiOiI3MzRhNjljYzBkZDM0OTQ4YTc5NDBhMWZhNDE2OTRjMyIsInVzZXJfaWQiOiIxIn0.OQwqHllC1RPCoG3uJXJsGpIhqXYeLiNyt0ySO_Eo92Y','2026-03-23 09:23:01.804404','2026-03-23 10:23:01.000000',1,'734a69cc0dd34948a7940a1fa41694c3'),(15,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI2NTAzMSwiaWF0IjoxNzc0MjYxNDMxLCJqdGkiOiI3MDI1NzNhNDM3YzA0OGRiYjY4MTU4MDJjYjAxMGNhMiIsInVzZXJfaWQiOiIxIn0.ht3x2TmgvwkffI2GzCHjaPUwNHUqGZgDdg25tpWh1q4','2026-03-23 10:23:51.405659','2026-03-23 11:23:51.000000',1,'702573a437c048dbb6815802cb010ca2'),(16,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI2NTAzMSwiaWF0IjoxNzc0MjYxNDMxLCJqdGkiOiIyZWU3ZmFmOWU3NDc0YTk3ODhkNzIwZjA0OTFhZWJjMyIsInVzZXJfaWQiOiIxIn0.lzad4O1rRqer3vMXTjafPsW_027LXkj_hwbmV5Eymow','2026-03-23 10:23:51.722766','2026-03-23 11:23:51.000000',1,'2ee7faf9e7474a9788d720f0491aebc3'),(17,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI3NzU0OCwiaWF0IjoxNzc0MjczOTQ4LCJqdGkiOiIxY2ZmMjY5ZDAwMDg0MTc1ODMyMjQwZjg3MGI1MjUxMyIsInVzZXJfaWQiOiIxIn0.m0K6KLhcg8N3Jw1spLPQmW1XHDXfZD6gVhcd1Mmr0xM','2026-03-23 13:52:28.354303','2026-03-23 14:52:28.000000',1,'1cff269d00084175832240f870b52513'),(18,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI3NzU2NSwiaWF0IjoxNzc0MjczOTY1LCJqdGkiOiJhNDc2ZTllYWYzNDE0NWQ5ODQ3ZmUyMDhmYmI5NzBhMCIsInVzZXJfaWQiOiIxIn0.-ocEQ1xd6yFSulHkAg9U-gJ6Mm7jvOxfxGKnAwhGEFI','2026-03-23 13:52:45.971015','2026-03-23 14:52:45.000000',1,'a476e9eaf34145d9847fe208fbb970a0'),(19,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI4NDM4OSwiaWF0IjoxNzc0MjgwNzg5LCJqdGkiOiIxNGUzYjgwMjMyNGI0ZmQ5OWZmYzI5NWIxZmE5MTM5OSIsInVzZXJfaWQiOiIxIn0.yKdCOl6AXt4naIxBJ5vY1cySvb_GnT9r8uyahVR3y2Y','2026-03-23 15:46:29.991920','2026-03-23 16:46:29.000000',1,'14e3b802324b4fd99ffc295b1fa91399'),(20,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI4NDM5MCwiaWF0IjoxNzc0MjgwNzkwLCJqdGkiOiIzZTg4NzIzYjFiZGI0MWE0OTkzOTMwYWQ4YzFiMjMzZSIsInVzZXJfaWQiOiIxIn0.sOC8NciJ5EDiTGpstXZr87y_fGeMzVxrZezOuehccIM','2026-03-23 15:46:30.443674','2026-03-23 16:46:30.000000',1,'3e88723b1bdb41a4993930ad8c1b233e'),(21,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NTA2MTA4OSwiaWF0IjoxNzc1MDU3NDg5LCJqdGkiOiIyMTY2ZmRkNGM4N2E0ZGRlYTc3M2E1YmY2YWNmOWYyZCIsInVzZXJfaWQiOiIxIn0.DeqLzN1j-wEDNeJFLsu4W_M8JsSLAm3jmn1VUMJRxgA','2026-04-01 15:31:29.724237','2026-04-01 16:31:29.000000',1,'2166fdd4c87a4ddea773a5bf6acf9f2d'),(22,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NTA2MTA5NSwiaWF0IjoxNzc1MDU3NDk1LCJqdGkiOiIxMmQxZTFhZWU2ZTE0N2JmOWI3ZjUxOWVjYmMyZmZhMyIsInVzZXJfaWQiOiIxIn0.T7rT-m1FAG42oww9OtTUuQk31pUaHWw_i_jrmcY1Ok4','2026-04-01 15:31:35.362768','2026-04-01 16:31:35.000000',1,'12d1e1aee6e147bf9b7f519ecbc2ffa3'),(23,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NTM5MDMyMiwiaWF0IjoxNzc1Mzg2NzIyLCJqdGkiOiI4OGYzMjcyYzc0NjU0MTExOTgwZGQ5N2U4MDA3ODRhMCIsInVzZXJfaWQiOiIxIn0.kVsjavcyKaD1f1wemjRmYapQUVpoq0SIbyQ0M2QsY84','2026-04-05 10:58:42.974175','2026-04-05 11:58:42.000000',1,'88f3272c74654111980dd97e800784a0'),(24,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NTM5MDMyNiwiaWF0IjoxNzc1Mzg2NzI2LCJqdGkiOiI5Y2RlZmM4MTVjMGQ0YTAyYWYxYTYyYTY4MzMyOTJhZiIsInVzZXJfaWQiOiIxIn0.Fa7dcNmQk-qDTyYIo2FCxGuzNGSm6UVWAcayFQVdkhg','2026-04-05 10:58:46.784558','2026-04-05 11:58:46.000000',1,'9cdefc815c0d4a02af1a62a6833292af'),(25,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA3MjE5MywiaWF0IjoxNzc2MDY4NTkzLCJqdGkiOiJjZDJkNTgwN2RmZGY0OWQ5OWIyOWUxODIzNGI0ZGM4NyIsInVzZXJfaWQiOiIxIn0.MfngekZ83qjs9D7Ez8KNSj8fMXDwgGTw4-p5LsM8_Js','2026-04-13 08:23:13.072671','2026-04-13 09:23:13.000000',1,'cd2d5807dfdf49d99b29e18234b4dc87'),(26,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA3MjE5MywiaWF0IjoxNzc2MDY4NTkzLCJqdGkiOiJjNzcwZjA3OTQ0OGU0N2U2YjM3NmRmOTE3ZGZjMjVlNSIsInVzZXJfaWQiOiIxIn0.rMqZuIBAdpq3vVHn26wt9r5KxPl645mV9HZtIgL3ZFc','2026-04-13 08:23:13.287572','2026-04-13 09:23:13.000000',1,'c770f079448e47e6b376df917dfc25e5'),(27,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA3Njg2MCwiaWF0IjoxNzc2MDczMjYwLCJqdGkiOiI4ZDUyMWUzYWY2YTk0MzQ3OTFlNzZhZjkzNDk1YTA3MyIsInVzZXJfaWQiOiIxIn0.sFITZiZc8Ct8POGawyLyKqC1U4J8H792an8CmHrOoZw','2026-04-13 09:41:00.333412','2026-04-13 10:41:00.000000',1,'8d521e3af6a9434791e76af93495a073'),(28,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA3Njg2MCwiaWF0IjoxNzc2MDczMjYwLCJqdGkiOiJiYTUwYjgwZDMzNGM0YzM1ODlkYjgxM2FiNjM0ZjNkMyIsInVzZXJfaWQiOiIxIn0.ZAHHej6YE-vGTSlf92jLhEEA6kPLKKKcW9Y5R_2mWSA','2026-04-13 09:41:00.505347','2026-04-13 10:41:00.000000',1,'ba50b80d334c4c3589db813ab634f3d3'),(29,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA5MDQzOSwiaWF0IjoxNzc2MDg2ODM5LCJqdGkiOiI5MzVjMGI4ODE4NzU0Zjk4OGFhMjExNTBmNzYyMzMzOSIsInVzZXJfaWQiOiIxIn0.KopdTrnYxWrKMCwkwm1Uo83hvpO-jbxjakh_KBTTUno','2026-04-13 13:27:19.487210','2026-04-13 14:27:19.000000',1,'935c0b8818754f988aa21150f7623339'),(30,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA5MDQzOSwiaWF0IjoxNzc2MDg2ODM5LCJqdGkiOiIxZDU1ZmY4M2MwZTk0OWMxYTM0NzA4ODc0ZGNmNzkxYyIsInVzZXJfaWQiOiIxIn0.RUYZ1lqtNaWv37l14ys-zjqEzZEf6CYUfjnExYuQl3U','2026-04-13 13:27:19.744451','2026-04-13 14:27:19.000000',1,'1d55ff83c0e949c1a34708874dcf791c'),(31,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA5NDA5MywiaWF0IjoxNzc2MDkwNDkzLCJqdGkiOiIyMjBhYTg2MDJmYWU0MWQ3YmJlZjhiYjg5OTFlMDZkMiIsInVzZXJfaWQiOiIxIn0.cK2qk8-Jd7Y-0QpG1mgu-Sy5DiQj9nHdcYKHibdZa9E','2026-04-13 14:28:13.115317','2026-04-13 15:28:13.000000',1,'220aa8602fae41d7bbef8bb8991e06d2'),(32,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA5NDA5MywiaWF0IjoxNzc2MDkwNDkzLCJqdGkiOiJlYjcyOGVmNDYwMDc0ZjQ3OGFjYzQ0NTg2MTJjODdiNCIsInVzZXJfaWQiOiIxIn0.hk8XXZu9_7l_I3k39JrdWWBcvdZWBc5dEEr1q3vNsXo','2026-04-13 14:28:13.199982','2026-04-13 15:28:13.000000',1,'eb728ef460074f478acc4458612c87b4'),(33,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA5Nzc2NywiaWF0IjoxNzc2MDk0MTY3LCJqdGkiOiIzMmFlZmJiZjUwZTU0MGRlOTNjNDYxMzdiYjZmYmE4YSIsInVzZXJfaWQiOiIxIn0.Kwy1EKEiKQYA2f6I0dpzhr1llMkOU4_-9M-qtdwsGf8','2026-04-13 15:29:27.954766','2026-04-13 16:29:27.000000',1,'32aefbbf50e540de93c46137bb6fba8a'),(34,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjA5Nzc2OCwiaWF0IjoxNzc2MDk0MTY4LCJqdGkiOiI5MzkyMzY0MGQxOTA0ZjFhOWZiZGQ3ZWZlODBkMGY0OCIsInVzZXJfaWQiOiIxIn0.iFc2Jd0wqPJS58kkj5KGA8Sp_REgYsBczBxCYp02TcQ','2026-04-13 15:29:28.088474','2026-04-13 16:29:28.000000',1,'93923640d1904f1a9fbdd7efe80d0f48'),(35,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjEwODUzNiwiaWF0IjoxNzc2MTA0OTM2LCJqdGkiOiI0ZTYyMmNkN2E2ZDM0OTU0OWQzMzg5MDJjMTIwNzIwMSIsInVzZXJfaWQiOiIxIn0.rBj2bK3YsGkVLnxD7a2Nn18M7FVNksze4KWiK7o8_Sc','2026-04-13 18:28:56.433501','2026-04-13 19:28:56.000000',1,'4e622cd7a6d349549d338902c1207201'),(36,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjEwODUzNywiaWF0IjoxNzc2MTA0OTM3LCJqdGkiOiIxMTNkMjgzMGY4OWY0MWUwYjg1NmUyMmY3YmE5MjBjYSIsInVzZXJfaWQiOiIxIn0.QSJ-V5tW_e7SgYBA9NV34VAvCslJJpwok8rInGMPzkM','2026-04-13 18:28:57.167265','2026-04-13 19:28:57.000000',1,'113d2830f89f41e0b856e22f7ba920ca'),(37,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE0NDMwOSwiaWF0IjoxNzc2MTQwNzA5LCJqdGkiOiJlZTZmZWQzMzUzNDA0MGVmOTQ5MTRmYThjOGZmODQyMiIsInVzZXJfaWQiOiIxIn0.dP3js0CtU1LPF5p4NsKbbiLanpYV3WzofmOG_QWgum4','2026-04-14 04:25:09.244290','2026-04-14 05:25:09.000000',1,'ee6fed33534040ef94914fa8c8ff8422'),(38,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE0NDMwOSwiaWF0IjoxNzc2MTQwNzA5LCJqdGkiOiJlNmQxNGRiYjQ2MjU0ZDdmODEzNmRkOGIzMDE0NDcyYSIsInVzZXJfaWQiOiIxIn0.O3j8ABzfMH9W6sMIFE8EmUWJ_G8VJPeEe3ZnuC8qLgA','2026-04-14 04:25:09.333749','2026-04-14 05:25:09.000000',1,'e6d14dbb46254d7f8136dd8b3014472a'),(39,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE0Nzk5MiwiaWF0IjoxNzc2MTQ0MzkyLCJqdGkiOiIwODcxNjFjMWMzM2E0MzBiODEwYzQ4OWZmY2EwNmM1YSIsInVzZXJfaWQiOiIxIn0.QFbBrTkt4P4ZvnmM2TrpoOGHgYWU59n7olCe9IAwXMA','2026-04-14 05:26:32.185521','2026-04-14 06:26:32.000000',1,'087161c1c33a430b810c489ffca06c5a'),(40,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE0Nzk5MiwiaWF0IjoxNzc2MTQ0MzkyLCJqdGkiOiJkOWM3NjU2NzgyODg0NmMwYTBiYTRlZmFjZmFlYTgwNiIsInVzZXJfaWQiOiIxIn0.fS8pmZvf09UJZ6MdR-eIb8ybd1LSqcIs8SyWl1q4nbs','2026-04-14 05:26:32.302497','2026-04-14 06:26:32.000000',1,'d9c76567828846c0a0ba4efacfaea806'),(41,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE1MTY4OCwiaWF0IjoxNzc2MTQ4MDg4LCJqdGkiOiIwMzMwMjBiNWQ1MDA0NTBiYjRmMGQxNzc0ZDNmYzEwNCIsInVzZXJfaWQiOiIxIn0.emvIFxIJquKVBYCRV9R6tuROkoCMLpEOdXQplLdQjHg','2026-04-14 06:28:08.452085','2026-04-14 07:28:08.000000',1,'033020b5d500450bb4f0d1774d3fc104'),(42,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE1MTY4OCwiaWF0IjoxNzc2MTQ4MDg4LCJqdGkiOiJkZTY1Y2ZhMzBhYmQ0YjA1OTgyYjQ4YTE4YzU4Mzk4NyIsInVzZXJfaWQiOiIxIn0.mYdGBfpmamvn9PDdvMF6zVbj3z-6e2jTRrPQAXqjt_M','2026-04-14 06:28:08.617862','2026-04-14 07:28:08.000000',1,'de65cfa30abd4b05982b48a18c583987'),(43,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE2MTQxOSwiaWF0IjoxNzc2MTU3ODE5LCJqdGkiOiI5NWE3NmY4NDc0ZGI0ZDcxYjBhYmFiNWRhNGE5NTdhOSIsInVzZXJfaWQiOiIxIn0.TU6B2avKN8zv79QAhgZNWbz26NKXlmV_wOqoPos9MVY','2026-04-14 09:10:19.970140','2026-04-14 10:10:19.000000',1,'95a76f8474db4d71b0abab5da4a957a9'),(44,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE2MTQyMCwiaWF0IjoxNzc2MTU3ODIwLCJqdGkiOiI5NjVhMGI2ODdiYWM0ZjMxOWFlZThhOGQ1MzAyOWYzNSIsInVzZXJfaWQiOiIxIn0.g7Cul4SaFhMF4B2O3gil7A6h6vNkq1ii0v0biFLmz1c','2026-04-14 09:10:20.109757','2026-04-14 10:10:20.000000',1,'965a0b687bac4f319aee8a8d53029f35'),(45,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE2NTQ0MSwiaWF0IjoxNzc2MTYxODQxLCJqdGkiOiI1NDAzMTZiMTA2MDA0MmJjODQ2OTJiZGFjMWNjNDVlNSIsInVzZXJfaWQiOiIxIn0.HzMY6Lac5bvWKsA-ke2bwJPmLSfxSinlMlSBCVdKJtI','2026-04-14 10:17:21.156100','2026-04-14 11:17:21.000000',1,'540316b1060042bc84692bdac1cc45e5'),(46,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE2NTQ0MSwiaWF0IjoxNzc2MTYxODQxLCJqdGkiOiIwNjJlZTMwMmY0ZWM0MDY2YjQxMDc1ZTEzYzcxMDIyYSIsInVzZXJfaWQiOiIxIn0.E3JdFSvfj4HFWhcXXd20aYWO3iwYIkO_hYzCjPmMC4g','2026-04-14 10:17:21.274226','2026-04-14 11:17:21.000000',1,'062ee302f4ec4066b41075e13c71022a'),(47,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE4MTE3OSwiaWF0IjoxNzc2MTc3NTc5LCJqdGkiOiJlNDI5NDVmMTJhMTE0MGQ4OTQzZGNjZDIzYzg5ODI4MCIsInVzZXJfaWQiOiIxIn0.7a1RFaM8hxHAda0mUlPPZYzEU7419NY9FzrmcMv2-6w','2026-04-14 14:39:39.109141','2026-04-14 15:39:39.000000',1,'e42945f12a1140d8943dccd23c898280'),(48,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE4MTE3OSwiaWF0IjoxNzc2MTc3NTc5LCJqdGkiOiI3YjI3YzJmMTUwNDk0NjMzODZlYmE5OTg3YTk2YTFlMCIsInVzZXJfaWQiOiIxIn0.chgQau12q_-XyBVqSfJ1q88O3B16QYN0phLHudLBn6k','2026-04-14 14:39:39.214533','2026-04-14 15:39:39.000000',1,'7b27c2f15049463386eba9987a96a1e0'),(49,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE4NDg1OSwiaWF0IjoxNzc2MTgxMjU5LCJqdGkiOiIzNDg0OTNhNjMwMDA0OTY3YTZhODVhMDMzNDZiOGI2OSIsInVzZXJfaWQiOiIxIn0.dIIN9qZgDnfl7cutYPTrRYh89Rz0bqnsdE8mIIo-01I','2026-04-14 15:40:59.847463','2026-04-14 16:40:59.000000',1,'348493a630004967a6a85a03346b8b69'),(50,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE4NDg2MCwiaWF0IjoxNzc2MTgxMjYwLCJqdGkiOiI1MTMxNjRhYTgxOGU0ODliOWQwM2ZjNWM4ODMzNWE0MCIsInVzZXJfaWQiOiIxIn0.reIwi63BG6AOf_zb6PK1mFwDRnl4wFfcUmzy4bYjJdI','2026-04-14 15:41:00.447564','2026-04-14 16:41:00.000000',1,'513164aa818e489b9d03fc5c88335a40'),(51,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE4ODY5OSwiaWF0IjoxNzc2MTg1MDk5LCJqdGkiOiI3YTY3YzU5YmEyMWI0ZjcxYWYyZGEwODljNDA1N2FkNiIsInVzZXJfaWQiOiIxIn0.JAcCax7dQJiSB1M9oSyHeP2cLIn7p-q4KVSjFs5HGlo','2026-04-14 16:44:59.879395','2026-04-14 17:44:59.000000',1,'7a67c59ba21b4f71af2da089c4057ad6'),(52,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjE4ODcwMCwiaWF0IjoxNzc2MTg1MTAwLCJqdGkiOiI0OTY5MGU4Y2UyYzU0ZmMwODgxZjMxODA2NGVjYWNmYiIsInVzZXJfaWQiOiIxIn0.gC4wvrSR3MW246W8y1Xu_1KW1rgmoS32Ykje9SF4QgM','2026-04-14 16:45:00.045961','2026-04-14 17:45:00.000000',1,'49690e8ce2c54fc0881f318064ecacfb'),(53,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjIwMTQ5NiwiaWF0IjoxNzc2MTk3ODk2LCJqdGkiOiJmNDk4NzQ4NmJhNGQ0NDhhYjYyYWMwYTE2NWExMmM1MCIsInVzZXJfaWQiOiIxIn0.x5rdRUijq-k5WeNijEgVj4hTdpScwAZ4kCY5885L_kM','2026-04-14 20:18:16.034648','2026-04-14 21:18:16.000000',1,'f4987486ba4d448ab62ac0a165a12c50'),(54,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjIwMTQ5NiwiaWF0IjoxNzc2MTk3ODk2LCJqdGkiOiI3MzFhOTQ0MDAwOGU0YzU1OWMyYjQzMmU2ODNiNmExNiIsInVzZXJfaWQiOiIxIn0.Rho7TM5lcDqFW7RFJkDgekbm3ZR5fMSfPyAKlhNR3dQ','2026-04-14 20:18:16.117715','2026-04-14 21:18:16.000000',1,'731a9440008e4c559c2b432e683b6a16'),(55,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjIyNzE4NCwiaWF0IjoxNzc2MjIzNTg0LCJqdGkiOiI2Y2ZlMDAyY2NjZjc0MzVmODMyNjBiMTAyZTg3ZDdkYiIsInVzZXJfaWQiOiIxIn0.GR4qiGoQO177q0bfI8p1bMFtQwDHCizkBEOwcOFBylg','2026-04-15 03:26:24.722799','2026-04-15 04:26:24.000000',1,'6cfe002cccf7435f83260b102e87d7db'),(56,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjIyNzE4NSwiaWF0IjoxNzc2MjIzNTg1LCJqdGkiOiI3NDVkNTgyZmU4MTk0NzE4OWQyMTNiNDEwZGU2Mzk2OSIsInVzZXJfaWQiOiIxIn0.gUbKS0129UdOZsCM6AXHpQjDUu4KqoPj2G5I-MSGcJ8','2026-04-15 03:26:25.093411','2026-04-15 04:26:25.000000',1,'745d582fe81947189d213b410de63969'),(57,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjIzMTAwMSwiaWF0IjoxNzc2MjI3NDAxLCJqdGkiOiIwZDA4Nzc4M2JmMzE0NGUzODMwYzMyZTQ4MmJkY2JkOSIsInVzZXJfaWQiOiIxIn0.EfNFooEW3p_e9a78EIu221lD7OhnkftpUHsWTMcKJi0','2026-04-15 04:30:01.618259','2026-04-15 05:30:01.000000',1,'0d087783bf3144e3830c32e482bdcbd9'),(58,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjIzMTAwMSwiaWF0IjoxNzc2MjI3NDAxLCJqdGkiOiI3M2U1YmYyMTFmM2Y0M2E4OWMzNjEzODU4NDE4ZTgyOCIsInVzZXJfaWQiOiIxIn0.zagem-_4BBPgd76EmPq1arr-vmZTRUry_U0OYqe-ZQM','2026-04-15 04:30:01.701959','2026-04-15 05:30:01.000000',1,'73e5bf211f3f43a89c3613858418e828'),(59,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjIzODA0NSwiaWF0IjoxNzc2MjM0NDQ1LCJqdGkiOiI4MWExY2Q2YmJlNmQ0ZmNkOGFkMDBjZDc4MTlkM2M3MSIsInVzZXJfaWQiOiIxIn0.0q5lTEJmXI2kAtIRTrOGyRCGLh0MwLbakZGyuG-WiVA','2026-04-15 06:27:25.291597','2026-04-15 07:27:25.000000',1,'81a1cd6bbe6d4fcd8ad00cd7819d3c71'),(60,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjIzODA1OCwiaWF0IjoxNzc2MjM0NDU4LCJqdGkiOiI0MDA1YzJiN2Y1M2E0YTZhYmNhNDJiNmEwZjBjNTVkMyIsInVzZXJfaWQiOiIxIn0.yA_bGEPDhm2SO12dJUkJHC-T8pHJ8dcRdhXzEpxejIA','2026-04-15 06:27:38.858067','2026-04-15 07:27:38.000000',1,'4005c2b7f53a4a6abca42b6a0f0c55d3'),(61,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjI2MjMyMiwiaWF0IjoxNzc2MjU4NzIyLCJqdGkiOiI4ZDc0NzE4MjA2OTE0YmJjYWNjZDg0ZjU5N2EwMmNlOCIsInVzZXJfaWQiOiIxIn0.RisXGqEJxL1ddrR2VSlvPo7EmQjwb0Pva8zPY-tbyk8','2026-04-15 13:12:02.453795','2026-04-15 14:12:02.000000',1,'8d74718206914bbcaccd84f597a02ce8'),(62,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjI2MjMyMywiaWF0IjoxNzc2MjU4NzIzLCJqdGkiOiI2OTMwZmMzMWRjMDE0NGY3ODQ0MGY4OWIxMTYyNzkyOCIsInVzZXJfaWQiOiIxIn0.xTthvivA6Ljn8Wb6mGGxjQlprlZn8xQDxLahvxMku10','2026-04-15 13:12:03.158897','2026-04-15 14:12:03.000000',1,'6930fc31dc0144f78440f89b11627928'),(63,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjI2NTk4NSwiaWF0IjoxNzc2MjYyMzg1LCJqdGkiOiIxODFlNTJiZjBjM2I0ZjM2OTIzMTU4ZDA2MTQ1ZGQwNiIsInVzZXJfaWQiOiIxIn0.-J6rnTki6Rmq90TbryBCrP-EurF_lfZULLzu9GwvtSk','2026-04-15 14:13:05.629425','2026-04-15 15:13:05.000000',1,'181e52bf0c3b4f36923158d06145dd06'),(64,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjI2NTk4NSwiaWF0IjoxNzc2MjYyMzg1LCJqdGkiOiJlMDA0ZWQ4ODRiZmM0MTA0OTBhOTc2ZDFmMWY2ZjBiYSIsInVzZXJfaWQiOiIxIn0.T8H49K7euuDNUfa4-CtnBxTwN2JOVCR7YrSuX-zu_oY','2026-04-15 14:13:05.786732','2026-04-15 15:13:05.000000',1,'e004ed884bfc410490a976d1f1f6f0ba'),(65,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjI2OTYzNiwiaWF0IjoxNzc2MjY2MDM2LCJqdGkiOiI3MzIyMTZmM2VmYjg0ODE5OGQxYjQ3NjQxYjIzYWFlMyIsInVzZXJfaWQiOiIxIn0.GfqGY_8D-AVQRcAbHkLaN_59GmjZqBHvedv_Kg6uKiA','2026-04-15 15:13:56.605636','2026-04-15 16:13:56.000000',1,'732216f3efb848198d1b47641b23aae3'),(66,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjI2OTYzNiwiaWF0IjoxNzc2MjY2MDM2LCJqdGkiOiIwZGFjYWI1ZmE1MjY0Y2ExOTA1ZTEzMDBjYmY4NDFjYSIsInVzZXJfaWQiOiIxIn0.Po6bQlHzDw3HrplNtGv9sdZQTbXjy1lc6YG_aueV3B4','2026-04-15 15:13:56.706188','2026-04-15 16:13:56.000000',1,'0dacab5fa5264ca1905e1300cbf841ca'),(67,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjI3MzMxNSwiaWF0IjoxNzc2MjY5NzE1LCJqdGkiOiI2ZWRjZjIwMmU4NTc0NTYwOGI3ZjA1YTRlMDEwZmQ3YSIsInVzZXJfaWQiOiIxIn0.bUWF2uYIU0w24AzcpxONSyqYqkuO0WIfDfg2647yF2w','2026-04-15 16:15:15.596338','2026-04-15 17:15:15.000000',1,'6edcf202e85745608b7f05a4e010fd7a'),(68,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjI3MzMxNSwiaWF0IjoxNzc2MjY5NzE1LCJqdGkiOiJjOWRkMzI2MWI5YjM0ZjkzYmFjMTRkZTI4YjAzMjdkOCIsInVzZXJfaWQiOiIxIn0.b3i1BP_-2I7fitFgpVImRCqmlJd1LmsbXdI8TFbukVY','2026-04-15 16:15:15.697376','2026-04-15 17:15:15.000000',1,'c9dd3261b9b34f93bac14de28b0327d8'),(69,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjM2ODE0NywiaWF0IjoxNzc2MzY0NTQ3LCJqdGkiOiJmZDA4ODVmNGQ5MDU0MWI4YmFjNmMwMjVjMjBjZDQzNSIsInVzZXJfaWQiOiIxIn0.GEF1T2_FSqpM-kMyOJvzX8zMMLiWAUwarPqpFd2ouPk','2026-04-16 18:35:47.062201','2026-04-16 19:35:47.000000',1,'fd0885f4d90541b8bac6c025c20cd435'),(70,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjM2ODE0NywiaWF0IjoxNzc2MzY0NTQ3LCJqdGkiOiJlOWU3ZjhiZjg0MWQ0MGM0OThiNjg5NzU4NmFkYThhNiIsInVzZXJfaWQiOiIxIn0.fXg0RAiu1z7XO5T1-BubRnSAjxldDUHCbKHjKspeG0g','2026-04-16 18:35:47.848349','2026-04-16 19:35:47.000000',1,'e9e7f8bf841d40c498b6897586ada8a6'),(71,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjM5OTg1MiwiaWF0IjoxNzc2Mzk2MjUyLCJqdGkiOiIyMTllMzBiMzNkZjI0NDY1YjNlM2RlMGYwOGFlZTQyNCIsInVzZXJfaWQiOiIxIn0.sZsUSNWBu1u_6xDCt_OMRQlDj2oJ7h79cy3qSImQ35s','2026-04-17 03:24:12.905789','2026-04-17 04:24:12.000000',1,'219e30b33df24465b3e3de0f08aee424'),(72,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjM5OTg2NCwiaWF0IjoxNzc2Mzk2MjY0LCJqdGkiOiJkZDUwM2JkMmFmOTk0YTZkYjEzOTI2ZWYxOWE1YzViYiIsInVzZXJfaWQiOiIxIn0.ULah8CcD6ojSQ36i7tD654MpL909oCi649PIsRemqNM','2026-04-17 03:24:24.824631','2026-04-17 04:24:24.000000',1,'dd503bd2af994a6db13926ef19a5c5bb'),(73,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQwNzQ4MSwiaWF0IjoxNzc2NDAzODgxLCJqdGkiOiJmNzQyZTM4NGJmMDc0YTcyYTQyNzUyODEwMTQxODY3NyIsInVzZXJfaWQiOiIxIn0.c-hc8ytfgZEhfxcpxDM-ordyxnLBw9jPGLj9MTX3BZs','2026-04-17 05:31:21.019488','2026-04-17 06:31:21.000000',1,'f742e384bf074a72a427528101418677'),(74,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQwNzQ4MSwiaWF0IjoxNzc2NDAzODgxLCJqdGkiOiJhOWY5Zjg4ZGZhNzQ0ODY0ODY5MGJiNjc3OTk1MWU4ZCIsInVzZXJfaWQiOiIxIn0.uyvQ-L6NOyUXU1I6nRoWVZwmdF2pRNxoN4F-XZIiaF0','2026-04-17 05:31:21.105983','2026-04-17 06:31:21.000000',1,'a9f9f88dfa7448648690bb6779951e8d'),(75,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQxMTIzNiwiaWF0IjoxNzc2NDA3NjM2LCJqdGkiOiI4ODE5MGFjYmE0NDk0Y2EwYmQxYjQ3ZGRhNzE4MWYwOCIsInVzZXJfaWQiOiIxIn0.38B6uAmeeJfzKYwMywEWsoi-sKOX69U2hzLjvIDvgfg','2026-04-17 06:33:56.136937','2026-04-17 07:33:56.000000',1,'88190acba4494ca0bd1b47dda7181f08'),(76,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQxMTIzNiwiaWF0IjoxNzc2NDA3NjM2LCJqdGkiOiI0YjdiODNkOTAwZjY0NzI1YmRhNTdiYWI5YWM2NDdkNyIsInVzZXJfaWQiOiIxIn0.5EFXmMMjQdvuefe8apdn3FDSk469r_w4ezjxkca5ziI','2026-04-17 06:33:56.297329','2026-04-17 07:33:56.000000',1,'4b7b83d900f64725bda57bab9ac647d7'),(77,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQxNDkwNywiaWF0IjoxNzc2NDExMzA3LCJqdGkiOiIzMWExZDM2NTY5OWQ0YTIwYjJkMWFlOTE0YjEwMjEyOSIsInVzZXJfaWQiOiIxIn0.zYNbmX8UIZpabImP6uyuBrIKE0SvuLTC9yievg_QSkI','2026-04-17 07:35:07.578859','2026-04-17 08:35:07.000000',1,'31a1d365699d4a20b2d1ae914b102129'),(78,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQxNDkwNywiaWF0IjoxNzc2NDExMzA3LCJqdGkiOiI5NmIyZWJkMGQ5ODY0ZTUxYjQ4YjNhZjI2NDMwZTg2NyIsInVzZXJfaWQiOiIxIn0.gl0su4lV2L0Rj7ZTRp12aDlwr-lVFKxgqDcmExDXhIk','2026-04-17 07:35:07.789448','2026-04-17 08:35:07.000000',1,'96b2ebd0d9864e51b48b3af26430e867'),(79,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQxODc5MSwiaWF0IjoxNzc2NDE1MTkxLCJqdGkiOiI4MjJkNTU5ZDczZDY0MTEzYWRlMDliYzYwMTNhYTRkYiIsInVzZXJfaWQiOiIxIn0.xwjqCRRSoNClDUridUNPp_z__thOigtAK9FXmmDNmg0','2026-04-17 08:39:51.274865','2026-04-17 09:39:51.000000',1,'822d559d73d64113ade09bc6013aa4db'),(80,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQxODc5MSwiaWF0IjoxNzc2NDE1MTkxLCJqdGkiOiIzYTYwMDQwMzA2ZTA0MDdlYWMzMzg0YzYwMTZlNjQxZiIsInVzZXJfaWQiOiIxIn0.T98bvs-Mk65jEZa_5EsQJEGcRk3XKIoX-kx4JU3pXpA','2026-04-17 08:39:51.364099','2026-04-17 09:39:51.000000',1,'3a60040306e0407eac3384c6016e641f'),(81,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQxOTA0OCwiaWF0IjoxNzc2NDE1NDQ4LCJqdGkiOiIwYWE1NWIxNTg5Yjc0MzZlYWE2MGVmOTg2OTcxMjkxMSIsInVzZXJfaWQiOiIxIn0.ZDArnAxXPDIt4PlP3fnaA6iQssUxgblD99j-20ak00s','2026-04-17 08:44:08.447889','2026-04-17 09:44:08.000000',1,'0aa55b1589b7436eaa60ef9869712911'),(82,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQxOTA0OCwiaWF0IjoxNzc2NDE1NDQ4LCJqdGkiOiIyODYwNzg5ODRlOTg0OTBmYmY2ODRjYWVjOGE2NWRmYiIsInVzZXJfaWQiOiIxIn0.P8UUjKUoi4S068UHTqgQRmHJ2zQAt4UEEJ27jvdIof8','2026-04-17 08:44:08.698270','2026-04-17 09:44:08.000000',1,'286078984e98490fbf684caec8a65dfb'),(83,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQyMTY4MiwiaWF0IjoxNzc2NDE4MDgyLCJqdGkiOiI4OGEzMWYyY2IzZDM0ZThlYjdkMTZkZDk2YTZiNDc0OSIsInVzZXJfaWQiOiIxIn0.jXOfarGzHP62WsgUZflVhqfbdFBZd7AmpcTxsZ7NPsQ','2026-04-17 09:28:02.219528','2026-04-17 10:28:02.000000',1,'88a31f2cb3d34e8eb7d16dd96a6b4749'),(84,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQyMTY4MiwiaWF0IjoxNzc2NDE4MDgyLCJqdGkiOiI2ZjYwNjE5MTUxZDk0OGM4YWQ3OTdhMmQ3OTA4NjA0YiIsInVzZXJfaWQiOiIxIn0.EQX7YZ2LMmljsiryneryZpJY3Hgdrblv5zOotY-uIIQ','2026-04-17 09:28:02.469730','2026-04-17 10:28:02.000000',1,'6f60619151d948c8ad797a2d7908604b'),(85,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQyNTM0MywiaWF0IjoxNzc2NDIxNzQzLCJqdGkiOiI4MWFjYmQwNWEwNTU0OThhOGY5ZTc2YzYyYzhkNzc0OCIsInVzZXJfaWQiOiIxIn0.Iy1f0u3FEDzIvzlZMRqYisOjsmFFKVvMLG2i0buRUfg','2026-04-17 10:29:03.649725','2026-04-17 11:29:03.000000',1,'81acbd05a055498a8f9e76c62c8d7748'),(86,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NjQyNTM0NCwiaWF0IjoxNzc2NDIxNzQ0LCJqdGkiOiJhMWRjN2NmZjYzZmU0MzkwYjE5NmVjYjg3YTQyYjAxNSIsInVzZXJfaWQiOiIxIn0.Eni0DOzpM8NA3ga7AYr84afmvhpZqO3NbR95uoRlBts','2026-04-17 10:29:04.016603','2026-04-17 11:29:04.000000',1,'a1dc7cff63fe4390b196ecb87a42b015'),(87,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzAzMzgzMCwiaWF0IjoxNzc3MDMwMjMwLCJqdGkiOiJjY2E2Nzk1OWVjOTk0NzA0OGVlY2NkMGM3NzA2MmNhMSIsInVzZXJfaWQiOiIxIn0.5D2v9oFw8YC_LiOmCZfDY9JGmGoK6A6U8pySr3-B8B0','2026-04-24 11:30:30.352729','2026-04-24 12:30:30.000000',1,'cca67959ec9947048eeccd0c77062ca1'),(88,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzAzMzgzMSwiaWF0IjoxNzc3MDMwMjMxLCJqdGkiOiIzZTU3NDJlMDk4ZTU0ZTk3OGE3MzY4YjY0ZDVkZmJiYyIsInVzZXJfaWQiOiIxIn0.BDmuo0tqUKXGRv1A1dtnstdMnBkX5jMKwTczYQRQ2Z4','2026-04-24 11:30:31.102987','2026-04-24 12:30:31.000000',1,'3e5742e098e54e978a7368b64d5dfbbc'),(89,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzAzNTkzNCwiaWF0IjoxNzc3MDMyMzM0LCJqdGkiOiI5ZmIyMjI3MjQ5YTA0MzQ5OGY0ZWI1OTYyYzQ3Y2I3YSIsInVzZXJfaWQiOiIxIn0.n2x3N9jU3ctGzZHjjNXdGawYfD_vuY8q5AfEYBVwEGw','2026-04-24 12:05:34.617808','2026-04-24 13:05:34.000000',1,'9fb2227249a043498f4eb5962c47cb7a'),(90,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzAzNTkzNSwiaWF0IjoxNzc3MDMyMzM1LCJqdGkiOiI3ZDY0ZTEyM2E0MzQ0MDViYWJkNTQ0OTNkOGNiNjc4OSIsInVzZXJfaWQiOiIxIn0.RQfdYrsuw-K0deNz28cIjBiVdE4IMoTfralwYKmPMpg','2026-04-24 12:05:35.287491','2026-04-24 13:05:35.000000',1,'7d64e123a434405babd54493d8cb6789'),(91,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzAzNjU3OCwiaWF0IjoxNzc3MDMyOTc4LCJqdGkiOiJkZDc3M2QwY2I0NTY0YjFjYTE2YjlkMGU1NDdhMDg5OSIsInVzZXJfaWQiOiIxIn0.QAUD03vXl6v0RGQo-4kYvr3D0-_2orh2MQSbQt7lB1I','2026-04-24 12:16:18.302320','2026-04-24 13:16:18.000000',1,'dd773d0cb4564b1ca16b9d0e547a0899'),(92,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzAzNjU3OCwiaWF0IjoxNzc3MDMyOTc4LCJqdGkiOiJjNmMwNjI3MGU3MmI0MzM0OWIxOGJlOGRkNGNkNzRlYiIsInVzZXJfaWQiOiIxIn0.q94O5lWwZ5OuYytrQcpdC8kZlzefvdfnPAtX402TyW0','2026-04-24 12:16:18.486088','2026-04-24 13:16:18.000000',1,'c6c06270e72b43349b18be8dd4cd74eb'),(93,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzA0MDIxNiwiaWF0IjoxNzc3MDM2NjE2LCJqdGkiOiJmNTlkY2Q4NTJlNzU0ZDI0OGZiNzMwZmQwODNlMjg1MiIsInVzZXJfaWQiOiIxIn0._W4-XzMQPN5wgG4rkjQFVB3snVF9bjSwqgh6K6kCWIo','2026-04-24 13:16:56.653195','2026-04-24 14:16:56.000000',1,'f59dcd852e754d248fb730fd083e2852'),(94,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzA0MDIxNiwiaWF0IjoxNzc3MDM2NjE2LCJqdGkiOiIyZWMwOTdmYmQzNjY0MzIxODc4ZGMzNjBmNTYyMzgxYiIsInVzZXJfaWQiOiIxIn0.TkJzPHgewManlvac2lINHPnIRhNmV_IdIgM27m-sAkc','2026-04-24 13:16:56.820142','2026-04-24 14:16:56.000000',1,'2ec097fbd3664321878dc360f562381b'),(95,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzA0MDM2OSwiaWF0IjoxNzc3MDM2NzY5LCJqdGkiOiJjMDFmMDQ1OTE5NGI0MWJlOGIzZGM5NmQwNDhmNzU0YSIsInVzZXJfaWQiOiIyIn0.6uAz9N2osNTB3wYUJSH0iJeb4wHowwbB6kA8RHpyaGI','2026-04-24 13:19:29.483466','2026-04-24 14:19:29.000000',2,'c01f0459194b41be8b3dc96d048f754a'),(96,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzA0MDM2OSwiaWF0IjoxNzc3MDM2NzY5LCJqdGkiOiI4OWM4NzVjYjRhYTc0ZWI0ODg5MTdmNWI3ZGM4NzI1MiIsInVzZXJfaWQiOiIyIn0.SJrMxjwV1mmMH0WrJL2oWdz9iygTiQxyOkMBwTc7q40','2026-04-24 13:19:29.750200','2026-04-24 14:19:29.000000',2,'89c875cb4aa74eb488917f5b7dc87252'),(97,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzI4Njc2NSwiaWF0IjoxNzc3MjgzMTY1LCJqdGkiOiJiMTdjMWFmZWY3ZWQ0NDM4ODA4NWNiMmUyNzBjYjZjNCIsInVzZXJfaWQiOiIxIn0.Gh36XD-b0mChsXuy-88MxUjfYlVUwdCoXsaHLPfh_KA','2026-04-27 09:46:05.741697','2026-04-27 10:46:05.000000',1,'b17c1afef7ed44388085cb2e270cb6c4'),(98,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzI4Njc2NiwiaWF0IjoxNzc3MjgzMTY2LCJqdGkiOiIxZDIyMmE4ODQ3YTc0NmM1YTFkMzQ3MDFiMzIyMWExYSIsInVzZXJfaWQiOiIxIn0.TO8GMmjFRJVoZ8EOxWPOPiGmSd6j2_3Ltd-yLxMAmdY','2026-04-27 09:46:06.559433','2026-04-27 10:46:06.000000',1,'1d222a8847a746c5a1d34701b3221a1a'),(99,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzMwNDI0OCwiaWF0IjoxNzc3MzAwNjQ4LCJqdGkiOiI0NGNiYWQ4YWU4OWE0OTg5OTNiNWY0MTUxZTgzNzhmOCIsInVzZXJfaWQiOiIxIn0.YVArKd9Qqi5p9ZCvUWibVltLDbhJBPE_rJPz_FekszA','2026-04-27 14:37:28.882148','2026-04-27 15:37:28.000000',1,'44cbad8ae89a498993b5f4151e8378f8'),(100,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzMwNDI0OSwiaWF0IjoxNzc3MzAwNjQ5LCJqdGkiOiIyNDE5MmIyOGI3ZDc0OWJkODcyYmM3NGQxODZmY2MyYiIsInVzZXJfaWQiOiIxIn0.N3iCjsUNfQ4BdURrf0Bywl5kFaV62EfRv-_Rm1PX-sk','2026-04-27 14:37:29.283301','2026-04-27 15:37:29.000000',1,'24192b28b7d749bd872bc74d186fcc2b'),(101,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ1NDQ1MiwiaWF0IjoxNzc3NDUwODUyLCJqdGkiOiI4NmZhMDI3NWQyZjQ0ZTRmOTk0OGViMTAyNzE3ODQxNCIsInVzZXJfaWQiOiIxIn0.KvqELeSLkzCZ5yueCWxgbhTCpi2dspkJ_KWFAFdUUHk','2026-04-29 08:20:52.079817','2026-04-29 09:20:52.000000',1,'86fa0275d2f44e4f9948eb1027178414'),(102,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ1NDQ1MiwiaWF0IjoxNzc3NDUwODUyLCJqdGkiOiIyYTI1MzRhNjBiODk0OWRjODg2NWNkZDJhMzcwZTQ2ZCIsInVzZXJfaWQiOiIxIn0.ZLER8D9JdeZQpHw_D_jOsAG2r8effg5T49gy7DcP8Lk','2026-04-29 08:20:52.380065','2026-04-29 09:20:52.000000',1,'2a2534a60b8949dc8865cdd2a370e46d'),(103,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ1ODg0MiwiaWF0IjoxNzc3NDU1MjQyLCJqdGkiOiI2Zjg1YmM1YTBjMDQ0YjNjYjJmODk3OGEwOWIzMWY5MSIsInVzZXJfaWQiOiIxIn0.xJYe4EiNb7mDv9_4waiahtG7Mt8c6mVJOLZb3rttxOc','2026-04-29 09:34:02.573246','2026-04-29 10:34:02.000000',1,'6f85bc5a0c044b3cb2f8978a09b31f91'),(104,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ1ODg0MiwiaWF0IjoxNzc3NDU1MjQyLCJqdGkiOiJhNDBlOTVjYThiMDk0MjI2YmFlNmE3NzA2NDI0Yzc3MCIsInVzZXJfaWQiOiIxIn0.CKk8OppAMuzusu2CEALvzdfyURBZkTo0iVHjnXUc3ro','2026-04-29 09:34:02.741267','2026-04-29 10:34:02.000000',1,'a40e95ca8b094226bae6a7706424c770'),(105,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ2MDUzMiwiaWF0IjoxNzc3NDU2OTMyLCJqdGkiOiIzYzIzM2RiMTNkNDY0NzRlYmE5MjBhNmQzYmY5YjdjYiIsInVzZXJfaWQiOiIyIn0.2r4uFveV6xwAsI-hq4VPeR8E7WyVSiBhc5JFHJviGyE','2026-04-29 10:02:12.767182','2026-04-29 11:02:12.000000',2,'3c233db13d46474eba920a6d3bf9b7cb'),(106,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ2MDUzMywiaWF0IjoxNzc3NDU2OTMzLCJqdGkiOiI0N2E2NDVjOGM0N2M0ZTBlYTA1NmU3NGNiNDIwNzVlOSIsInVzZXJfaWQiOiIyIn0.6-88Bf8Ext74N7HzsfweQ2pJD11LVUIVJklA03T-9Do','2026-04-29 10:02:13.017299','2026-04-29 11:02:13.000000',2,'47a645c8c47c4e0ea056e74cb42075e9'),(107,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ2MDU3MywiaWF0IjoxNzc3NDU2OTczLCJqdGkiOiJhZmE4ZWNmZGIwMGQ0ZjM2YTE4Mjc5OWEzOTQxMWM0NyIsInVzZXJfaWQiOiIxIn0.pD7ig722I2pCEadoIBspjuroHi8JdTk8XfImCkZKwg0','2026-04-29 10:02:53.212620','2026-04-29 11:02:53.000000',1,'afa8ecfdb00d4f36a182799a39411c47'),(108,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ2MDU3MywiaWF0IjoxNzc3NDU2OTczLCJqdGkiOiI3MTcxZDJjOTAwNjQ0NGYyYTU0NzcyYzE2YjU0ZDZlNiIsInVzZXJfaWQiOiIxIn0.OWgDPOXmaG4VCaVFP-2Ezfysf1j6jNh09Hw3i8EhWbU','2026-04-29 10:02:53.569773','2026-04-29 11:02:53.000000',1,'7171d2c9006444f2a54772c16b54d6e6'),(109,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ2MDYyMywiaWF0IjoxNzc3NDU3MDIzLCJqdGkiOiJjZTdiY2QwNTgyMjg0OWJkOGIyYjUzYzAzN2ExYzRlZiIsInVzZXJfaWQiOiIyIn0.BORiYCA1JEjIPC7lDaqhk_fXCd5wNuv6wPrShes_NLo','2026-04-29 10:03:43.737446','2026-04-29 11:03:43.000000',2,'ce7bcd05822849bd8b2b53c037a1c4ef'),(110,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ2MDYyMywiaWF0IjoxNzc3NDU3MDIzLCJqdGkiOiJkYWU1NWY1YWU3Njc0ZTJhYWQ4MjU4OTVmY2Y3NWVlMSIsInVzZXJfaWQiOiIyIn0.BL1HhT1zyS7v02qP5sD9t2sjE-_DF6bjWQQ8-jqoDy4','2026-04-29 10:03:43.957844','2026-04-29 11:03:43.000000',2,'dae55f5ae7674e2aad825895fcf75ee1'),(111,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ4MDE1MywiaWF0IjoxNzc3NDc2NTUzLCJqdGkiOiJlMTg0MTVkYWU3MDY0ZTU4OTk2YzNmNGQxMDUzOTg1MCIsInVzZXJfaWQiOiIyIn0.UZw331DImwlxP6MbzePxwPn_b14WpeM3M7RKh9oJfrQ','2026-04-29 15:29:13.155849','2026-04-29 16:29:13.000000',2,'e18415dae7064e58996c3f4d10539850'),(112,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzQ4MDE1MywiaWF0IjoxNzc3NDc2NTUzLCJqdGkiOiIzOWVhMDM1ZGI2Mzk0ZDAwOGI4ZDIyMGUzOTIyNWEzNSIsInVzZXJfaWQiOiIyIn0.n3fv0l5pItFVnm6jNBvZIH2SH7gtMm6OPgkWDWTi6LQ','2026-04-29 15:29:13.651481','2026-04-29 16:29:13.000000',2,'39ea035db6394d008b8d220e39225a35'),(113,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzYzOTkxOCwiaWF0IjoxNzc3NjM2MzE4LCJqdGkiOiJiY2RhYzI5MzljNzM0ZTVjYjM3OTJhNzYxNmNhZWI0NSIsInVzZXJfaWQiOiIyIn0.LdN9MySOsEaETMyMPx6JCDMC1nMO6iz9fz46GjGzDxM','2026-05-01 11:51:58.782547','2026-05-01 12:51:58.000000',2,'bcdac2939c734e5cb3792a7616caeb45'),(114,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzYzOTkxOSwiaWF0IjoxNzc3NjM2MzE5LCJqdGkiOiJkZDQ2YmRiZDU5NmM0Yjk1ODQzNDdiYzY5ZmQxOGY1YiIsInVzZXJfaWQiOiIyIn0.M8yKhPnE8cScMP85dB4UalqpCp7sbX1Jxr1f8D76hH4','2026-05-01 11:51:59.152413','2026-05-01 12:51:59.000000',2,'dd46bdbd596c4b9584347bc69fd18f5b'),(115,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzY0NDk4OSwiaWF0IjoxNzc3NjQxMzg5LCJqdGkiOiJhMjgyMmMwMmNiNDA0NGMwOTdhMDk4YTBiM2NjN2Y3YiIsInVzZXJfaWQiOiIyIn0.VB-M0xOFI3iuJtXEeqvOvmZd4YliS9admmeFoRd9XUA','2026-05-01 13:16:29.494391','2026-05-01 14:16:29.000000',2,'a2822c02cb4044c097a098a0b3cc7f7b'),(116,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzY0NDk4OSwiaWF0IjoxNzc3NjQxMzg5LCJqdGkiOiIxMjIyYWJiOGMzNTk0ZWMyYmYyZjI2NjNkODVlMzljNyIsInVzZXJfaWQiOiIyIn0.rIh2-VmWgWZSy-mAR0I73IOGJTF3aoFB_yVJ7qz9644','2026-05-01 13:16:29.695015','2026-05-01 14:16:29.000000',2,'1222abb8c3594ec2bf2f2663d85e39c7'),(117,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzgyNDA1NSwiaWF0IjoxNzc3ODIwNDU1LCJqdGkiOiJhZDA3ZmRkMWQ1MTk0NGU0YWVmOTAzYmFjNjllMjllNSIsInVzZXJfaWQiOiIyIn0.ezH7M0rVuOiemlx16GCSOGA3I_23xbtiYJkTRu3ocw8','2026-05-03 15:00:55.321543','2026-05-03 16:00:55.000000',2,'ad07fdd1d51944e4aef903bac69e29e5'),(118,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzgyNDA1NSwiaWF0IjoxNzc3ODIwNDU1LCJqdGkiOiI2MjI3N2QwZTM5NTk0ODMyYmEzNzM4NGEwOTVmNTFjMSIsInVzZXJfaWQiOiIyIn0.nYcoR5CZD5R4xDyGyWGhu7hZz5fU3l93aVaHPYVOrrk','2026-05-03 15:00:55.589175','2026-05-03 16:00:55.000000',2,'62277d0e39594832ba37384a095f51c1'),(119,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzgyNzg1MSwiaWF0IjoxNzc3ODI0MjUxLCJqdGkiOiJhYjJkM2Q2MzJkNGI0OWNhOTAzZWNmNzE4NTEyZWVhYyIsInVzZXJfaWQiOiIyIn0.oJrz4ra6xCvCURsAFUd6TPMg5PyOK_zZzOhcBLhq3F8','2026-05-03 16:04:11.705987','2026-05-03 17:04:11.000000',2,'ab2d3d632d4b49ca903ecf718512eeac'),(120,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NzgyNzg1MSwiaWF0IjoxNzc3ODI0MjUxLCJqdGkiOiI3OTFiNTg1NDZlNDc0NDFjYjBiMmMxNmYxMzdjNzZlMiIsInVzZXJfaWQiOiIyIn0.VzfMLXWlUzFeXos47FjNH9F3Z8tbXNdYgXxH1Gj_2DI','2026-05-03 16:04:11.940648','2026-05-03 17:04:11.000000',2,'791b58546e47441cb0b2c16f137c76e2'),(121,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3Nzk3NjcyNSwiaWF0IjoxNzc3OTczMTI1LCJqdGkiOiIwNDc1M2E2NTVlNTI0NDk0YWYyODA2MzdjZTkzZTE4NyIsInVzZXJfaWQiOiIxIn0.Wbxh02ZlbABjm1DIh27tUB1vr42jK0Q0N48PgU3QSlc','2026-05-05 09:25:25.257741','2026-05-05 10:25:25.000000',1,'04753a655e524494af280637ce93e187'),(122,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3Nzk3NjcyNSwiaWF0IjoxNzc3OTczMTI1LCJqdGkiOiIxNGQ2N2IwYzc0YWM0NGI0YTMyYmE5ZDE5NjFmODcxZCIsInVzZXJfaWQiOiIxIn0.iEJwMMWaTG-cQiYffsvd76o0-gee_dkwk7RJYLDZvKs','2026-05-05 09:25:25.557930','2026-05-05 10:25:25.000000',1,'14d67b0c74ac44b4a32ba9d1961f871d'),(123,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3Nzk4ODM2NSwiaWF0IjoxNzc3OTg0NzY1LCJqdGkiOiIzZTZlYjc5NWU1M2Q0MTAwODNiZjNmNjJiYzg4MmM4OSIsInVzZXJfaWQiOiIxIn0.7-tk1a1UarOskoAgkz4U3ikjiD_gNEsVi6yHPOu2CKM','2026-05-05 12:39:25.575905','2026-05-05 13:39:25.000000',1,'3e6eb795e53d410083bf3f62bc882c89'),(124,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3Nzk4ODM2NSwiaWF0IjoxNzc3OTg0NzY1LCJqdGkiOiJmMzE2NDk0ZWMwYmE0OWFlYTNkYTNhZDU0NGM3NWFkMyIsInVzZXJfaWQiOiIxIn0.G1slnhjuqnHu9_GjsieVLm9qeHdoW4aWPtWRkTh-Bpw','2026-05-05 12:39:25.761365','2026-05-05 13:39:25.000000',1,'f316494ec0ba49aea3da3ad544c75ad3'),(125,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3Nzk5Njc2OSwiaWF0IjoxNzc3OTkzMTY5LCJqdGkiOiJjNTZiN2NkYjZiYjc0ODAzOTk2NGQyNjcyYTczMDJhYSIsInVzZXJfaWQiOiIxIn0.k1dNxVKAwPxM6FWvA8dmp74xJxPtwtwMXxTe4lz27vQ','2026-05-05 14:59:29.059417','2026-05-05 15:59:29.000000',1,'c56b7cdb6bb748039964d2672a7302aa'),(126,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3Nzk5Njc2OSwiaWF0IjoxNzc3OTkzMTY5LCJqdGkiOiI5NTg1Mjc0MTA1ZjM0MjU1YTJmNTk3OTdjYWEwYWM0MSIsInVzZXJfaWQiOiIxIn0.WIu95kiSmNM5EixUgdPQl453uQDdG0NdWQPY9bY03_o','2026-05-05 14:59:29.310845','2026-05-05 15:59:29.000000',1,'9585274105f34255a2f59797caa0ac41'),(127,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3ODA1MTQ3MywiaWF0IjoxNzc4MDQ3ODczLCJqdGkiOiI3OGYzOWZkNmNlYzU0NWFiYmRjMWViMmY4NjYyYmZhMSIsInVzZXJfaWQiOiIyIn0.-qdhZZmo6edvMz7P24jnyEvIzOSmVjh3-RMq2JaiExQ','2026-05-06 06:11:13.140199','2026-05-06 07:11:13.000000',2,'78f39fd6cec545abbdc1eb2f8662bfa1'),(128,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3ODA1MTQ3MywiaWF0IjoxNzc4MDQ3ODczLCJqdGkiOiIwZTJhN2YzMDE4ODI0NmVlOTBiZjQ2ZGIwODEzZWI2MyIsInVzZXJfaWQiOiIyIn0.mB-AiDD6gJIM3EK-UAhln7nles6HQiXXDblNFP-9330','2026-05-06 06:11:13.608733','2026-05-06 07:11:13.000000',2,'0e2a7f30188246ee90bf46db0813eb63');
/*!40000 ALTER TABLE `token_blacklist_outstandingtoken` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users_membership`
--

DROP TABLE IF EXISTS `users_membership`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_membership` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `role` varchar(20) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `default_succursale_id` bigint DEFAULT NULL,
  `entreprise_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `users_membership_user_id_entreprise_id_cf4027e0_uniq` (`user_id`,`entreprise_id`),
  KEY `users_membership_default_succursale_i_eb7d7bf8_fk_stock_suc` (`default_succursale_id`),
  KEY `users_membership_entreprise_id_ccc3d23a_fk_stock_entreprise_id` (`entreprise_id`),
  CONSTRAINT `users_membership_default_succursale_i_eb7d7bf8_fk_stock_suc` FOREIGN KEY (`default_succursale_id`) REFERENCES `stock_succursale` (`id`),
  CONSTRAINT `users_membership_entreprise_id_ccc3d23a_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `users_membership_user_id_4e97941d_fk_users_user_id` FOREIGN KEY (`user_id`) REFERENCES `users_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_membership`
--

LOCK TABLES `users_membership` WRITE;
/*!40000 ALTER TABLE `users_membership` DISABLE KEYS */;
INSERT INTO `users_membership` VALUES (1,'admin',1,'2026-03-22 14:04:51.587538',NULL,1,1),(2,'user',1,'2026-03-22 14:07:21.105867',NULL,1,2);
/*!40000 ALTER TABLE `users_membership` ENABLE KEYS */;
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
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_user`
--

LOCK TABLES `users_user` WRITE;
/*!40000 ALTER TABLE `users_user` DISABLE KEYS */;
INSERT INTO `users_user` VALUES (1,'pbkdf2_sha256$1000000$ogUwbhVTxYsYyvEcKPOOes$riUumszukv8kkUkFDZBBG5rg+Khuz28Hc12Z/SdFyCI=','2026-05-05 14:59:29.193722',0,'console','console','malambo','consolemalmabo@gmail.com',0,1,'2026-03-22 13:57:43.186852','admin'),(2,'pbkdf2_sha256$1000000$62Vg6xVH3qgp6coW3MtgXv$YFVzYXtBYCHiRPxBUuhlnn6j6NIkhEUp+6zzkBU950Q=','2026-05-06 06:11:13.408341',0,'mireille','','','mireille@gmail.com',0,1,'2026-03-22 14:07:20.034243','user'),(3,'pbkdf2_sha256$1000000$jTSKAVIvapP2adJZrEqrRs$pIqZiHPJaYi8NihpuMXvwoUvcydr+frXcT/eWngbFoU=','2026-04-29 07:26:54.841840',1,'jp','','','jp@gmail.com',1,1,'2026-04-17 08:48:28.990947','superadmin');
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
-- Table structure for table `users_userbranch`
--

DROP TABLE IF EXISTS `users_userbranch`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users_userbranch` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `membership_id` bigint NOT NULL,
  `succursale_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `users_userbranch_membership_id_succursale_id_e3eaea8e_uniq` (`membership_id`,`succursale_id`),
  KEY `users_userbranch_succursale_id_a2aa1c6b_fk_stock_succursale_id` (`succursale_id`),
  CONSTRAINT `users_userbranch_membership_id_8cae7d6d_fk_users_membership_id` FOREIGN KEY (`membership_id`) REFERENCES `users_membership` (`id`),
  CONSTRAINT `users_userbranch_succursale_id_a2aa1c6b_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_userbranch`
--

LOCK TABLES `users_userbranch` WRITE;
/*!40000 ALTER TABLE `users_userbranch` DISABLE KEYS */;
/*!40000 ALTER TABLE `users_userbranch` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-05-06  9:50:56
