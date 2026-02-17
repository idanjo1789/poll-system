CREATE DATABASE IF NOT EXISTS poll_db;
USE poll_db;
CREATE TABLE IF NOT EXISTS questions (
  question_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  title VARCHAR(255) NOT NULL,
  description TEXT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (question_id),
  KEY idx_questions_is_active_created_at (is_active, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLaLATE=utf8mb4_unicode_ci;
