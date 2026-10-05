<?php

/**
 * announce api
 * Method: GET, POST
 * Endpoint: /announce.php
 */

require_once __DIR__ . '/db.php';

$data = getRequestData();

$fileId = trim($data['file_id'] ?? '');
$peerId = trim($data['peer_id'] ?? '');
$port = filter_var($data['port'] ?? null, FILTER_VALIDATE_INT);
$uploaded = filter_var($data['uploaded'] ?? 0, FILTER_VALIDATE_INT);
$downloaded = filter_var($data['downloaded'] ?? 0, FILTER_VALIDATE_INT);
$bytesLeft = filter_var($data['bytes_left'] ?? null, FILTER_VALIDATE_INT);
$event = strtolower(trim($data['event'] ?? ''));

$ip = trim($data['ip'] ?? '');
if (empty($ip)) {
    $ip = $_SERVER['REMOTE_ADDR'] ?? '127.0.0.1';
    if ($ip === '::1') {
        $ip = '127.0.0.1';
    }
}

$bitfield = $data['bitfield'] ?? null;
if (is_array($bitfield)) {
    $bitfieldJson = json_encode($bitfield);
} else {
    $bitfieldJson = is_string($bitfield) ? $bitfield : null;
}

if (empty($fileId) || empty($peerId) || $port === false) {
    jsonResponse(400, [
        'status' => 'error',
        'message' => 'missing required fields (file_id, peer_id, port)'
    ]);
}

try {
    $db = Database::getConnection();
    $db->query("DELETE FROM peers WHERE updated_at < NOW() - INTERVAL 45 SECOND");

    if ($event === 'stopped') {
        // peeer exit
        $stmt = $db->prepare("DELETE FROM peers WHERE file_id = :file_id AND peer_id = :peer_id");
        $stmt->execute([':file_id' => $fileId, ':peer_id' => $peerId]);

        jsonResponse(200, [
            'status' => 'success',
            'message' => 'exited'
        ]);
    }

    if ($bytesLeft === false || $bytesLeft === null) {
        $bytesLeft = 0;
    }

    if ($event === 'completed') {
        $bytesLeft = 0;
    }

    $stmt = $db->prepare("
        INSERT INTO peers (file_id, peer_id, ip, port, uploaded, downloaded, bytes_left, bitfield, updated_at)
        VALUES (:file_id, :peer_id, :ip, :port, :uploaded, :downloaded, :bytes_left, :bitfield, NOW())
        ON DUPLICATE KEY UPDATE
            ip = VALUES(ip),
            port = VALUES(port),
            uploaded = VALUES(uploaded),
            downloaded = VALUES(downloaded),
            bytes_left = VALUES(bytes_left),
            bitfield = COALESCE(VALUES(bitfield), bitfield),
            updated_at = NOW()
    ");

    $stmt->execute([
        ':file_id' => $fileId,
        ':peer_id' => $peerId,
        ':ip' => $ip,
        ':port' => $port,
        ':uploaded' => $uploaded,
        ':downloaded' => $downloaded,
        ':bytes_left' => $bytesLeft,
        ':bitfield' => $bitfieldJson
    ]);

    // ana count
    $stmtCount = $db->prepare("
        SELECT 
            SUM(CASE WHEN bytes_left = 0 THEN 1 ELSE 0 END) AS complete_count,
            SUM(CASE WHEN bytes_left > 0 THEN 1 ELSE 0 END) AS incomplete_count
        FROM peers 
        WHERE file_id = :file_id
    ");
    $stmtCount->execute([':file_id' => $fileId]);
    $counts = $stmtCount->fetch();

    $complete = (int)($counts['complete_count'] ?? 0);
    $incomplete = (int)($counts['incomplete_count'] ?? 0);

    // get another peeers
    $stmtPeers = $db->prepare("
        SELECT peer_id, ip, port, bytes_left, bitfield
        FROM peers
        WHERE file_id = :file_id AND peer_id != :peer_id
        ORDER BY updated_at DESC
        LIMIT 50
    ");
    $stmtPeers->execute([':file_id' => $fileId, ':peer_id' => $peerId]);
    $rawPeers = $stmtPeers->fetchAll();

    $peersList = [];
    foreach ($rawPeers as $p) {
        $bitfieldParsed = null;
        if (!empty($p['bitfield'])) {
            $bitfieldParsed = json_decode($p['bitfield'], true);
        }

        $peersList[] = [
            'peer_id' => $p['peer_id'],
            'ip' => $p['ip'],
            'port' => (int)$p['port'],
            'bytes_left' => (int)$p['bytes_left'],
            'bitfield' => $bitfieldParsed
        ];
    }

    // resp
    jsonResponse(200, [
        'interval' => 15,
        'complete' => $complete,
        'incomplete' => $incomplete,
        'peers' => $peersList
    ]);
} catch (Exception $e) {
    jsonResponse(500, [
        'status' => 'error',
        'message' => 'server error: ' . $e->getMessage()
    ]);
}
