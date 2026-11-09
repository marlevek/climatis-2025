<?php
// Fixture sem efeitos externos. Dados recebidos sao sempre sinteticos.
$raw = file_get_contents('php://input');
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin === 'https://client.seo5a.invalid') {
    header('Access-Control-Allow-Origin: ' . $origin);
    header('Access-Control-Allow-Methods: GET, HEAD, POST, PUT, PATCH, DELETE, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type, X-Lab-Test');
}
header('Content-Type: application/json; charset=utf-8');
$files = [];
foreach ($_FILES as $key => $file) {
    $files[$key] = ['name' => $file['name'], 'size' => $file['size'], 'error' => $file['error'], 'sha256' => is_uploaded_file($file['tmp_name']) ? hash_file('sha256', $file['tmp_name']) : null];
}
echo json_encode([
    'fixture' => 'echo', 'method' => $_SERVER['REQUEST_METHOD'],
    'body_bytes' => strlen($raw), 'body_sha256' => hash('sha256', $raw),
    'post' => $_POST, 'files' => $files, 'query' => $_SERVER['QUERY_STRING'] ?? '',
    'uri' => $_SERVER['REQUEST_URI'], 'https' => $_SERVER['HTTPS'] ?? 'off',
    'forwarded_proto' => $_SERVER['HTTP_X_FORWARDED_PROTO'] ?? null,
    'redirect_status' => $_SERVER['REDIRECT_STATUS'] ?? '',
    'parent_marker' => $_SERVER['LAB_PARENT'] ?? null,
    'trust_proxy_fixture_only' => getenv('LAB_TRUST_PROXY') === '1'
], JSON_UNESCAPED_SLASHES);
