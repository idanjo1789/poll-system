CREATE DATABASE IF NOT EXISTS polls_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE polls_db;

CREATE TABLE IF NOT EXISTS polls (
  id INT AUTO_INCREMENT PRIMARY KEY,
  question VARCHAR(500) NOT NULL,
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_polls_is_active (is_active),
  INDEX idx_polls_created_at (created_at)
) ENGINE=InnoDB;