CREATE DATABASE  IF NOT EXISTS `api_cantines` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `api_cantines`;
-- MySQL dump 10.13  Distrib 8.0.45, for Win64 (x86_64)
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
) ENGINE=InnoDB AUTO_INCREMENT=113 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',2,'add_permission'),(6,'Can change permission',2,'change_permission'),(7,'Can delete permission',2,'delete_permission'),(8,'Can view permission',2,'view_permission'),(9,'Can add group',3,'add_group'),(10,'Can change group',3,'change_group'),(11,'Can delete group',3,'delete_group'),(12,'Can view group',3,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add Outstanding Token',6,'add_outstandingtoken'),(22,'Can change Outstanding Token',6,'change_outstandingtoken'),(23,'Can delete Outstanding Token',6,'delete_outstandingtoken'),(24,'Can view Outstanding Token',6,'view_outstandingtoken'),(25,'Can add Blacklisted Token',7,'add_blacklistedtoken'),(26,'Can change Blacklisted Token',7,'change_blacklistedtoken'),(27,'Can delete Blacklisted Token',7,'delete_blacklistedtoken'),(28,'Can view Blacklisted Token',7,'view_blacklistedtoken'),(29,'Can add user',8,'add_user'),(30,'Can change user',8,'change_user'),(31,'Can delete user',8,'delete_user'),(32,'Can view user',8,'view_user'),(33,'Can add membership',9,'add_membership'),(34,'Can change membership',9,'change_membership'),(35,'Can delete membership',9,'delete_membership'),(36,'Can view membership',9,'view_membership'),(37,'Can add user branch',10,'add_userbranch'),(38,'Can change user branch',10,'change_userbranch'),(39,'Can delete user branch',10,'delete_userbranch'),(40,'Can view user branch',10,'view_userbranch'),(41,'Can add entreprise',11,'add_entreprise'),(42,'Can change entreprise',11,'change_entreprise'),(43,'Can delete entreprise',11,'delete_entreprise'),(44,'Can view entreprise',11,'view_entreprise'),(45,'Can add succursale',12,'add_succursale'),(46,'Can change succursale',12,'change_succursale'),(47,'Can delete succursale',12,'delete_succursale'),(48,'Can view succursale',12,'view_succursale'),(49,'Can add unite',13,'add_unite'),(50,'Can change unite',13,'change_unite'),(51,'Can delete unite',13,'delete_unite'),(52,'Can view unite',13,'view_unite'),(53,'Can add type article',14,'add_typearticle'),(54,'Can change type article',14,'change_typearticle'),(55,'Can delete type article',14,'delete_typearticle'),(56,'Can view type article',14,'view_typearticle'),(57,'Can add sous type article',15,'add_soustypearticle'),(58,'Can change sous type article',15,'change_soustypearticle'),(59,'Can delete sous type article',15,'delete_soustypearticle'),(60,'Can view sous type article',15,'view_soustypearticle'),(61,'Can add article',16,'add_article'),(62,'Can change article',16,'change_article'),(63,'Can delete article',16,'delete_article'),(64,'Can view article',16,'view_article'),(65,'Can add entree',17,'add_entree'),(66,'Can change entree',17,'change_entree'),(67,'Can delete entree',17,'delete_entree'),(68,'Can view entree',17,'view_entree'),(69,'Can add ligne entree',18,'add_ligneentree'),(70,'Can change ligne entree',18,'change_ligneentree'),(71,'Can delete ligne entree',18,'delete_ligneentree'),(72,'Can view ligne entree',18,'view_ligneentree'),(73,'Can add stock',19,'add_stock'),(74,'Can change stock',19,'change_stock'),(75,'Can delete stock',19,'delete_stock'),(76,'Can view stock',19,'view_stock'),(77,'Can add sortie',20,'add_sortie'),(78,'Can change sortie',20,'change_sortie'),(79,'Can delete sortie',20,'delete_sortie'),(80,'Can view sortie',20,'view_sortie'),(81,'Can add client',21,'add_client'),(82,'Can change client',21,'change_client'),(83,'Can delete client',21,'delete_client'),(84,'Can view client',21,'view_client'),(85,'Can add Dette client',22,'add_detteclient'),(86,'Can change Dette client',22,'change_detteclient'),(87,'Can delete Dette client',22,'delete_detteclient'),(88,'Can view Dette client',22,'view_detteclient'),(89,'Can add Paiement de dette',23,'add_paiementdette'),(90,'Can change Paiement de dette',23,'change_paiementdette'),(91,'Can delete Paiement de dette',23,'delete_paiementdette'),(92,'Can view Paiement de dette',23,'view_paiementdette'),(93,'Can add ligne sortie',24,'add_lignesortie'),(94,'Can change ligne sortie',24,'change_lignesortie'),(95,'Can delete ligne sortie',24,'delete_lignesortie'),(96,'Can view ligne sortie',24,'view_lignesortie'),(97,'Can add Lot utilisé dans sortie',25,'add_lignesortielot'),(98,'Can change Lot utilisé dans sortie',25,'change_lignesortielot'),(99,'Can delete Lot utilisé dans sortie',25,'delete_lignesortielot'),(100,'Can view Lot utilisé dans sortie',25,'view_lignesortielot'),(101,'Can add Bénéfice par lot',26,'add_beneficelot'),(102,'Can change Bénéfice par lot',26,'change_beneficelot'),(103,'Can delete Bénéfice par lot',26,'delete_beneficelot'),(104,'Can view Bénéfice par lot',26,'view_beneficelot'),(105,'Can add mouvement caisse',27,'add_mouvementcaisse'),(106,'Can change mouvement caisse',27,'change_mouvementcaisse'),(107,'Can delete mouvement caisse',27,'delete_mouvementcaisse'),(108,'Can view mouvement caisse',27,'view_mouvementcaisse'),(109,'Can add Devise',28,'add_devise'),(110,'Can change Devise',28,'change_devise'),(111,'Can delete Devise',28,'delete_devise'),(112,'Can view Devise',28,'view_devise');
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
) ENGINE=InnoDB AUTO_INCREMENT=29 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (1,'admin','logentry'),(3,'auth','group'),(2,'auth','permission'),(4,'contenttypes','contenttype'),(5,'sessions','session'),(16,'stock','article'),(26,'stock','beneficelot'),(21,'stock','client'),(22,'stock','detteclient'),(28,'stock','devise'),(17,'stock','entree'),(11,'stock','entreprise'),(18,'stock','ligneentree'),(24,'stock','lignesortie'),(25,'stock','lignesortielot'),(27,'stock','mouvementcaisse'),(23,'stock','paiementdette'),(20,'stock','sortie'),(15,'stock','soustypearticle'),(19,'stock','stock'),(12,'stock','succursale'),(14,'stock','typearticle'),(13,'stock','unite'),(7,'token_blacklist','blacklistedtoken'),(6,'token_blacklist','outstandingtoken'),(9,'users','membership'),(8,'users','user'),(10,'users','userbranch');
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
) ENGINE=InnoDB AUTO_INCREMENT=43 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'stock','0001_initial','2026-03-22 04:20:30.195194'),(2,'contenttypes','0001_initial','2026-03-22 04:20:32.386269'),(3,'contenttypes','0002_remove_content_type_name','2026-03-22 04:20:43.556665'),(4,'auth','0001_initial','2026-03-22 04:21:02.154200'),(5,'auth','0002_alter_permission_name_max_length','2026-03-22 04:21:03.912806'),(6,'auth','0003_alter_user_email_max_length','2026-03-22 04:21:03.981837'),(7,'auth','0004_alter_user_username_opts','2026-03-22 04:21:04.075603'),(8,'auth','0005_alter_user_last_login_null','2026-03-22 04:21:04.282728'),(9,'auth','0006_require_contenttypes_0002','2026-03-22 04:21:04.345233'),(10,'auth','0007_alter_validators_add_error_messages','2026-03-22 04:21:04.461180'),(11,'auth','0008_alter_user_username_max_length','2026-03-22 04:21:04.583638'),(12,'auth','0009_alter_user_last_name_max_length','2026-03-22 04:21:04.777715'),(13,'auth','0010_alter_group_name_max_length','2026-03-22 04:21:05.178915'),(14,'auth','0011_update_proxy_permissions','2026-03-22 04:21:05.279191'),(15,'auth','0012_alter_user_first_name_max_length','2026-03-22 04:21:05.348256'),(16,'users','0001_initial','2026-03-22 04:21:18.002627'),(17,'admin','0001_initial','2026-03-22 04:21:26.450425'),(18,'admin','0002_logentry_remove_auto_add','2026-03-22 04:21:26.528565'),(19,'admin','0003_logentry_add_action_flag_choices','2026-03-22 04:21:26.613235'),(20,'sessions','0001_initial','2026-03-22 04:21:28.757394'),(21,'stock','0002_initial','2026-03-22 04:22:11.015684'),(22,'stock','0003_entreprise_logo','2026-03-22 04:22:13.492056'),(23,'stock','0004_add_entreprise_slogan','2026-03-22 04:22:15.776662'),(24,'stock','0005_entreprise_has_branches_succursale','2026-03-22 04:22:22.566236'),(25,'stock','0006_add_tenant_fields_to_models','2026-03-22 04:23:56.718374'),(26,'stock','0007_client_is_special','2026-03-22 04:24:00.846405'),(27,'token_blacklist','0001_initial','2026-03-22 04:24:08.701147'),(28,'token_blacklist','0002_outstandingtoken_jti_hex','2026-03-22 04:24:10.823048'),(29,'token_blacklist','0003_auto_20171017_2007','2026-03-22 04:24:10.992366'),(30,'token_blacklist','0004_auto_20171017_2013','2026-03-22 04:24:14.132933'),(31,'token_blacklist','0005_remove_outstandingtoken_jti','2026-03-22 04:24:16.979184'),(32,'token_blacklist','0006_auto_20171017_2113','2026-03-22 04:24:17.982192'),(33,'token_blacklist','0007_auto_20171017_2214','2026-03-22 04:24:25.404955'),(34,'token_blacklist','0008_migrate_to_bigautofield','2026-03-22 04:24:35.096580'),(35,'token_blacklist','0010_fix_migrate_to_bigautofield','2026-03-22 04:24:35.281567'),(36,'token_blacklist','0011_linearizes_history','2026-03-22 04:24:35.466515'),(37,'token_blacklist','0012_alter_outstandingtoken_user','2026-03-22 04:24:35.936689'),(38,'token_blacklist','0013_alter_blacklistedtoken_options_and_more','2026-03-22 04:24:36.137280'),(39,'users','0002_add_role_user_agent','2026-03-22 04:24:36.268829'),(40,'users','0003_membership_userbranch','2026-03-22 04:24:56.028542'),(41,'users','0004_backfill_memberships_from_user_entreprise','2026-03-22 04:24:56.182264'),(42,'users','0005_remove_user_entreprise','2026-03-22 04:24:58.404492');
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
INSERT INTO `stock_article` VALUES ('Colle elephant',NULL,'ARCO0001','1',45,3,1,NULL),('Colle liquide',NULL,'ARCO0002','1',45,3,1,NULL),('Colle liquide office',NULL,'ARCO0003','1',45,3,1,NULL),('isolent',NULL,'ARCO0004','1',45,3,1,NULL),('super glue',NULL,'ARCO0005','1',45,3,1,NULL),('tresolente/scotch GF',NULL,'ARCO0006','1',45,3,1,NULL),('tresolente/scotch MF',NULL,'ARCO0007','1',45,3,1,NULL),('tresolente/scotch PF',NULL,'ARCO0008','1',45,3,1,NULL),('Cadenat',NULL,'ARCO0009','1',45,3,1,NULL),('Peigne GF',NULL,'ARCO0010','1',45,3,1,NULL),('Peigne PF',NULL,'ARCO0011','1',45,3,1,NULL),('Fil a coudre',NULL,'ARCO0012','1',45,3,1,NULL),('Agenda 25k GF',NULL,'FOAG0001','1',41,3,1,NULL),('Agenda A6 PF',NULL,'FOAG0002','1',41,3,1,NULL),('Cahier calligraphie',NULL,'FOCA0001','1',1,3,1,NULL),('Cahier dessin',NULL,'FOCA0002','1',1,3,1,NULL),('Cahier ligne  simple',NULL,'FOCA0003','1',1,3,1,NULL),('Cahier ligné brouillon',NULL,'FOCA0004','1',1,3,1,NULL),('Cahier ligné demi brouillon',NULL,'FOCA0005','1',1,3,1,NULL),('Cahier minustre GF',NULL,'FOCA0006','1',1,3,1,NULL),('Cahier minustre PF',NULL,'FOCA0007','1',1,3,1,NULL),('Cahier minustre A7',NULL,'FOCA0008','1',1,3,1,NULL),('Cahier quadrille 200pages',NULL,'FOCA0009','1',1,3,1,NULL),('cahier quadrille 32 pages',NULL,'FOCA0010','1',1,3,1,NULL),('cahier quadrille 96 pages',NULL,'FOCA0011','1',1,3,1,NULL),('carbone',NULL,'FOCA0012','1',1,3,1,NULL),('crayon',NULL,'FOCA0013','1',1,3,1,NULL),('crayon couleur',NULL,'FOCA0014','1',1,3,1,NULL),('journal de classe',NULL,'FOCA0015','1',1,3,1,NULL),('Journaux',NULL,'FOCA0016','1',1,3,1,NULL),('Latte',NULL,'FOCA0017','1',1,3,1,NULL),('Machine scientifique',NULL,'FOCA0018','1',1,3,1,NULL),('note book',NULL,'FOCA0019','1',1,3,1,NULL),('perforateur',NULL,'FOCA0020','1',1,3,1,NULL),('stylon  bleu',NULL,'FOCA0021','1',1,3,1,NULL),('stylon rouge',NULL,'FOCA0022','1',1,3,1,NULL),('stylon noir',NULL,'FOCA0023','1',1,3,1,NULL),('tableau periodique',NULL,'FOCA0024','1',1,3,1,NULL),('touches',NULL,'FOCA0025','1',1,3,1,NULL),('Papier Maquette',NULL,'FOCA0026','1',1,3,1,NULL),('Papier bristole A1',NULL,'FOCA0027','1',1,3,1,NULL),('Ecritoire',NULL,'FOCA0028','1',1,3,1,NULL),('Boite d\'instrument',NULL,'FOCL0001','1',4,3,1,NULL),('encre correctrice',NULL,'FOEN0001','1',36,3,1,NULL),('farde a plastic',NULL,'FOFA0001','1',35,3,1,NULL),('farde a traingle',NULL,'FOFA0002','1',35,3,1,NULL),('Bic marker',NULL,'FOMA0001','1',37,3,1,NULL),('Bic marker tableau blanc',NULL,'FOMA0002','1',37,3,1,NULL),('Bic Souligneur',NULL,'FOMA0003','1',37,3,1,NULL),('Envelloppe Chequis',NULL,'FOMA0004','1',37,3,1,NULL),('papier brustol A1',NULL,'FOPA0001','1',3,3,1,NULL),('papier brustol A4',NULL,'FOPA0002','1',3,3,1,NULL),('papier calque A3',NULL,'FOPA0003','1',3,3,1,NULL),('papier calque (roulon)',NULL,'FOPA0004','1',3,3,1,NULL),('papier diplicateur A4',NULL,'FOPA0005','1',3,3,1,NULL),('papier maquette',NULL,'FOPA0006','1',3,3,1,NULL),('papier milimetrer A1',NULL,'FOPA0007','1',3,3,1,NULL),('papier milimetrer A3',NULL,'FOPA0008','1',3,3,1,NULL),('papier milimetrer A4',NULL,'FOPA0009','1',3,3,1,NULL),('papier vitré',NULL,'FOPA0010','1',3,3,1,NULL),('Ardoise',NULL,'FOST0001','1',2,1,1,NULL),('Bic compo 0,5mm Tip Top',NULL,'FOST0002','1',2,3,1,NULL),('Bic compo 0,5mm uni',NULL,'FOST0003','1',2,3,1,NULL),('gome mercure',NULL,'FOST0004','1',2,3,1,NULL),('gome PF',NULL,'FOST0005','1',2,3,1,NULL),('calculatrice',NULL,'FOST0006','1',2,3,1,NULL),('mine',NULL,'FOST0007','1',2,3,1,NULL),('Badge lux',NULL,'FOST0008','1',2,3,1,NULL),('Badge ordinaire',NULL,'FOST0009','1',2,3,1,NULL),('Bic Rasoire',NULL,'FOST0010','1',2,3,1,NULL),('chossete Gucci',NULL,'HACH0001','1',25,3,1,NULL),('chossete perpette',NULL,'HACH0002','1',25,3,1,NULL),('chossete Versace',NULL,'HACH0003','1',25,3,1,NULL),('chossete Homme',NULL,'HACH0004','1',25,3,1,NULL),('chaussete Longue',NULL,'HACH0005','1',25,3,1,NULL),('Pagne Petit olande',NULL,'HAPA0001','1',33,3,1,NULL),('Pagne wax vasco',NULL,'HAPA0002','1',33,3,1,NULL),('Pagne wax nouvo',NULL,'HAPA0003','1',33,3,1,NULL),('Pagne wax vilisco fake',NULL,'HAPA0004','1',33,3,1,NULL),('siculiste femme  long',NULL,'HASI0001','1',39,3,1,NULL),('singlet diana rose',NULL,'HASI0002','1',39,3,1,NULL),('singlet fille  fammy',NULL,'HASI0003','1',39,3,1,NULL),('singlet fille lux',NULL,'HASI0004','1',39,3,1,NULL),('singlet littlevictan(enfant)',NULL,'HASI0005','1',39,3,1,NULL),('singlet homme',NULL,'HASI0006','1',39,3,1,NULL),('siculiste femme  court',NULL,'HASO0001','1',24,3,1,NULL),('sous vetement femme love',NULL,'HASO0002','1',24,3,1,NULL),('sous-vetement enfant garcon',NULL,'HASO0003','1',24,3,1,NULL),('sous-vetement enfant(mixte)',NULL,'HASO0004','1',24,3,1,NULL),('sous-vetement femme lux',NULL,'HASO0005','1',24,3,1,NULL),('sous-vetement hommelux',NULL,'HASO0006','1',24,3,1,NULL),('soutien',NULL,'HASO0007','1',24,3,1,NULL),('soutien lux',NULL,'HASO0008','1',24,3,1,NULL),('Culotte Home',NULL,'HASO0009','1',24,3,1,NULL),('Bazoka bigg boss',NULL,'PRBI0001','1',9,3,1,NULL),('Biscuit BORA',NULL,'PRBI0002','1',9,4,1,NULL),('Biscuit chocolat PF',NULL,'PRBI0003','1',9,4,1,NULL),('Biscuit chocolat yum GF',NULL,'PRBI0004','1',9,4,1,NULL),('Biscuit cremica',NULL,'PRBI0005','1',9,4,1,NULL),('Biscuit FOOT',NULL,'PRBI0006','1',9,4,1,NULL),('Biscuit max',NULL,'PRBI0007','1',9,4,1,NULL),('Biscuit MILK PLUS',NULL,'PRBI0008','1',9,4,1,NULL),('Biscuit SOJA',NULL,'PRBI0009','1',9,4,1,NULL),('Bombon sifle',NULL,'PRBI0010','1',9,3,1,NULL),('Bombon hewa',NULL,'PRBI0011','1',9,3,1,NULL),('Bombon ivori',NULL,'PRBI0012','1',9,3,1,NULL),('Bombon ordinaire',NULL,'PRBI0013','1',9,3,1,NULL),('Biscuit starBix',NULL,'PRBI0014','1',9,9,1,NULL),('eau tamu 1000ml',NULL,'PRBO0001','1',11,3,1,NULL),('eau tamu 1500ml',NULL,'PRBO0002','1',11,3,1,NULL),('eau tamu 330ml',NULL,'PRBO0003','1',11,3,1,NULL),('eau tamu 550ml',NULL,'PRBO0004','1',11,3,1,NULL),('Jus afya',NULL,'PRBO0005','1',11,3,1,NULL),('jus embe GF',NULL,'PRBO0006','1',11,3,1,NULL),('jus embe PF',NULL,'PRBO0007','1',11,3,1,NULL),('jus fanta PF',NULL,'PRBO0008','1',11,3,1,NULL),('Jus mango',NULL,'PRBO0009','1',11,3,1,NULL),('jus naturel',NULL,'PRBO0010','1',11,3,1,NULL),('jus mirinda GF',NULL,'PRBO0011','1',11,3,1,NULL),('jus mirinda PF',NULL,'PRBO0012','1',11,3,1,NULL),('jus rafiki 1l',NULL,'PRBO0013','1',11,3,1,NULL),('jus apple',NULL,'PRBO0014','1',11,3,1,NULL),('jus oner PF',NULL,'PRBO0015','1',11,3,1,NULL),('jus oner GF',NULL,'PRBO0016','1',11,3,1,NULL),('Jus novida PF',NULL,'PRBO0017','1',11,3,1,NULL),('jus novida GF',NULL,'PRBO0018','1',11,3,1,NULL),('jus fanta GF',NULL,'PRBO0019','1',11,3,1,NULL),('sucre djino',NULL,'PRBO0020','1',11,2,1,NULL),('Jus a carton 330 ml',NULL,'PRBO0021','1',11,3,1,NULL),('jus a onerya 330 ml',NULL,'PRBO0022','1',11,3,1,NULL),('Allumetes (waceshu)',NULL,'PRCO0001','1',15,4,1,NULL),('Allumetes PF',NULL,'PRCO0002','1',15,4,1,NULL),('Allumetes PF',NULL,'PRCO0003','1',15,4,1,NULL),('Lunch box Alminium GF',NULL,'PRCO0004','1',15,3,1,NULL),('Lunch box Alminium PF',NULL,'PRCO0005','1',15,3,1,NULL),('Lunch box Plastique',NULL,'PRCO0006','1',15,3,1,NULL),('Verre a usage unique PF',NULL,'PRCO0007','1',15,3,1,NULL),('Verre a usage unique GF',NULL,'PRCO0008','1',15,3,1,NULL),('Sissette',NULL,'PRCO0009','1',15,3,1,NULL),('creme top claire',NULL,'PRCR0001','1',18,3,1,NULL),('creme Cocopulp',NULL,'PRCR0002','1',18,3,1,NULL),('creme budchou 300ml',NULL,'PRCR0003','1',18,3,1,NULL),('creme cocowhite GF',NULL,'PRCR0004','1',18,3,1,NULL),('creme cocowhite PF',NULL,'PRCR0005','1',18,3,1,NULL),('creme  cocoa',NULL,'PRCR0006','1',18,3,1,NULL),('creme  top lemon',NULL,'PRCR0007','1',18,3,1,NULL),('creme day by day GF',NULL,'PRCR0008','1',18,3,1,NULL),('creme day by day MF',NULL,'PRCR0009','1',18,3,1,NULL),('creme day by day PF',NULL,'PRCR0010','1',18,3,1,NULL),('creme nevia 70g',NULL,'PRCR0011','1',18,3,1,NULL),('creme silver GF',NULL,'PRCR0012','1',18,3,1,NULL),('creme silver PF',NULL,'PRCR0013','1',18,3,1,NULL),('creme skala aloe',NULL,'PRCR0014','1',18,3,1,NULL),('creme top lemon GF',NULL,'PRCR0015','1',18,3,1,NULL),('creme paw paw',NULL,'PRCR0016','1',18,3,1,NULL),('creme top line',NULL,'PRCR0017','1',18,3,1,NULL),('Lotion Amara for men',NULL,'PRCR0018','1',18,3,1,NULL),('lotion skala for men',NULL,'PRCR0019','1',18,3,1,NULL),('Lotion skala homme',NULL,'PRCR0020','1',18,3,1,NULL),('Lotion rapide claire',NULL,'PRCR0021','1',18,3,1,NULL),('Lotioin White express',NULL,'PRCR0022','1',18,3,1,NULL),('Lotion Revlo',NULL,'PRCR0023','1',18,3,1,NULL),('Lotion vestline',NULL,'PRCR0024','1',18,3,1,NULL),('Brosse a dent',NULL,'PRDE0001','1',17,3,1,NULL),('Brossse de toilette',NULL,'PRDE0002','1',17,3,1,NULL),('Brossse de Cuisine',NULL,'PRDE0003','1',17,3,1,NULL),('cure dent',NULL,'PRDE0004','1',17,3,1,NULL),('Dentifrice aloe',NULL,'PRDE0005','1',17,3,1,NULL),('Dentifrice colgate',NULL,'PRDE0006','1',17,3,1,NULL),('Dentifrice fresh up',NULL,'PRDE0007','1',17,3,1,NULL),('Dentifrice flodent',NULL,'PRDE0008','1',17,3,1,NULL),('Bross a dent Luxe',NULL,'PRDE0009','1',17,3,1,NULL),('Bross a dent Ordinaire',NULL,'PRDE0010','1',17,3,1,NULL),('Bluetooth air pord',NULL,'PRDI0001','1',32,3,1,NULL),('Cable USB court',NULL,'PRDI0002','1',32,3,1,NULL),('Cable USB fantome court',NULL,'PRDI0003','1',32,3,1,NULL),('Cable USB fantome long',NULL,'PRDI0004','1',32,3,1,NULL),('Cable USB long',NULL,'PRDI0005','1',32,3,1,NULL),('chargeur AD',NULL,'PRDI0006','1',32,3,1,NULL),('chargeur 2.5 A',NULL,'PRDI0007','1',32,3,1,NULL),('chargeur Faster',NULL,'PRDI0008','1',32,3,1,NULL),('fil boul (TIF-TAQ)',NULL,'PRDI0009','1',32,3,1,NULL),('fil mahine a coudre',NULL,'PRDI0010','1',32,3,1,NULL),('ralonge',NULL,'PRDI0011','1',32,3,1,NULL),('ralonge safety',NULL,'PRDI0012','1',32,3,1,NULL),('emballage cadeau sac',NULL,'PREM0001','1',44,3,1,NULL),('emballage cadeau simple',NULL,'PREM0002','1',44,3,1,NULL),('emballage decalot',NULL,'PREM0003','1',44,3,1,NULL),('emballage sac',NULL,'PREM0004','1',44,3,1,NULL),('emballage sac (cavera)',NULL,'PREM0005','1',44,3,1,NULL),('emballage vert',NULL,'PREM0006','1',44,3,1,NULL),('Bouquet de fleur luxe',NULL,'PRFL0001','1',43,3,1,NULL),('Bouquet de fleur MF',NULL,'PRFL0002','1',43,3,1,NULL),('Bouquet de fleur PF',NULL,'PRFL0003','1',43,3,1,NULL),('couronne',NULL,'PRFL0004','1',43,3,1,NULL),('Fleur a gateau',NULL,'PRFL0005','1',43,12,1,NULL),('Fleur maquette',NULL,'PRFL0006','1',43,3,1,NULL),('glycerine botion',NULL,'PRGL0001','1',20,3,1,NULL),('glycerine carotte',NULL,'PRGL0002','1',20,3,1,NULL),('glycerine day by day',NULL,'PRGL0003','1',20,3,1,NULL),('glycerine Enfant et adulte',NULL,'PRGL0004','1',20,3,1,NULL),('glycerine kris',NULL,'PRGL0005','1',20,3,1,NULL),('glycerine movit',NULL,'PRGL0006','1',20,3,1,NULL),('glycerine pop GF',NULL,'PRGL0007','1',20,3,1,NULL),('glycerine pop PF',NULL,'PRGL0008','1',20,3,1,NULL),('glycerine pure medical',NULL,'PRGL0009','1',20,3,1,NULL),('glycerine skala',NULL,'PRGL0010','1',20,3,1,NULL),('glycerine suzana PF',NULL,'PRGL0011','1',20,3,1,NULL),('glycerine suzana MF',NULL,'PRGL0012','1',20,3,1,NULL),('Glycerine Naomie',NULL,'PRGL0013','1',20,3,1,NULL),('Suzana',NULL,'PRGL0014','1',20,3,1,NULL),('carte biblique',NULL,'PRLI0001','1',28,3,1,NULL),('Hymne et Louange',NULL,'PRLI0002','1',28,3,1,NULL),('Nyimbo za kristo',NULL,'PRLI0003','1',28,3,1,NULL),('Esyo nyimbo esya kristo',NULL,'PRLI0004','1',28,3,1,NULL),('Holy bible',NULL,'PRLI0005','1',28,3,1,NULL),('Holy bible good news',NULL,'PRLI0006','1',28,3,1,NULL),('Bougie gateau',NULL,'PRMA0001','1',12,3,1,NULL),('chapa ndazi',NULL,'PRMA0002','1',12,3,1,NULL),('colorant gateau',NULL,'PRMA0003','1',12,3,1,NULL),('ecritoire',NULL,'PRMA0004','1',12,3,1,NULL),('farine de fromat azam',NULL,'PRMA0005','1',12,2,1,NULL),('farine kaunga',NULL,'PRMA0006','1',12,2,1,NULL),('fourchette',NULL,'PRMA0007','1',12,3,1,NULL),('icing sugar',NULL,'PRMA0008','1',12,3,1,NULL),('Levure paquet',NULL,'PRMA0009','1',12,9,1,NULL),('Levure Cuillèur',NULL,'PRMA0010','1',12,14,1,NULL),('Lotion Amara for women',NULL,'PRMA0011','1',12,3,1,NULL),('prestige 500g',NULL,'PRMA0012','1',12,3,1,NULL),('prestige 250g',NULL,'PRMA0013','1',12,3,1,NULL),('vanilla liquide',NULL,'PRMA0014','1',12,3,1,NULL),('vanilla ruf',NULL,'PRMA0015','1',12,3,1,NULL),('vinaigre',NULL,'PRMA0016','1',12,3,1,NULL),('vitamine E',NULL,'PRMA0017','1',12,3,1,NULL),('Farine kaunga',NULL,'PRMA0018','1',12,2,1,NULL),('Farine azame',NULL,'PRMA0019','1',12,2,1,NULL),('Attache',NULL,'PRNE0001','1',14,3,1,NULL),('Autocolant',NULL,'PRNE0002','1',14,3,1,NULL),('toss omo 1kg',NULL,'PRNE0003','1',14,3,1,NULL),('toss omo 500gr',NULL,'PRNE0004','1',14,3,1,NULL),('toss omo 5kg',NULL,'PRNE0005','1',14,3,1,NULL),('Raclette',NULL,'PRNE0006','1',14,3,1,NULL),('Balais Luxe',NULL,'PRNE0007','1',14,3,1,NULL),('Bross a lessive PF',NULL,'PRNE0008','1',14,3,1,NULL),('Bross a lessive GF',NULL,'PRNE0009','1',14,3,1,NULL),('Bross a lessive MF',NULL,'PRNE0010','1',14,3,1,NULL),('Bross a soulier',NULL,'PRNE0011','1',14,3,1,NULL),('Bross a WC',NULL,'PRNE0012','1',14,3,1,NULL),('Insectiscuide',NULL,'PRNE0013','1',14,3,1,NULL),('Parapluie Tirette',NULL,'PRNE0014','1',14,3,1,NULL),('Boulle odora',NULL,'PRNE0015','1',14,3,1,NULL),('Lungette himide PF',NULL,'PRNE0016','1',14,3,1,NULL),('Lungette himide GF',NULL,'PRNE0017','1',14,3,1,NULL),('Lungette himide MF',NULL,'PRNE0018','1',14,3,1,NULL),('Angel face',NULL,'PRPA0001','1',21,4,1,NULL),('Angel troos: soulier',NULL,'PRPA0002','1',21,3,1,NULL),('Cache nez',NULL,'PRPA0003','1',21,3,1,NULL),('parfum (deodorant) secret',NULL,'PRPA0004','1',21,3,1,NULL),('parfum (deodorant) en boule',NULL,'PRPA0005','1',21,3,1,NULL),('parfum (deodorant) for men',NULL,'PRPA0006','1',21,3,1,NULL),('poudre 22 degre',NULL,'PRPA0007','1',21,3,1,NULL),('poudre my love',NULL,'PRPA0008','1',21,3,1,NULL),('poudre passion 25g',NULL,'PRPA0009','1',21,3,1,NULL),('poudre passion 90g',NULL,'PRPA0010','1',21,3,1,NULL),('pile tiger GF',NULL,'PRPI0001','1',31,3,1,NULL),('pile tiger PF',NULL,'PRPI0002','1',31,3,1,NULL),('pile tocebal',NULL,'PRPI0003','1',31,3,1,NULL),('pile vinnic',NULL,'PRPI0004','1',31,3,1,NULL),('pile electra',NULL,'PRPI0005','1',31,3,1,NULL),('pile tiger',NULL,'PRPI0006','1',31,3,1,NULL),('pile viniki',NULL,'PRPI0007','1',31,3,1,NULL),('pile tocebale',NULL,'PRPI0008','1',31,3,1,NULL),('pile electran GF',NULL,'PRPI0009','1',31,3,1,NULL),('Movit gel',NULL,'PRPO0001','1',19,3,1,NULL),('mycozema',NULL,'PRPO0002','1',19,3,1,NULL),('pommade afrocare GF',NULL,'PRPO0003','1',19,3,1,NULL),('pommade afrocare PF',NULL,'PRPO0004','1',19,3,1,NULL),('pommade amla',NULL,'PRPO0005','1',19,3,1,NULL),('pommade body lux',NULL,'PRPO0006','1',19,3,1,NULL),('pommade familia PF',NULL,'PRPO0007','1',19,3,1,NULL),('pommade  movit GF 250g',NULL,'PRPO0008','1',19,3,1,NULL),('pommade  movit MF 120 g',NULL,'PRPO0009','1',19,3,1,NULL),('pommade  movit PF 70g',NULL,'PRPO0010','1',19,3,1,NULL),('pommade presol GF 125g',NULL,'PRPO0011','1',19,3,1,NULL),('pommade presol MF 80g',NULL,'PRPO0012','1',19,3,1,NULL),('pommade presol PF',NULL,'PRPO0013','1',19,3,1,NULL),('pommade radian GF',NULL,'PRPO0014','1',19,3,1,NULL),('pommade radian PF',NULL,'PRPO0015','1',19,3,1,NULL),('pommade TOP LINE',NULL,'PRPO0016','1',19,3,1,NULL),('pommade skala 100g',NULL,'PRPO0017','1',19,3,1,NULL),('pommade skala 25g',NULL,'PRPO0018','1',19,3,1,NULL),('pommade vestiline PF',NULL,'PRPO0019','1',19,3,1,NULL),('pommade sulfur 8-plus',NULL,'PRPO0020','1',19,3,1,NULL),('pommade boudchu',NULL,'PRPO0021','1',19,3,1,NULL),('pommade baby junior PF',NULL,'PRPO0022','1',19,3,1,NULL),('pommade baby junior MF',NULL,'PRPO0023','1',19,3,1,NULL),('pommade baby junior GF',NULL,'PRPO0024','1',19,3,1,NULL),('pommade vaseline GF',NULL,'PRPO0025','1',19,3,1,NULL),('pommade vaseline PF',NULL,'PRPO0026','1',19,3,1,NULL),('pommade sleeping baby',NULL,'PRPO0027','1',19,3,1,NULL),('pommde UB',NULL,'PRPO0028','1',19,3,1,NULL),('vaseline blue seal GF',NULL,'PRPO0029','1',19,3,1,NULL),('vaseline blue seal PF',NULL,'PRPO0030','1',19,3,1,NULL),('vaseline medical GF',NULL,'PRPO0031','1',19,3,1,NULL),('vaseline medical PF',NULL,'PRPO0032','1',19,3,1,NULL),('Vestline garlic',NULL,'PRPO0033','1',19,3,1,NULL),('Arrachide',NULL,'PRPR0001','1',8,2,1,NULL),('savon fumbact PF 75g',NULL,'PRSA0001','1',16,3,1,NULL),('savon fumbact GF 125g',NULL,'PRSA0002','1',16,3,1,NULL),('savon germol 125g',NULL,'PRSA0003','1',16,3,1,NULL),('savon germol 75g',NULL,'PRSA0004','1',16,3,1,NULL),('savon imperial GF',NULL,'PRSA0005','1',16,3,1,NULL),('savon imperial PF',NULL,'PRSA0006','1',16,3,1,NULL),('savon liquide',NULL,'PRSA0007','1',16,3,1,NULL),('savon medi-soft',NULL,'PRSA0008','1',16,3,1,NULL),('savon monganga',NULL,'PRSA0009','1',16,3,1,NULL),('savon CYNTOL PF 60g',NULL,'PRSA0010','1',16,3,1,NULL),('savon CYNTOL MF125g',NULL,'PRSA0011','1',16,3,1,NULL),('savon CYNTOL GF175 g',NULL,'PRSA0012','1',16,3,1,NULL),('savon imperial PF',NULL,'PRSA0013','1',16,3,1,NULL),('savon imperial GF',NULL,'PRSA0014','1',16,3,1,NULL),('savon saibu',NULL,'PRSA0015','1',16,13,1,NULL),('savon sicovir',NULL,'PRSA0016','1',16,3,1,NULL),('savon lwanzo',NULL,'PRSA0017','1',16,3,1,NULL),('savon salama',NULL,'PRSA0018','1',16,3,1,NULL),('savon pigeon',NULL,'PRSA0019','1',16,3,1,NULL),('savon salama',NULL,'PRSA0020','1',16,3,1,NULL),('sceau plastic',NULL,'PRSA0021','1',16,3,1,NULL),('papier hygienique',NULL,'PRSE0001','1',22,3,1,NULL),('papier mouchoir Tissus',NULL,'PRSE0002','1',22,3,1,NULL),('papier mouchoir rose',NULL,'PRSE0003','1',22,3,1,NULL),('papier serviette',NULL,'PRSE0004','1',22,3,1,NULL),('vim',NULL,'PRSE0005','1',47,3,1,NULL),('Cotex lavable',NULL,'PRSE0006','1',22,3,1,NULL),('Cotex usage unique Diva',NULL,'PRSE0007','1',22,3,1,NULL),('Cotex usage unique Softcare',NULL,'PRSE0008','1',22,3,1,NULL),('Cotex usage unique Naomi',NULL,'PRSE0009','1',22,3,1,NULL),('Mouchoire GF',NULL,'PRSE0010','1',22,3,1,NULL),('Mouchoire PF',NULL,'PRSE0011','1',22,3,1,NULL),('carte mémoire 1GB',NULL,'PRST0001','1',29,3,1,NULL),('carte mémoire 4GB',NULL,'PRST0002','1',29,3,1,NULL),('carte mémoire 8GB',NULL,'PRST0003','1',29,3,1,NULL),('ecouteurs',NULL,'PRST0004','1',29,3,1,NULL),('flash 16GB',NULL,'PRST0005','1',29,3,1,NULL),('flash 32GB',NULL,'PRST0006','1',29,3,1,NULL),('flash 8GB',NULL,'PRST0007','1',29,3,1,NULL),('Bol carmel',NULL,'PRUS0001','1',13,3,1,NULL),('Bol fero io',NULL,'PRUS0002','1',13,3,1,NULL),('Cuillère',NULL,'PRUS0003','1',13,3,1,NULL),('cullotte',NULL,'PRUS0004','1',13,3,1,NULL),('gobelin lux',NULL,'PRUS0005','1',13,3,1,NULL),('gobelin ordinaire',NULL,'PRUS0006','1',13,3,1,NULL),('gobelin usage unique',NULL,'PRUS0007','1',13,3,1,NULL),('plat melanim',NULL,'PRUS0008','1',13,3,1,NULL),('plastique',NULL,'PRUS0009','1',13,3,1,NULL),('themos always 0,5l',NULL,'PRUS0010','1',13,3,1,NULL),('themos always 0,75l',NULL,'PRUS0011','1',13,3,1,NULL),('themos always 0,8l',NULL,'PRUS0012','1',13,3,1,NULL),('themos always 2,5l',NULL,'PRUS0013','1',13,3,1,NULL),('themos always 3,5l',NULL,'PRUS0014','1',13,3,1,NULL),('Verre Metallique',NULL,'PRUS0015','1',13,3,1,NULL);
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
  `lot_entree_id` bigint NOT NULL,
  `ligne_sortie_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_beneficelot_lot_entree_id_9e1012b4_fk_stock_ligneentree_id` (`lot_entree_id`),
  KEY `stock_beneficelot_ligne_sortie_id_82bcff57_fk_stock_lig` (`ligne_sortie_id`),
  CONSTRAINT `stock_beneficelot_ligne_sortie_id_82bcff57_fk_stock_lig` FOREIGN KEY (`ligne_sortie_id`) REFERENCES `stock_lignesortie` (`id`),
  CONSTRAINT `stock_beneficelot_lot_entree_id_9e1012b4_fk_stock_ligneentree_id` FOREIGN KEY (`lot_entree_id`) REFERENCES `stock_ligneentree` (`id`),
  CONSTRAINT `stock_beneficelot_chk_1` CHECK ((`quantite_vendue` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_beneficelot`
--

LOCK TABLES `stock_beneficelot` WRITE;
/*!40000 ALTER TABLE `stock_beneficelot` DISABLE KEYS */;
INSERT INTO `stock_beneficelot` VALUES (1,2,0.00,1.00,1.00,2.00,'2026-03-23 16:30:19.838142',2,1),(2,2,0.00,1.00,1.00,2.00,'2026-03-23 16:32:30.566160',3,2);
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
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  `is_special` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_clien_entrepr_f00fc4_idx` (`entreprise_id`),
  KEY `stock_clien_succurs_353de2_idx` (`succursale_id`),
  KEY `stock_clien_entrepr_2611a1_idx` (`entreprise_id`,`succursale_id`),
  KEY `stock_clien_entrepr_513664_idx` (`entreprise_id`,`is_special`),
  CONSTRAINT `stock_client_entreprise_id_e7d231b4_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_client_succursale_id_a5c49e75_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_client`
--

LOCK TABLES `stock_client` WRITE;
/*!40000 ALTER TABLE `stock_client` DISABLE KEYS */;
INSERT INTO `stock_client` VALUES ('CLI0001','Client inconnu','','',NULL,'2026-03-23 16:30:19.421233',1,NULL,0);
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_entree`
--

LOCK TABLES `stock_entree` WRITE;
/*!40000 ALTER TABLE `stock_entree` DISABLE KEYS */;
INSERT INTO `stock_entree` VALUES (1,'Inventaire','','2026-03-23 16:22:30.654283',1,NULL),(2,'Inventaire','','2026-03-23 16:29:29.610026',1,NULL);
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
INSERT INTO `stock_entreprise` VALUES (1,'CANTINE UNILUK','commerce','Congo','Nord-Kivu/ butembo LUKANGA','+243976316454','uniluk@gmail.com','DC78900','Console Malambo','entreprises/logos/uniluklogo_VAe2dO0.jpg','YESU NI JIBU',0);
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
  `quantite_restante` int unsigned NOT NULL,
  `prix_unitaire` decimal(10,2) NOT NULL,
  `prix_vente` decimal(10,2) NOT NULL,
  `date_expiration` date DEFAULT NULL,
  `date_entree` datetime(6) NOT NULL,
  `seuil_alerte` int unsigned NOT NULL,
  `article_id` varchar(10) NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `entree_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_ligneentree_devise_id_2d1d5e04_fk_stock_devise_id` (`devise_id`),
  KEY `stock_ligneentree_entree_id_c3061fbb_fk_stock_entree_id` (`entree_id`),
  KEY `stock_ligne_article_e99d66_idx` (`article_id`,`date_entree`),
  CONSTRAINT `stock_ligneentree_article_id_5e64e8c1_fk_stock_art` FOREIGN KEY (`article_id`) REFERENCES `stock_article` (`article_id`),
  CONSTRAINT `stock_ligneentree_devise_id_2d1d5e04_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_ligneentree_entree_id_c3061fbb_fk_stock_entree_id` FOREIGN KEY (`entree_id`) REFERENCES `stock_entree` (`id`),
  CONSTRAINT `stock_ligneentree_chk_1` CHECK ((`quantite` >= 0)),
  CONSTRAINT `stock_ligneentree_chk_2` CHECK ((`quantite_restante` >= 0)),
  CONSTRAINT `stock_ligneentree_chk_3` CHECK ((`seuil_alerte` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_ligneentree`
--

LOCK TABLES `stock_ligneentree` WRITE;
/*!40000 ALTER TABLE `stock_ligneentree` DISABLE KEYS */;
INSERT INTO `stock_ligneentree` VALUES (2,10,8,0.00,1.00,NULL,'2026-03-23 16:25:29.117063',3,'PRSE0005',1,1),(3,20,18,0.00,1.00,NULL,'2026-03-23 16:29:29.618019',10,'PRUS0015',1,2);
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_lignesortie`
--

LOCK TABLES `stock_lignesortie` WRITE;
/*!40000 ALTER TABLE `stock_lignesortie` DISABLE KEYS */;
INSERT INTO `stock_lignesortie` VALUES (1,2,1.00,'2026-03-23 16:30:19.814153','PRSE0005',1,1),(2,2,1.00,'2026-03-23 16:32:30.558161','PRUS0015',1,2);
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_lignesortielot`
--

LOCK TABLES `stock_lignesortielot` WRITE;
/*!40000 ALTER TABLE `stock_lignesortielot` DISABLE KEYS */;
INSERT INTO `stock_lignesortielot` VALUES (1,2,0.00,1.00,1,2),(2,2,0.00,1.00,2,3);
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
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_mouvementcaisse_devise_id_338fdfd8_fk_stock_devise_id` (`devise_id`),
  KEY `stock_mouvementcaisse_entree_id_e4bddbfa_fk_stock_entree_id` (`entree_id`),
  KEY `stock_mouvementcaisse_sortie_id_a52a187c_fk_stock_sortie_id` (`sortie_id`),
  KEY `stock_mouve_entrepr_bd2459_idx` (`entreprise_id`),
  KEY `stock_mouve_succurs_0d3ad9_idx` (`succursale_id`),
  KEY `stock_mouve_entrepr_c4f4c1_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_mouvementcaiss_entreprise_id_3e634145_fk_stock_ent` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_mouvementcaiss_succursale_id_d90c42e9_fk_stock_suc` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`),
  CONSTRAINT `stock_mouvementcaisse_devise_id_338fdfd8_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_mouvementcaisse_entree_id_e4bddbfa_fk_stock_entree_id` FOREIGN KEY (`entree_id`) REFERENCES `stock_entree` (`id`),
  CONSTRAINT `stock_mouvementcaisse_sortie_id_a52a187c_fk_stock_sortie_id` FOREIGN KEY (`sortie_id`) REFERENCES `stock_sortie` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_mouvementcaisse`
--

LOCK TABLES `stock_mouvementcaisse` WRITE;
/*!40000 ALTER TABLE `stock_mouvementcaisse` DISABLE KEYS */;
INSERT INTO `stock_mouvementcaisse` VALUES (1,'2026-03-23 16:30:19.838142',2.00,'ENTREE','Vente sortie #1 - USD','Cash',NULL,1,NULL,1,1,NULL),(2,'2026-03-23 16:32:30.574160',2.00,'ENTREE','Vente sortie #2 - USD','Cash',NULL,1,NULL,2,1,NULL);
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
  `reference` varchar(100) DEFAULT NULL,
  `dette_id` bigint NOT NULL,
  `devise_id` bigint DEFAULT NULL,
  `utilisateur_id` bigint DEFAULT NULL,
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_paiementdette_dette_id_11c70796_fk_stock_detteclient_id` (`dette_id`),
  KEY `stock_paiementdette_devise_id_37ca7a0d_fk_stock_devise_id` (`devise_id`),
  KEY `stock_paiementdette_utilisateur_id_0f570acb_fk_users_user_id` (`utilisateur_id`),
  KEY `stock_paiementdette_succursale_id_734f0406_fk_stock_suc` (`succursale_id`),
  KEY `stock_paiem_entrepr_0ffc77_idx` (`entreprise_id`),
  KEY `stock_paiem_entrepr_c82dab_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_paiementdette_dette_id_11c70796_fk_stock_detteclient_id` FOREIGN KEY (`dette_id`) REFERENCES `stock_detteclient` (`id`),
  CONSTRAINT `stock_paiementdette_devise_id_37ca7a0d_fk_stock_devise_id` FOREIGN KEY (`devise_id`) REFERENCES `stock_devise` (`id`),
  CONSTRAINT `stock_paiementdette_entreprise_id_efe944a4_fk_stock_ent` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_paiementdette_succursale_id_734f0406_fk_stock_suc` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`),
  CONSTRAINT `stock_paiementdette_utilisateur_id_0f570acb_fk_users_user_id` FOREIGN KEY (`utilisateur_id`) REFERENCES `users_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_paiementdette`
--

LOCK TABLES `stock_paiementdette` WRITE;
/*!40000 ALTER TABLE `stock_paiementdette` DISABLE KEYS */;
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
  `statut` varchar(20) NOT NULL,
  `date_creation` datetime(6) NOT NULL,
  `client_id` varchar(20) DEFAULT NULL,
  `devise_id` bigint DEFAULT NULL,
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_sortie`
--

LOCK TABLES `stock_sortie` WRITE;
/*!40000 ALTER TABLE `stock_sortie` DISABLE KEYS */;
INSERT INTO `stock_sortie` VALUES (1,'Vente au Client','PAYEE','2026-03-23 16:30:19.718161','CLI0001',NULL,1,NULL),(2,'Vente au Client','PAYEE','2026-03-23 16:32:30.534163','CLI0001',NULL,1,NULL);
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
) ENGINE=InnoDB AUTO_INCREMENT=48 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_soustypearticle`
--

LOCK TABLES `stock_soustypearticle` WRITE;
/*!40000 ALTER TABLE `stock_soustypearticle` DISABLE KEYS */;
INSERT INTO `stock_soustypearticle` VALUES (1,'Cahiers & papiers','',1,1,NULL),(2,'Stylos, crayons & écriture','',1,1,NULL),(3,'Papier','',1,1,NULL),(4,'Classement & organisation','',1,1,NULL),(5,'Enveloppes & emballages','',1,1,NULL),(6,'Agrafage & collage','',1,1,NULL),(7,'Produits de base','',3,1,NULL),(8,'Produits frais & naturels','',3,1,NULL),(9,'Biscuits & snacks','',3,1,NULL),(10,'Produits laitiers','',3,1,NULL),(11,'Boissons & jus','',3,1,NULL),(12,'Matières pour pâtisserie','',3,1,NULL),(13,'Ustensiles de cuisine','',4,1,NULL),(14,'Nettoyage & entretien','',4,1,NULL),(15,'Consommables ménage','',4,1,NULL),(16,'Savons','',5,1,NULL),(17,'Dentifrices & soins bouche','',5,1,NULL),(18,'Crèmes & lotions','',5,1,NULL),(19,'Pommades & gels','',5,1,NULL),(20,'Glycerines','',5,1,NULL),(21,'Parfums & poudres','',5,1,NULL),(22,'Serviettes hygiéniques','',6,1,NULL),(23,'Produits bébé','',6,1,NULL),(24,'Sous-vêtements','',8,1,NULL),(25,'Chaussettes & habits','',8,1,NULL),(26,'Chaussures & accessoires','',8,1,NULL),(27,'Bible','',9,1,NULL),(28,'Livre','',9,1,NULL),(29,'Stockage & accessoires','',10,1,NULL),(30,'Energie & connexion','',10,1,NULL),(31,'Piles','',10,1,NULL),(32,'Divers','',10,1,NULL),(33,'Pagne','',8,1,NULL),(34,'Classeurs','',1,1,NULL),(35,'Fardes','',1,1,NULL),(36,'Encre','',1,1,NULL),(37,'Marqueur','',1,1,NULL),(38,'Chemise','',8,1,NULL),(39,'Singlet','',8,1,NULL),(40,'Cadenat','',11,1,NULL),(41,'Agenda','',1,1,NULL),(42,'PowerBank','',10,1,NULL),(43,'Fleurs','',12,1,NULL),(44,'Emballage Cadeau','',12,1,NULL),(45,'Colle','',11,1,NULL),(46,'Produit pour Cheveux','',5,1,NULL),(47,'Nettoyage toilette','',13,1,NULL);
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
) ENGINE=InnoDB AUTO_INCREMENT=362 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_stock`
--

LOCK TABLES `stock_stock` WRITE;
/*!40000 ALTER TABLE `stock_stock` DISABLE KEYS */;
INSERT INTO `stock_stock` VALUES (1,0,0,'FOAG0001'),(2,0,0,'FOAG0002'),(3,0,0,'PRCO0001'),(4,0,0,'PRCO0002'),(5,0,0,'PRCO0003'),(6,0,0,'PRPA0001'),(7,0,0,'PRPA0002'),(8,0,0,'FOST0001'),(9,0,0,'PRPR0001'),(10,0,0,'PRNE0001'),(11,0,0,'PRNE0002'),(12,0,0,'PRBI0001'),(13,0,0,'FOST0002'),(14,0,0,'FOST0003'),(15,0,0,'FOMA0001'),(16,0,0,'FOMA0002'),(17,0,0,'PRBI0002'),(18,0,0,'PRBI0003'),(19,0,0,'PRBI0004'),(20,0,0,'PRBI0005'),(21,0,0,'PRBI0006'),(22,0,0,'PRBI0007'),(23,0,0,'PRBI0008'),(24,0,0,'PRBI0009'),(25,0,0,'PRDI0001'),(26,0,0,'FOCL0001'),(27,0,0,'PRUS0001'),(28,0,0,'PRUS0002'),(29,0,0,'PRBI0010'),(30,0,0,'PRBI0011'),(31,0,0,'PRBI0012'),(32,0,0,'PRBI0013'),(33,0,0,'PRMA0001'),(34,0,0,'PRFL0001'),(35,0,0,'PRFL0002'),(36,0,0,'PRFL0003'),(37,0,0,'PRDE0001'),(38,0,0,'PRDE0002'),(39,0,0,'PRDE0003'),(40,0,0,'PRDI0002'),(41,0,0,'PRDI0003'),(42,0,0,'PRDI0004'),(43,0,0,'PRDI0005'),(44,0,0,'PRPA0003'),(45,0,0,'FOCA0001'),(46,0,0,'FOCA0002'),(47,0,0,'FOCA0003'),(48,0,0,'FOCA0004'),(49,0,0,'FOCA0005'),(50,0,0,'FOCA0006'),(51,0,0,'FOCA0007'),(52,0,0,'FOCA0008'),(53,0,0,'FOCA0009'),(54,0,0,'FOCA0010'),(55,0,0,'FOCA0011'),(56,0,0,'FOCA0012'),(57,0,0,'PRLI0001'),(58,0,0,'PRST0001'),(59,0,0,'PRST0002'),(60,0,0,'PRST0003'),(61,0,0,'PRMA0002'),(62,0,0,'PRDI0006'),(63,0,0,'PRDI0007'),(64,0,0,'PRDI0008'),(65,0,0,'HACH0001'),(66,0,0,'HACH0002'),(67,0,0,'HACH0003'),(68,0,0,'HACH0004'),(69,0,0,'HACH0005'),(70,0,0,'ARCO0001'),(71,0,0,'ARCO0002'),(72,0,0,'ARCO0003'),(73,0,0,'PRMA0003'),(74,0,0,'PRFL0004'),(75,0,0,'FOCA0013'),(76,0,0,'FOCA0014'),(77,0,0,'PRCR0001'),(78,0,0,'PRCR0002'),(79,0,0,'PRCR0003'),(80,0,0,'PRCR0004'),(81,0,0,'PRCR0005'),(82,0,0,'PRCR0006'),(83,0,0,'PRCR0007'),(84,0,0,'PRCR0008'),(85,0,0,'PRCR0009'),(86,0,0,'PRCR0010'),(87,0,0,'PRCR0011'),(88,0,0,'PRCR0012'),(89,0,0,'PRCR0013'),(90,0,0,'PRCR0014'),(91,0,0,'PRCR0015'),(92,0,0,'PRCR0016'),(93,0,0,'PRCR0017'),(94,0,0,'PRDE0004'),(95,0,0,'PRUS0003'),(96,0,0,'PRUS0004'),(97,0,0,'PRDE0005'),(98,0,0,'PRDE0006'),(99,0,0,'PRDE0007'),(100,0,0,'PRDE0008'),(101,0,0,'PRBO0001'),(102,0,0,'PRBO0002'),(103,0,0,'PRBO0003'),(104,0,0,'PRBO0004'),(105,0,0,'PRMA0004'),(106,0,0,'PRST0004'),(107,0,0,'PREM0001'),(108,0,0,'PREM0002'),(109,0,0,'PREM0003'),(110,0,0,'PREM0004'),(111,0,0,'PREM0005'),(112,0,0,'PREM0006'),(113,0,0,'FOEN0001'),(114,0,0,'FOFA0001'),(115,0,0,'FOFA0002'),(116,0,0,'PRMA0005'),(117,0,0,'PRMA0006'),(118,0,0,'PRDI0009'),(119,0,0,'PRDI0010'),(120,0,0,'PRST0005'),(121,0,0,'PRST0006'),(122,0,0,'PRST0007'),(123,0,0,'PRMA0007'),(124,0,0,'PRFL0005'),(125,0,0,'PRFL0006'),(126,0,0,'PRGL0001'),(127,0,0,'PRGL0002'),(128,0,0,'PRGL0003'),(129,0,0,'PRGL0004'),(130,0,0,'PRGL0005'),(131,0,0,'PRGL0006'),(132,0,0,'PRGL0007'),(133,0,0,'PRGL0008'),(134,0,0,'PRGL0009'),(135,0,0,'PRGL0010'),(136,0,0,'PRGL0011'),(137,0,0,'PRGL0012'),(138,0,0,'PRUS0005'),(139,0,0,'PRUS0006'),(140,0,0,'PRUS0007'),(141,0,0,'FOST0004'),(142,0,0,'FOST0005'),(143,0,0,'PRMA0008'),(144,0,0,'ARCO0004'),(145,0,0,'FOCA0015'),(146,0,0,'FOCA0016'),(147,0,0,'PRBO0005'),(148,0,0,'PRBO0006'),(149,0,0,'PRBO0007'),(150,0,0,'PRBO0008'),(151,0,0,'PRBO0009'),(152,0,0,'PRBO0010'),(153,0,0,'PRBO0011'),(154,0,0,'PRBO0012'),(155,0,0,'PRBO0013'),(156,0,0,'PRBO0014'),(157,0,0,'PRBO0015'),(158,0,0,'PRBO0016'),(159,0,0,'PRBO0017'),(160,0,0,'PRBO0018'),(161,0,0,'PRBO0019'),(162,0,0,'FOCA0017'),(163,0,0,'PRMA0009'),(164,0,0,'PRMA0010'),(165,0,0,'PRMA0011'),(166,0,0,'PRCR0018'),(167,0,0,'PRCR0019'),(168,0,0,'PRCR0020'),(169,0,0,'PRCR0021'),(170,0,0,'PRCR0022'),(171,0,0,'PRCR0023'),(172,0,0,'PRCR0024'),(173,0,0,'PRCO0004'),(174,0,0,'PRCO0005'),(175,0,0,'FOCA0018'),(176,0,0,'FOST0006'),(177,0,0,'FOST0007'),(178,0,0,'PRPO0001'),(179,0,0,'PRPO0002'),(180,0,0,'FOCA0019'),(181,0,0,'FOPA0001'),(182,0,0,'FOPA0002'),(183,0,0,'FOPA0003'),(184,0,0,'FOPA0004'),(185,0,0,'FOPA0005'),(186,0,0,'PRSE0001'),(187,0,0,'FOPA0006'),(188,0,0,'FOPA0007'),(189,0,0,'FOPA0008'),(190,0,0,'FOPA0009'),(191,0,0,'PRSE0002'),(192,0,0,'PRSE0003'),(193,0,0,'PRSE0004'),(194,0,0,'FOPA0010'),(195,0,0,'PRPA0004'),(196,0,0,'PRPA0005'),(197,0,0,'PRPA0006'),(198,0,0,'FOCA0020'),(199,0,0,'PRPI0001'),(200,0,0,'PRPI0002'),(201,0,0,'PRPI0003'),(202,0,0,'PRPI0004'),(203,0,0,'PRPI0005'),(204,0,0,'PRUS0008'),(205,0,0,'PRUS0009'),(206,0,0,'PRPO0003'),(207,0,0,'PRPO0004'),(208,0,0,'PRPO0005'),(209,0,0,'PRPO0006'),(210,0,0,'PRPO0007'),(211,0,0,'PRPO0008'),(212,0,0,'PRPO0009'),(213,0,0,'PRPO0010'),(214,0,0,'PRPO0011'),(215,0,0,'PRPO0012'),(216,0,0,'PRPO0013'),(217,0,0,'PRPO0014'),(218,0,0,'PRPO0015'),(219,0,0,'PRPO0016'),(220,0,0,'PRPO0017'),(221,0,0,'PRPO0018'),(222,0,0,'PRPO0019'),(223,0,0,'PRPO0020'),(224,0,0,'PRPO0021'),(225,0,0,'PRPO0022'),(226,0,0,'PRPO0023'),(227,0,0,'PRPO0024'),(228,0,0,'PRPO0025'),(229,0,0,'PRPO0026'),(230,0,0,'PRPO0027'),(231,0,0,'PRPO0028'),(232,0,0,'PRPA0007'),(233,0,0,'PRPA0008'),(234,0,0,'PRPA0009'),(235,0,0,'PRPA0010'),(236,0,0,'PRMA0012'),(237,0,0,'PRMA0013'),(238,0,0,'PRDI0011'),(239,0,0,'PRDI0012'),(240,0,0,'PRSA0001'),(241,0,0,'PRSA0002'),(242,0,0,'PRSA0003'),(243,0,0,'PRSA0004'),(244,0,0,'PRSA0005'),(245,0,0,'PRSA0006'),(246,0,0,'PRSA0007'),(247,0,0,'PRSA0008'),(248,0,0,'PRSA0009'),(249,0,0,'PRSA0010'),(250,0,0,'PRSA0011'),(251,0,0,'PRSA0012'),(252,0,0,'PRSA0013'),(253,0,0,'PRSA0014'),(254,0,0,'PRSA0015'),(255,0,0,'PRSA0016'),(256,0,0,'PRSA0017'),(257,0,0,'PRSA0018'),(258,0,0,'PRSA0019'),(259,0,0,'PRSA0020'),(260,0,0,'PRSA0021'),(261,0,0,'HASO0001'),(262,0,0,'HASI0001'),(263,0,0,'HASI0002'),(264,0,0,'HASI0003'),(265,0,0,'HASI0004'),(266,0,0,'HASI0005'),(267,0,0,'HASI0006'),(268,0,0,'HASO0002'),(269,0,0,'HASO0003'),(270,0,0,'HASO0004'),(271,0,0,'HASO0005'),(272,0,0,'HASO0006'),(273,0,0,'HASO0007'),(274,0,0,'HASO0008'),(275,0,0,'FOCA0021'),(276,0,0,'FOCA0022'),(277,0,0,'FOCA0023'),(278,0,0,'PRBO0020'),(279,0,0,'ARCO0005'),(280,0,0,'FOCA0024'),(281,0,0,'PRUS0010'),(282,0,0,'PRUS0011'),(283,0,0,'PRUS0012'),(284,0,0,'PRUS0013'),(285,0,0,'PRUS0014'),(286,0,0,'PRNE0003'),(287,0,0,'PRNE0004'),(288,0,0,'PRNE0005'),(289,0,0,'FOCA0025'),(290,0,0,'ARCO0006'),(291,0,0,'ARCO0007'),(292,0,0,'ARCO0008'),(293,0,0,'PRMA0014'),(294,0,0,'PRMA0015'),(295,0,0,'PRPO0029'),(296,0,0,'PRPO0030'),(297,0,0,'PRPO0031'),(298,0,0,'PRPO0032'),(299,0,0,'PRPO0033'),(300,8,3,'PRSE0005'),(301,0,0,'PRMA0016'),(302,0,0,'PRMA0017'),(303,0,0,'ARCO0009'),(304,0,0,'ARCO0010'),(305,0,0,'ARCO0011'),(306,0,0,'FOMA0003'),(307,0,0,'FOMA0004'),(308,0,0,'ARCO0012'),(309,0,0,'PRGL0013'),(310,0,0,'PRGL0014'),(311,0,0,'PRBI0014'),(312,0,0,'PRLI0002'),(313,0,0,'PRLI0003'),(314,0,0,'PRLI0004'),(315,0,0,'PRLI0005'),(316,0,0,'PRNE0006'),(317,0,0,'PRNE0007'),(318,0,0,'PRLI0006'),(319,0,0,'PRNE0008'),(320,0,0,'PRNE0009'),(321,0,0,'PRNE0010'),(322,0,0,'PRNE0011'),(323,0,0,'PRDE0009'),(324,0,0,'PRDE0010'),(325,0,0,'PRNE0012'),(326,18,10,'PRUS0015'),(327,0,0,'PRCO0006'),(328,0,0,'PRCO0007'),(329,0,0,'PRCO0008'),(330,0,0,'PRCO0009'),(331,0,0,'PRNE0013'),(332,0,0,'PRNE0014'),(333,0,0,'FOST0008'),(334,0,0,'FOST0009'),(335,0,0,'HAPA0001'),(336,0,0,'HAPA0002'),(337,0,0,'HAPA0003'),(338,0,0,'HAPA0004'),(339,0,0,'FOST0010'),(340,0,0,'PRNE0015'),(341,0,0,'FOCA0026'),(342,0,0,'FOCA0027'),(343,0,0,'FOCA0028'),(344,0,0,'PRNE0016'),(345,0,0,'PRNE0017'),(346,0,0,'PRNE0018'),(347,0,0,'PRSE0006'),(348,0,0,'PRSE0007'),(349,0,0,'PRSE0008'),(350,0,0,'PRSE0009'),(351,0,0,'PRSE0010'),(352,0,0,'PRSE0011'),(353,0,0,'PRMA0018'),(354,0,0,'PRMA0019'),(355,0,0,'PRBO0021'),(356,0,0,'PRBO0022'),(357,0,0,'PRPI0006'),(358,0,0,'PRPI0007'),(359,0,0,'PRPI0008'),(360,0,0,'PRPI0009'),(361,0,0,'HASO0009');
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
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_typearticle`
--

LOCK TABLES `stock_typearticle` WRITE;
/*!40000 ALTER TABLE `stock_typearticle` DISABLE KEYS */;
INSERT INTO `stock_typearticle` VALUES (1,'FOURNITURES SCOLAIRES & DE BUREAU','',1,NULL),(3,'PRODUITS ALIMENTAIRES (NOURRITURE)','',1,NULL),(4,'PRODUITS DE CUISINE & MENAGE','',1,NULL),(5,'PRODUITS COSMETIQUES & HYGIENE CORPORELLE','',1,NULL),(6,'PRODUITS FEMININS & BEBE','',1,NULL),(8,'HABILLEMENT & ACCESSOIRES','',1,NULL),(9,'PRODUITS RELIGIEUX','',1,NULL),(10,'PRODUITS ELECTRONIQUES & ACCESSOIRES','',1,NULL),(11,'ARTICLES DIVERS & QUINCAILLERIE LEGERE','',1,NULL),(12,'PRODUITS EVENEMENTIELS','',1,NULL),(13,'NETTOYAGE ET ENTRETIEN MENAGER','',1,NULL);
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
  `entreprise_id` bigint DEFAULT NULL,
  `succursale_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `stock_unite_succursale_id_4f96accc_fk_stock_succursale_id` (`succursale_id`),
  KEY `stock_unite_entrepr_550fdb_idx` (`entreprise_id`),
  KEY `stock_unite_entrepr_40ae77_idx` (`entreprise_id`,`succursale_id`),
  CONSTRAINT `stock_unite_entreprise_id_0b1f0036_fk_stock_entreprise_id` FOREIGN KEY (`entreprise_id`) REFERENCES `stock_entreprise` (`id`),
  CONSTRAINT `stock_unite_succursale_id_4f96accc_fk_stock_succursale_id` FOREIGN KEY (`succursale_id`) REFERENCES `stock_succursale` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `stock_unite`
--

LOCK TABLES `stock_unite` WRITE;
/*!40000 ALTER TABLE `stock_unite` DISABLE KEYS */;
INSERT INTO `stock_unite` VALUES (1,'Litres','',1,NULL),(2,'Kilogramme','',1,NULL),(3,'Pc \\ Pieces','',1,NULL),(4,'Boxes','',1,NULL),(5,'Rame','',1,NULL),(6,'Sac','',1,NULL),(7,'Bouteille','',1,NULL),(8,'Cartons','',1,NULL),(9,'Paquet','',1,NULL),(10,'Plaquettes','',1,NULL),(11,'Rouleau','',1,NULL),(12,'Boite','',1,NULL),(13,'Bar','',1,NULL),(14,'Cuilleur','',1,NULL);
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
) ENGINE=InnoDB AUTO_INCREMENT=25 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `token_blacklist_outstandingtoken`
--

