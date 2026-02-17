CREATE DATABASE IF NOT EXISTS poll_db;
USE poll_db;

CREATE TABLE IF NOT EXISTS answers (
  answer_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  question_id BIGINT UNSIGNED NOT NULL,
  choice TINYINT UNSIGNED NOT NULL,
  text VARCHAR(255) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (answer_id),

  UNIQUE KEY uq_answers_question_choice (question_id, choice),
  KEY idx_answers_question_id (question_id),

  CONSTRAINT fk_answers_question
    FOREIGN KEY (question_id)
    REFERENCES questions(question_id)
    ON DELETE CASCADE
    ON UPDATE CASCADE,

  CONSTRAINT chk_answers_choice
    CHECK (choice BETWEEN 1 AND 4)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
  