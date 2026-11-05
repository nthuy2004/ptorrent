<?php
/**
 * dky new file vaof tracker
 * Method: POST
 * Endpoint: /register.php
 */

require_once __DIR__ . '/db.php';

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    jsonResponse(405, ['status' => 'error', 'message' => 'Allow only POST']);
}

$data = getRequestData();

$fileId = trim($data['file_id'] ?? '');
$fileName = trim($data['file_name'] ?? '');
$fileSize = filter_var($data['file_size'] ?? null, FILTER_VALIDATE_INT);
$pieceSize = filter_var($data['piece_size'] ?? null, FILTER_VALIDATE_INT);
$totalPieces = filter_var($data['total_pieces'] ?? null, FILTER_VALIDATE_INT);
$fileHash = trim($data['file_hash'] ?? '');

if (empty($fileId) || empty($fileName) || $fileSize === false || $pieceSize === false || $totalPieces === false || empty($fileHash)) {
    jsonResponse(400, [
        'status' => 'error',
        'message' => 'missing field (file_id, file_name, file_size, piece_size, total_pieces, file_hash)'
    ]);
}

try {
    $db = Database::getConnection();

    $stmt = $db->prepare("
        INSERT INTO files (file_id, file_name, file_size, piece_size, total_pieces, file_hash)
        VALUES (:file_id, :file_name, :file_size, :piece_size, :total_pieces, :file_hash)
        ON DUPLICATE KEY UPDATE 
            file_name = VALUES(file_name),
            file_size = VALUES(file_size),
            piece_size = VALUES(piece_size),
            total_pieces = VALUES(total_pieces),
            file_hash = VALUES(file_hash)
    ");

    $stmt->execute([
        ':file_id' => $fileId,
        ':file_name' => $fileName,
        ':file_size' => $fileSize,
        ':piece_size' => $pieceSize,
        ':total_pieces' => $totalPieces,
        ':file_hash' => $fileHash
    ]);

    jsonResponse(200, [
        'status' => 'success',
        'message' => 'OK',
        'file_id' => $fileId
    ]);

} catch (Exception $e) {
    jsonResponse(500, [
        'status' => 'error',
        'message' => 'server error: ' . $e->getMessage()
    ]);
}
