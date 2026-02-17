CREATE TABLE IF NOT EXISTS votes (
  vote_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  question_id BIGINT UNSIGNED NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  choice TINYINT UNSIGNED NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (vote_id),

  UNIQUE KEY uq_votes_question_user (question_id, user_id),
  KEY idx_votes_question_id (question_id),
  KEY idx_votes_user_id (user_id),

  CONSTRAINT fk_votes_question
    FOREIGN KEY (question_id) REFERENCES questions(question_id)
    ON DELETE CASCADE,

  CONSTRAINT chk_votes_choice
    CHECK (choice BETWEEN 1 AND 4)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
