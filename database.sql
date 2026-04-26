-- ============================================================
--  AURA — MySQL Database Schema
--  Run this file to set up the MySQL version of the database.
--  (The default project uses SQLite via models/database.py)
-- ============================================================

CREATE DATABASE IF NOT EXISTS aura_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE aura_db;

-- ── Users table ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          INT          NOT NULL AUTO_INCREMENT,
    name        VARCHAR(100) NOT NULL,
    email       VARCHAR(150) NOT NULL UNIQUE,
    password    VARCHAR(64)  NOT NULL,   -- SHA-256 hex (64 chars)
    salt        VARCHAR(32)  NOT NULL,   -- hex salt (32 chars)
    created_at  DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Chat history table ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_history (
    id          INT          NOT NULL AUTO_INCREMENT,
    user_id     INT          NOT NULL,
    role        ENUM('user','bot') NOT NULL,
    message     TEXT         NOT NULL,
    intent      VARCHAR(50),
    confidence  FLOAT,
    timestamp   DATETIME     DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    INDEX idx_user_time (user_id, timestamp),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ── Sample data (optional) ───────────────────────────────────────────────────
-- INSERT INTO users (name, email, password, salt)
-- VALUES ('Test Student', 'test@college.edu', '<hashed>', '<salt>');
