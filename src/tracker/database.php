<?php

include_once __DIR__ . '/utils.php';

class Database
{
    private static ?PDO $instance = null;

    public static function getConnection()
    {
        if (self::$instance === null) {
            $host = getenv('DB_HOST') ?: '127.0.0.1';
            $port = getenv('DB_PORT') ?: '3306';
            $dbname = getenv('DB_NAME') ?: 'ptorrent';
            $user = getenv('DB_USER') ?: 'root';
            $pass = getenv('DB_PASS') ?: '';

            $dsn = "mysql:host={$host};port={$port};dbname={$dbname};charset=utf8mb4";
            $options = [
                PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
                PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
                PDO::ATTR_EMULATE_PREPARES   => false,
            ];

            try {
                self::$instance = new PDO($dsn, $user, $pass, $options);
            } catch (PDOException $e) {
                echo(json_encode([
                    'status' => 'error',
                    'message' => 'cannot connect to database: ' . $e->getMessage()
                ], JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
                exit;
            }
        }
        return self::$instance;
    }
}
