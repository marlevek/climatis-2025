<?php
// Simulacao de rotas e alguns redirects publicos; NAO e WordPress real.
$uri = $_SERVER['REQUEST_URI'];
$path = parse_url($uri, PHP_URL_PATH);
$method = $_SERVER['REQUEST_METHOD'];
$host = $_SERVER['HTTP_HOST'];
$tls = ($_SERVER['HTTPS'] ?? '') === 'on';
if (getenv('LAB_TRUST_PROXY') === '1') { $tls = ($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https'; }
$scheme = $tls ? 'https' : 'http';
$query = $_SERVER['QUERY_STRING'] ?? '';
if (in_array($method, ['GET', 'HEAD'], true)) {
    if ($path === '/Blog/' && !isset($_GET['rest_route']) && ($host !== 'www.climatis.com.br' || !$tls)) {
        header('X-Redirect-By: Fixture-WordPress'); header('Location: https://www.climatis.com.br' . $uri, true, 302); exit;
    }
    if (in_array($path, ['/Blog/artigo-valido/', '/Blog/category/climatizacao/', '/Blog/feed/'], true) && $host !== 'www.climatis.com.br') {
        header('X-Redirect-By: Fixture-WordPress'); header('Location: ' . $scheme . '://www.climatis.com.br' . $uri, true, 302); exit;
    }
}
if ($path === '/Blog/wp-json/' || ($path === '/Blog/' && isset($_GET['rest_route']))) {
    require '/var/www/lab/api/echo.php'; exit;
}
if ($path === '/Blog/feed/') {
    header('Content-Type: application/rss+xml; charset=utf-8'); echo '<?xml version="1.0"?><rss version="2.0"><channel><title>Feed fixture</title></channel></rss>'; exit;
}
if (in_array($path, ['/Blog/', '/Blog/artigo-valido/', '/Blog/category/climatizacao/'], true)) {
    header('Content-Type: text/html; charset=utf-8'); echo '<html><head><link rel="canonical" href="https://www.climatis.com.br' . htmlspecialchars($path, ENT_QUOTES) . '"></head><body>blog-fixture:' . htmlspecialchars($path, ENT_QUOTES) . '</body></html>'; exit;
}
http_response_code(404); header('Content-Type: text/html; charset=utf-8'); echo 'blog-fixture-404';
