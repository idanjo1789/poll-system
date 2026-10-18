CREATE DATABASE IF NOT EXISTS poll_db;

USE user_db;
DROP TABLE IF EXISTS votes;
DROP TABLE IF EXISTS answers;
DROP TABLE IF EXISTS questions;

USE poll_db;

SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('user_db', 'poll_db')
ORDER BY table_schema, table_name;