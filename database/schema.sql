-- ONLINE EXAMINATION SYSTEM
-- Domain DDL generated from the migrated MySQL 8 schema.
-- Questions live in the bank. exam_questions is the master paper.
-- attempt_questions freezes the shuffled paper. attempt_option_orders
-- freezes the shuffled MCQ option order for that attempt.
-- Reports are queries, so there is no report table.
-- Django migrate also creates contenttypes, auth, admin, and session tables.
-- Apply this file with oes_migrator. The application connects as oes_app.


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password_hash` varchar(128) COLLATE utf8mb4_unicode_ci NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(254) COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `active` tinyint(1) NOT NULL,
  `created_at` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `user_role_idx` (`role`),
  CONSTRAINT `user_role_valid` CHECK ((`role` in (_utf8mb4'STUDENT',_utf8mb4'FACULTY',_utf8mb4'ADMIN')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `subjects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subjects` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `topics`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `topics` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(150) COLLATE utf8mb4_unicode_ci NOT NULL,
  `subject_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `topic_subject_name_uniq` (`subject_id`,`name`),
  CONSTRAINT `topics_subject_id_d544fc3c_fk_subjects_id` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `questions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `type` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `text` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `difficulty` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `marks` decimal(6,2) NOT NULL,
  `explanation` longtext COLLATE utf8mb4_unicode_ci,
  `active` tinyint(1) NOT NULL,
  `created_by_id` bigint NOT NULL,
  `subject_id` bigint NOT NULL,
  `topic_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `questions_topic_id_6b28e0da_fk_topics_id` (`topic_id`),
  KEY `question_bank_idx` (`subject_id`,`type`,`difficulty`),
  KEY `question_active_idx` (`active`),
  KEY `questions_created_by_id_9672a6d2_fk_users_id` (`created_by_id`),
  CONSTRAINT `questions_created_by_id_9672a6d2_fk_users_id` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`),
  CONSTRAINT `questions_subject_id_87289572_fk_subjects_id` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`),
  CONSTRAINT `questions_topic_id_6b28e0da_fk_topics_id` FOREIGN KEY (`topic_id`) REFERENCES `topics` (`id`),
  CONSTRAINT `question_difficulty_valid` CHECK ((`difficulty` in (_utf8mb4'EASY',_utf8mb4'MEDIUM',_utf8mb4'HARD'))),
  CONSTRAINT `question_marks_positive` CHECK ((`marks` > 0)),
  CONSTRAINT `question_type_valid` CHECK ((`type` in (_utf8mb4'MCQ',_utf8mb4'DESCRIPTIVE')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `question_options`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `question_options` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `option_text` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `is_correct` tinyint(1) NOT NULL,
  `question_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `question_options_question_id_10370079_fk_questions_id` (`question_id`),
  CONSTRAINT `question_options_question_id_10370079_fk_questions_id` FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `exams`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exams` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `instructions` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `start_at` datetime(6) NOT NULL,
  `end_at` datetime(6) NOT NULL,
  `duration_minutes` int unsigned NOT NULL,
  `pass_marks` decimal(6,2) NOT NULL,
  `negative_mark` decimal(6,2) NOT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_by_id` bigint NOT NULL,
  `subject_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `exam_window_idx` (`status`,`start_at`,`end_at`),
  KEY `exams_created_by_id_6cd46f54_fk_users_id` (`created_by_id`),
  KEY `exams_subject_id_9f278c89_fk_subjects_id` (`subject_id`),
  CONSTRAINT `exams_created_by_id_6cd46f54_fk_users_id` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`id`),
  CONSTRAINT `exams_subject_id_9f278c89_fk_subjects_id` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`id`),
  CONSTRAINT `exam_duration_positive` CHECK ((`duration_minutes` > 0)),
  CONSTRAINT `exam_negative_non_negative` CHECK ((`negative_mark` >= 0)),
  CONSTRAINT `exam_pass_marks_non_negative` CHECK ((`pass_marks` >= 0)),
  CONSTRAINT `exam_status_valid` CHECK ((`status` in (_utf8mb4'DRAFT',_utf8mb4'PUBLISHED',_utf8mb4'CLOSED'))),
  CONSTRAINT `exam_window_order` CHECK ((`end_at` > `start_at`)),
  CONSTRAINT `exams_chk_1` CHECK ((`duration_minutes` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `exam_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exam_questions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `exam_id` bigint NOT NULL,
  `question_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `exam_question_uniq` (`exam_id`,`question_id`),
  KEY `exam_questions_question_id_fbc99364_fk_questions_id` (`question_id`),
  CONSTRAINT `exam_questions_exam_id_19ce11e5_fk_exams_id` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`),
  CONSTRAINT `exam_questions_question_id_fbc99364_fk_questions_id` FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `exam_attempts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exam_attempts` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `started_at` datetime(6) NOT NULL,
  `submitted_at` datetime(6) DEFAULT NULL,
  `status` varchar(20) COLLATE utf8mb4_unicode_ci NOT NULL,
  `exam_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `one_attempt_per_student` (`exam_id`,`user_id`),
  KEY `attempt_user_idx` (`user_id`),
  CONSTRAINT `exam_attempts_exam_id_e9bb1335_fk_exams_id` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`),
  CONSTRAINT `exam_attempts_user_id_0a725b49_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `attempt_status_valid` CHECK ((`status` in (_utf8mb4'IN_PROGRESS',_utf8mb4'SUBMITTED',_utf8mb4'EVALUATED')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `attempt_questions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attempt_questions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `display_order` int unsigned NOT NULL,
  `question_id` bigint NOT NULL,
  `attempt_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `attempt_question_uniq` (`attempt_id`,`question_id`),
  UNIQUE KEY `attempt_order_uniq` (`attempt_id`,`display_order`),
  KEY `attempt_questions_question_id_f60d1575_fk_questions_id` (`question_id`),
  CONSTRAINT `attempt_questions_attempt_id_f63f6f13_fk_exam_attempts_id` FOREIGN KEY (`attempt_id`) REFERENCES `exam_attempts` (`id`),
  CONSTRAINT `attempt_questions_question_id_f60d1575_fk_questions_id` FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`),
  CONSTRAINT `attempt_questions_chk_1` CHECK ((`display_order` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `attempt_option_orders`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attempt_option_orders` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `display_order` int unsigned NOT NULL,
  `option_id` bigint NOT NULL,
  `attempt_question_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `attempt_option_uniq` (`attempt_question_id`,`option_id`),
  UNIQUE KEY `attempt_option_order_uniq` (`attempt_question_id`,`display_order`),
  KEY `attempt_option_orders_option_id_21cab5af_fk_question_options_id` (`option_id`),
  CONSTRAINT `attempt_option_order_attempt_question_id_32b87598_fk_attempt_q` FOREIGN KEY (`attempt_question_id`) REFERENCES `attempt_questions` (`id`),
  CONSTRAINT `attempt_option_orders_option_id_21cab5af_fk_question_options_id` FOREIGN KEY (`option_id`) REFERENCES `question_options` (`id`),
  CONSTRAINT `attempt_option_orders_chk_1` CHECK ((`display_order` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `attempt_answers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attempt_answers` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `descriptive_text` longtext COLLATE utf8mb4_unicode_ci,
  `marked_for_review` tinyint(1) NOT NULL DEFAULT '0',
  `awarded_marks` decimal(6,2) DEFAULT NULL,
  `evaluated_at` datetime(6) DEFAULT NULL,
  `evaluated_by_id` bigint DEFAULT NULL,
  `question_id` bigint NOT NULL,
  `selected_option_id` bigint DEFAULT NULL,
  `attempt_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `attempt_answer_uniq` (`attempt_id`,`question_id`),
  KEY `answer_attempt_idx` (`attempt_id`),
  KEY `attempt_answers_evaluated_by_id_b78185cb_fk_users_id` (`evaluated_by_id`),
  KEY `attempt_answers_question_id_e34489ec_fk_questions_id` (`question_id`),
  KEY `attempt_answers_selected_option_id_c8144cc6_fk_question_` (`selected_option_id`),
  CONSTRAINT `attempt_answers_attempt_id_6ed91d37_fk_exam_attempts_id` FOREIGN KEY (`attempt_id`) REFERENCES `exam_attempts` (`id`),
  CONSTRAINT `attempt_answers_evaluated_by_id_b78185cb_fk_users_id` FOREIGN KEY (`evaluated_by_id`) REFERENCES `users` (`id`),
  CONSTRAINT `attempt_answers_question_id_e34489ec_fk_questions_id` FOREIGN KEY (`question_id`) REFERENCES `questions` (`id`),
  CONSTRAINT `attempt_answers_selected_option_id_c8144cc6_fk_question_` FOREIGN KEY (`selected_option_id`) REFERENCES `question_options` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `results` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `objective_marks` decimal(6,2) NOT NULL,
  `descriptive_marks` decimal(6,2) NOT NULL,
  `total_marks` decimal(6,2) NOT NULL,
  `max_marks` decimal(6,2) NOT NULL,
  `status` varchar(10) COLLATE utf8mb4_unicode_ci NOT NULL,
  `published` tinyint(1) NOT NULL,
  `generated_at` datetime(6) NOT NULL,
  `attempt_id` bigint NOT NULL,
  `exam_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `attempt_id` (`attempt_id`),
  UNIQUE KEY `one_result_per_student_exam` (`user_id`,`exam_id`),
  KEY `results_exam_id_ac777c45_fk_exams_id` (`exam_id`),
  CONSTRAINT `results_attempt_id_58c6df4c_fk_exam_attempts_id` FOREIGN KEY (`attempt_id`) REFERENCES `exam_attempts` (`id`),
  CONSTRAINT `results_exam_id_ac777c45_fk_exams_id` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`),
  CONSTRAINT `results_user_id_1a41824a_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `result_descriptive_non_negative` CHECK ((`descriptive_marks` >= 0)),
  CONSTRAINT `result_objective_non_negative` CHECK ((`objective_marks` >= 0)),
  CONSTRAINT `result_status_valid` CHECK ((`status` in (_utf8mb4'PASS',_utf8mb4'FAIL'))),
  CONSTRAINT `result_total_non_negative` CHECK ((`total_marks` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `action` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `entity_id` bigint unsigned DEFAULT NULL,
  `at` datetime(6) NOT NULL,
  `detail` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `audit_user_at_idx` (`user_id`,`at`),
  KEY `audit_action_idx` (`action`),
  CONSTRAINT `audit_logs_user_id_752b0e2b_fk_users_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`),
  CONSTRAINT `audit_action_valid` CHECK ((`action` in (_utf8mb4'LOGIN',_utf8mb4'START',_utf8mb4'SAVE',_utf8mb4'SUBMIT',_utf8mb4'EVALUATE',_utf8mb4'PUBLISH'))),
  CONSTRAINT `audit_logs_chk_1` CHECK ((`entity_id` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

