-- Run this to create the database & tables (or let SQLAlchemy create automatically)
CREATE DATABASE IF NOT EXISTS study_buddy CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE study_buddy;

CREATE TABLE IF NOT EXISTS flashcard_sets (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  source_text MEDIUMTEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS flashcards (
  id INT AUTO_INCREMENT PRIMARY KEY,
  set_id INT NOT NULL,
  question TEXT NOT NULL,
  answer TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (set_id) REFERENCES flashcard_sets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