LOCK TABLES `token_blacklist_outstandingtoken` WRITE;
/*!40000 ALTER TABLE `token_blacklist_outstandingtoken` DISABLE KEYS */;
INSERT INTO `token_blacklist_outstandingtoken` VALUES (1,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MTQ5NywiaWF0IjoxNzc0MTg3ODk3LCJqdGkiOiI5ZTg5OGRjYTIxNjM0NDNjOTlmZTQ2NjAwNTI4Mzg0NSIsInVzZXJfaWQiOiIxIn0.fY3fV-oW0ZM82ZXenk1dXk8oAJpjPMdNWiaGCztTecI','2026-03-22 13:58:17.623444','2026-03-22 14:58:17.000000',1,'9e898dca2163443c99fe466005283845'),(2,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MTg5MSwiaWF0IjoxNzc0MTg4MjkxLCJqdGkiOiIyNzlhZjUzYmY2MGI0MWU3YjZjMzQyZTExZGYxMWI3NyIsInVzZXJfaWQiOiIxIn0.mRT9p-jUeyClktEujOn8KILtm9utORe_JMgr6Br26kE','2026-03-22 14:04:51.772454','2026-03-22 15:04:51.000000',1,'279af53bf60b41e7b6c342e11df11b77'),(3,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MjA5MiwiaWF0IjoxNzc0MTg4NDkyLCJqdGkiOiIxNTIzOGZiYWYxNzc0MmUzYmRjMDczNDYxYjQ0NThiNiIsInVzZXJfaWQiOiIyIn0.TC22ls_jJV6d9awV7tXZrlk_1qSxEwVjuNKmQEl2jig','2026-03-22 14:08:12.762754','2026-03-22 15:08:12.000000',2,'15238fbaf17742e3bdc073461b4458b6'),(4,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MjA5MywiaWF0IjoxNzc0MTg4NDkzLCJqdGkiOiJhMmQxNzdlNzkxNDM0YTE4ODYyYTY3MTk2MGJmMjA5OCIsInVzZXJfaWQiOiIyIn0.L_rngrIiDMFTbnPZMFDHwEBbuC4QDOXdloOiJV3VGfc','2026-03-22 14:08:13.395680','2026-03-22 15:08:13.000000',2,'a2d177e791434a18862a671960bf2098'),(5,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MjExNSwiaWF0IjoxNzc0MTg4NTE1LCJqdGkiOiJhNDhmNzY4MTZkYzM0YWMwOTY4ZGEzZDUxYjYxMmQwNyIsInVzZXJfaWQiOiIxIn0.NzmC1sASVW_AOX9j_GUD9-1jy_aDFOzlBwpZMv-sfO4','2026-03-22 14:08:35.239807','2026-03-22 15:08:35.000000',1,'a48f76816dc34ac0968da3d51b612d07'),(6,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5MjExNSwiaWF0IjoxNzc0MTg4NTE1LCJqdGkiOiIxMjY0NzI0MTIxMWI0NWFlYTgwZDJkMTY4MWVhYjdhYyIsInVzZXJfaWQiOiIxIn0._TsL8jlv7g5A0bkI7guGp6Nbo58Kqd4XOG2Gdol1LBE','2026-03-22 14:08:35.440363','2026-03-22 15:08:35.000000',1,'12647241211b45aea80d2d1681eab7ac'),(7,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5NTgxMCwiaWF0IjoxNzc0MTkyMjEwLCJqdGkiOiJiNzkzYTcyMGQyMGY0YzI5OWFhMjBlYmNlZjVlNjI4OCIsInVzZXJfaWQiOiIxIn0.SWfSOSPWHE6zwJpfyoeaHutQibAqKRfJ_v09HI1Y6bM','2026-03-22 15:10:10.722815','2026-03-22 16:10:10.000000',1,'b793a720d20f4c299aa20ebcef5e6288'),(8,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDE5NTgxMCwiaWF0IjoxNzc0MTkyMjEwLCJqdGkiOiI0MWMyOGVkODhkN2Y0NWFhOWI0NDFlYWI4ODk2MGE5NCIsInVzZXJfaWQiOiIxIn0.VlpWDrei-jGF_BsZ8h7UTxbB5Z1B3Wzz28qELX4zeuQ','2026-03-22 15:10:10.976756','2026-03-22 16:10:10.000000',1,'41c28ed88d7f45aa9b441eab88960a94'),(9,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDIwNDU1MiwiaWF0IjoxNzc0MjAwOTUyLCJqdGkiOiI4OGM1NThkMmJhOTY0ZjM5OTUwOWEwYTBhNDJhYTViNCIsInVzZXJfaWQiOiIxIn0.IahkcGytNDTXTFDoS0eVW_p7PhGNuEBCDZR00dLZHp8','2026-03-22 17:35:52.087883','2026-03-22 18:35:52.000000',1,'88c558d2ba964f399509a0a0a42aa5b4'),(10,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDIwNDU1MiwiaWF0IjoxNzc0MjAwOTUyLCJqdGkiOiJiMTNmYjFmZTkxYWI0YzM2YTY2MGYyZmIyODQyNjk3ZSIsInVzZXJfaWQiOiIxIn0.vz-7kh6BVlVXr5Guf3SZck2tHEWQ8cSOnmzBtO6KAk4','2026-03-22 17:35:52.444280','2026-03-22 18:35:52.000000',1,'b13fb1fe91ab4c36a660f2fb2842697e'),(11,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI1NzQ0NSwiaWF0IjoxNzc0MjUzODQ1LCJqdGkiOiI2YjIzNjg0ZTI5NDU0MmRiYjA1NzllZTNhM2JmZDMyYyIsInVzZXJfaWQiOiIxIn0.h0V2Gi9PPiHDebaYOwuObX_qE_MTiS1T5AQ-Ac3uI8A','2026-03-23 08:17:25.695797','2026-03-23 09:17:25.000000',1,'6b23684e294542dbb0579ee3a3bfd32c'),(12,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI1NzQ0NiwiaWF0IjoxNzc0MjUzODQ2LCJqdGkiOiJkMDU4M2M5OWE0Zjg0ZmFmODFkZjRhMWI4N2MyMjcxYSIsInVzZXJfaWQiOiIxIn0.1ExzTOYlXoqowcF1k3a0hZjtq_zAbKQGEKoe1R9hqpg','2026-03-23 08:17:26.366125','2026-03-23 09:17:26.000000',1,'d0583c99a4f84faf81df4a1b87c2271a'),(13,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI2MTM4MSwiaWF0IjoxNzc0MjU3NzgxLCJqdGkiOiI4YjU4NzI5YjUzODE0MDQ3OWZhMTBmOTIwNjZiYTRhYyIsInVzZXJfaWQiOiIxIn0.a_2vAw2vpWhKv7nhLXAo2YouTcaDzTDoe68zGz_Df74','2026-03-23 09:23:01.549583','2026-03-23 10:23:01.000000',1,'8b58729b538140479fa10f92066ba4ac'),(14,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI2MTM4MSwiaWF0IjoxNzc0MjU3NzgxLCJqdGkiOiI3MzRhNjljYzBkZDM0OTQ4YTc5NDBhMWZhNDE2OTRjMyIsInVzZXJfaWQiOiIxIn0.OQwqHllC1RPCoG3uJXJsGpIhqXYeLiNyt0ySO_Eo92Y','2026-03-23 09:23:01.804404','2026-03-23 10:23:01.000000',1,'734a69cc0dd34948a7940a1fa41694c3'),(15,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI2NTAzMSwiaWF0IjoxNzc0MjYxNDMxLCJqdGkiOiI3MDI1NzNhNDM3YzA0OGRiYjY4MTU4MDJjYjAxMGNhMiIsInVzZXJfaWQiOiIxIn0.ht3x2TmgvwkffI2GzCHjaPUwNHUqGZgDdg25tpWh1q4','2026-03-23 10:23:51.405659','2026-03-23 11:23:51.000000',1,'702573a437c048dbb6815802cb010ca2'),(16,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI2NTAzMSwiaWF0IjoxNzc0MjYxNDMxLCJqdGkiOiIyZWU3ZmFmOWU3NDc0YTk3ODhkNzIwZjA0OTFhZWJjMyIsInVzZXJfaWQiOiIxIn0.lzad4O1rRqer3vMXTjafPsW_027LXkj_hwbmV5Eymow','2026-03-23 10:23:51.722766','2026-03-23 11:23:51.000000',1,'2ee7faf9e7474a9788d720f0491aebc3'),(17,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI3NzU0OCwiaWF0IjoxNzc0MjczOTQ4LCJqdGkiOiIxY2ZmMjY5ZDAwMDg0MTc1ODMyMjQwZjg3MGI1MjUxMyIsInVzZXJfaWQiOiIxIn0.m0K6KLhcg8N3Jw1spLPQmW1XHDXfZD6gVhcd1Mmr0xM','2026-03-23 13:52:28.354303','2026-03-23 14:52:28.000000',1,'1cff269d00084175832240f870b52513'),(18,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI3NzU2NSwiaWF0IjoxNzc0MjczOTY1LCJqdGkiOiJhNDc2ZTllYWYzNDE0NWQ5ODQ3ZmUyMDhmYmI5NzBhMCIsInVzZXJfaWQiOiIxIn0.-ocEQ1xd6yFSulHkAg9U-gJ6Mm7jvOxfxGKnAwhGEFI','2026-03-23 13:52:45.971015','2026-03-23 14:52:45.000000',1,'a476e9eaf34145d9847fe208fbb970a0'),(19,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI4NDM4OSwiaWF0IjoxNzc0MjgwNzg5LCJqdGkiOiIxNGUzYjgwMjMyNGI0ZmQ5OWZmYzI5NWIxZmE5MTM5OSIsInVzZXJfaWQiOiIxIn0.yKdCOl6AXt4naIxBJ5vY1cySvb_GnT9r8uyahVR3y2Y','2026-03-23 15:46:29.991920','2026-03-23 16:46:29.000000',1,'14e3b802324b4fd99ffc295b1fa91399'),(20,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NDI4NDM5MCwiaWF0IjoxNzc0MjgwNzkwLCJqdGkiOiIzZTg4NzIzYjFiZGI0MWE0OTkzOTMwYWQ4YzFiMjMzZSIsInVzZXJfaWQiOiIxIn0.sOC8NciJ5EDiTGpstXZr87y_fGeMzVxrZezOuehccIM','2026-03-23 15:46:30.443674','2026-03-23 16:46:30.000000',1,'3e88723b1bdb41a4993930ad8c1b233e'),(21,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NTA2MTA4OSwiaWF0IjoxNzc1MDU3NDg5LCJqdGkiOiIyMTY2ZmRkNGM4N2E0ZGRlYTc3M2E1YmY2YWNmOWYyZCIsInVzZXJfaWQiOiIxIn0.DeqLzN1j-wEDNeJFLsu4W_M8JsSLAm3jmn1VUMJRxgA','2026-04-01 15:31:29.724237','2026-04-01 16:31:29.000000',1,'2166fdd4c87a4ddea773a5bf6acf9f2d'),(22,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NTA2MTA5NSwiaWF0IjoxNzc1MDU3NDk1LCJqdGkiOiIxMmQxZTFhZWU2ZTE0N2JmOWI3ZjUxOWVjYmMyZmZhMyIsInVzZXJfaWQiOiIxIn0.T7rT-m1FAG42oww9OtTUuQk31pUaHWw_i_jrmcY1Ok4','2026-04-01 15:31:35.362768','2026-04-01 16:31:35.000000',1,'12d1e1aee6e147bf9b7f519ecbc2ffa3'),(23,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NTM5MDMyMiwiaWF0IjoxNzc1Mzg2NzIyLCJqdGkiOiI4OGYzMjcyYzc0NjU0MTExOTgwZGQ5N2U4MDA3ODRhMCIsInVzZXJfaWQiOiIxIn0.kVsjavcyKaD1f1wemjRmYapQUVpoq0SIbyQ0M2QsY84','2026-04-05 10:58:42.974175','2026-04-05 11:58:42.000000',1,'88f3272c74654111980dd97e800784a0'),(24,'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTc3NTM5MDMyNiwiaWF0IjoxNzc1Mzg2NzI2LCJqdGkiOiI5Y2RlZmM4MTVjMGQ0YTAyYWYxYTYyYTY4MzMyOTJhZiIsInVzZXJfaWQiOiIxIn0.Fa7dcNmQk-qDTyYIo2FCxGuzNGSm6UVWAcayFQVdkhg','2026-04-05 10:58:46.784558','2026-04-05 11:58:46.000000',1,'9cdefc815c0d4a02af1a62a6833292af');
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
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users_user`
--

LOCK TABLES `users_user` WRITE;
/*!40000 ALTER TABLE `users_user` DISABLE KEYS */;
INSERT INTO `users_user` VALUES (1,'pbkdf2_sha256$1000000$x7mE2m8iGEwOYHMsLiE1OT$WvQnx8DkLFp3yXAlrlHwor+27anruM1qFhFGp7v1Jzo=','2026-04-05 10:58:44.879345',0,'console','console','malambo','consolemalmabo@gmail.com',0,1,'2026-03-22 13:57:43.186852','admin'),(2,'pbkdf2_sha256$1000000$62Vg6xVH3qgp6coW3MtgXv$YFVzYXtBYCHiRPxBUuhlnn6j6NIkhEUp+6zzkBU950Q=','2026-03-22 14:08:12.978947',0,'mireille','','','mireille@gmail.com',0,1,'2026-03-22 14:07:20.034243','user');
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

-- Dump completed on 2026-04-05 13:06:11
