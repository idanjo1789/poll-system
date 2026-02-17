CREATE DATABASE IF NOT EXISTS user_db;
USE user_db;

CREATE TABLE IF NOT EXISTS users (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  first_name    VARCHAR(100)     NOT NULL,
  last_name     VARCHAR(100)     NOT NULL,
  email         VARCHAR(255)     NOT NULL,
  age           INT              NULL,
  address       VARCHAR(255)     NULL,
  joining_date  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  is_registered TINYINT(1)       NOT NULL DEFAULT 0,
  created_at    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email),
  KEY idx_users_is_registered (is_registered),
  KEY idx_users_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
