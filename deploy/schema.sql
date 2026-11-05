CREATE DATABASE IF NOT EXISTS ptorrent CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ptorrent;

CREATE TABLE IF NOT EXISTS files (
    file_id VARCHAR(64) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_size BIGINT NOT NULL,
    piece_size INT NOT NULL,
    total_pieces INT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (file_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS peers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_id VARCHAR(64) NOT NULL,
    peer_id VARCHAR(64) NOT NULL,
    ip VARCHAR(45) NOT NULL,
    port INT NOT NULL,
    uploaded BIGINT DEFAULT 0,
    downloaded BIGINT DEFAULT 0,
    bytes_left BIGINT DEFAULT 0,
    bitfield JSON DEFAULT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_file_peer (file_id, peer_id),
    INDEX idx_file_id (file_id),
    INDEX idx_updated_at (updated_at),
    CONSTRAINT fk_peers_files FOREIGN KEY (file_id) REFERENCES files (file_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
