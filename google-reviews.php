<?php
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: public, max-age=900');

$configFile = __DIR__ . '/google-reviews-config.php';
$config = [];

if (is_file($configFile)) {
    $loadedConfig = require $configFile;
    if (is_array($loadedConfig)) {
        $config = $loadedConfig;
    }
}

$apiKey = getenv('GOOGLE_PLACES_API_KEY') ?: ($config['api_key'] ?? '');
$placeId = getenv('GOOGLE_PLACE_ID') ?: ($config['place_id'] ?? '');
$cacheDir = __DIR__ . '/cache';
$cacheFile = $cacheDir . '/google-reviews.json';
$cacheTtl = 6 * 60 * 60;

function send_json(array $payload, int $status = 200): void
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function read_cache(string $cacheFile, int $cacheTtl): ?array
{
    if (!is_file($cacheFile) || (time() - filemtime($cacheFile)) > $cacheTtl) {
        return null;
    }

    $content = file_get_contents($cacheFile);
    if ($content === false) {
        return null;
    }

    $data = json_decode($content, true);
    return is_array($data) ? $data : null;
}

function write_cache(string $cacheDir, string $cacheFile, array $payload): void
{
    if (!is_dir($cacheDir)) {
        @mkdir($cacheDir, 0755, true);
    }

    if (is_dir($cacheDir) && is_writable($cacheDir)) {
        @file_put_contents($cacheFile, json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
    }
}

if ($apiKey === '' || $placeId === '') {
    $cached = read_cache($cacheFile, $cacheTtl);
    if ($cached !== null) {
        send_json($cached);
    }

    send_json([
        'configured' => false,
        'source' => 'fallback',
        'message' => 'Google Places API ainda não configurada.',
    ]);
}

if (!extension_loaded('openssl') && !extension_loaded('curl')) {
    send_json([
        'configured' => true,
        'source' => 'fallback',
        'message' => 'O PHP precisa da extensão OpenSSL ou cURL habilitada para consultar a Google Places API.',
    ], 502);
}

$cached = read_cache($cacheFile, $cacheTtl);
if ($cached !== null) {
    send_json($cached);
}

$url = 'https://places.googleapis.com/v1/places/' . rawurlencode($placeId)
    . '?languageCode=pt-BR&fields=displayName,rating,userRatingCount,reviews,googleMapsUri';

$context = stream_context_create([
    'http' => [
        'method' => 'GET',
        'timeout' => 6,
        'ignore_errors' => true,
        'header' => "X-Goog-Api-Key: {$apiKey}\r\n",
    ],
]);

$response = @file_get_contents($url, false, $context);
if ($response === false) {
    send_json([
        'configured' => true,
        'source' => 'fallback',
        'message' => 'Não foi possível consultar as avaliações do Google neste momento.',
    ], 502);
}

$data = json_decode($response, true);
if (!is_array($data)) {
    send_json([
        'configured' => true,
        'source' => 'fallback',
        'message' => 'Resposta inválida do Google Places.',
    ], 502);
}

$statusLine = $http_response_header[0] ?? '';
if (!str_contains($statusLine, ' 200 ')) {
    send_json([
        'configured' => true,
        'source' => 'fallback',
        'message' => $data['error']['message'] ?? 'Google Places retornou uma resposta inesperada.',
    ], 502);
}

$reviews = [];
foreach (($data['reviews'] ?? []) as $review) {
    if (!is_array($review)) {
        continue;
    }

    $text = $review['text']['text'] ?? '';
    $author = $review['authorAttribution']['displayName'] ?? 'Cliente Google';
    $rating = $review['rating'] ?? null;

    if ($text === '') {
        continue;
    }

    $reviews[] = [
        'author' => $author,
        'rating' => $rating,
        'text' => $text,
    ];
}

$payload = [
    'configured' => true,
    'source' => 'google',
    'name' => $data['displayName']['text'] ?? 'Climátis',
    'rating' => $data['rating'] ?? null,
    'total_reviews' => $data['userRatingCount'] ?? null,
    'google_maps_url' => $data['googleMapsUri'] ?? 'https://www.google.com/search?q=Clim%C3%A1tis+Curitiba+avalia%C3%A7%C3%B5es',
    'reviews' => array_slice($reviews, 0, 3),
    'updated_at' => date(DATE_ATOM),
];

write_cache($cacheDir, $cacheFile, $payload);
send_json($payload);
