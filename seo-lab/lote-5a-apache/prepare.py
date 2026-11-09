"""Gera somente fixtures/configurações locais; nunca copia PHPs ou dados reais."""
from __future__ import annotations

import base64
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]
DOCUMENTS = ["SEO_LOTE_5A_CANONICAL_PROPOSTA.md", "SEO_LOTE_5A_IMPLEMENTACAO_PREPARADA.md", "SEO_LOTE_5A_B1_PROCEDIMENTO_OPERACIONAL.md"]


def write(name: str, content: str | bytes) -> None:
    target = LAB / name
    target.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        target.write_bytes(content)
    else:
        target.write_text(content, encoding="utf-8", newline="\n")


def original_manifest() -> dict[str, str]:
    result = {}
    for p in ROOT.rglob("*"):
        if not p.is_file() or ".git" in p.relative_to(ROOT).parts or LAB in p.parents:
            continue
        if p == ROOT / "SEO_LOTE_5A_LAB_APACHE_RESULTADOS.md":
            continue
        result[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result


def vhosts(mode: str, policy: str = "", parent: bool = False) -> str:
    common = '''ServerName www.climatis.com.br
ServerTokens Prod
ServerSignature Off
TraceEnable Off
LogLevel warn rewrite:trace2
ErrorLog /proc/self/fd/2
LogFormat "%h %m %U%q %>s %{Location}o" lab
CustomLog /proc/self/fd/1 lab
<Directory /var/www/lab>
    Options FollowSymLinks
    AllowOverride All
    Require all granted
    DirectoryIndex index.html index.php
</Directory>
<Directory /var/www/lab/api>
    php_flag enable_post_data_reading Off
</Directory>
'''
    if parent:
        common += '''<Directory /var/www>
    RewriteEngine On
    RewriteRule ^ - [E=LAB_PARENT:seen]
</Directory>
'''
    for port in [80, 443]:
        common += f"\n<VirtualHost *:{port}>\n    ServerName www.climatis.com.br:{port}\n    ServerAlias climatis.com.br\n    DocumentRoot /var/www/lab\n"
        if port == 443:
            common += "    SSLEngine On\n    SSLCertificateFile /opt/lab/certs/lab.crt\n    SSLCertificateKeyFile /opt/lab/certs/lab.key\n"
        if policy:
            common += policy + "\n"
        common += "</VirtualHost>\n"
    return common


def proxy_config(policy: str) -> str:
    result = "ServerName www.climatis.com.br\nServerTokens Prod\nTraceEnable Off\nLogLevel warn rewrite:trace2\nErrorLog /proc/self/fd/2\nProxyRequests Off\n"
    for port in [80, 443]:
        result += f"\n<VirtualHost *:{port}>\n    ServerName www.climatis.com.br:{port}\n    ServerAlias climatis.com.br\n"
        if port == 443:
            result += "    SSLEngine On\n    SSLCertificateFile /opt/lab/certs/lab.crt\n    SSLCertificateKeyFile /opt/lab/certs/lab.key\n"
        result += policy + "\n"
        result += f'''    ProxyPreserveHost On
    RequestHeader unset X-Forwarded-Proto
    RequestHeader set X-Forwarded-Proto "{'https' if port == 443 else 'http'}"
    ProxyPass / http://backend:80/
    ProxyPassReverse / http://backend:80/
</VirtualHost>
'''
    return result


def extra_experiments() -> None:
    """Experimentos adicionais sem alterar os cenários originais."""
    base = (LAB / "rules/baseline.htaccess").read_text(encoding="utf-8")
    conflict = '''RewriteEngine On
RewriteRule ^module-order$ https://www.climatis.com.br/rewrite-order.html [R=302,L]
Redirect 302 /module-order https://www.climatis.com.br/alias-order.html
'''
    write("rules/precedence-directory.htaccess", base + "\n" + conflict)
    write("apache/precedence-directory.conf", vhosts("precedence-directory"))
    reverse_conflict = '''Redirect 302 /module-order https://www.climatis.com.br/alias-order.html
RewriteEngine On
RewriteRule ^module-order$ https://www.climatis.com.br/rewrite-order.html [R=302,L]
'''
    write("rules/precedence-directory-verified.htaccess", base + "\n" + reverse_conflict)
    write("apache/precedence-directory-verified.conf", vhosts("precedence-directory-verified"))
    write("apache/precedence-vhost.conf", vhosts("precedence-vhost", conflict.replace("^module-order$", "^/module-order$")))
    write("fixtures/rewrite-order.html", "precedence-fixture:rewrite\n")
    write("fixtures/alias-order.html", "precedence-fixture:alias\n")
    vhost_policy = (LAB / "rules/candidate-vhost-302.conf").read_text(encoding="utf-8")
    blog_slash = '''# Correcao EXCLUSIVA DO LAB: evita DirectorySlash HTTP na origem atras do proxy.
RewriteEngine On
RewriteCond %{HTTP_HOST} ^(?:www\\.)?climatis\\.com\\.br(?::[0-9]+)?$ [NC]
RewriteCond %{REQUEST_METHOD} ^(?:GET|HEAD)$
RewriteCond %{IS_SUBREQ} =false
RewriteCond %{ENV:REDIRECT_STATUS} ^$
RewriteCond %{THE_REQUEST} \\s/Blog(?:\\?|\\s)
RewriteRule ^/Blog$ https://www.climatis.com.br/Blog/ [R=302,L,NE]

'''
    fixed = blog_slash + vhost_policy.replace("RewriteEngine On\n", "", 1)
    write("rules/candidate-edge-fixed-302.conf", fixed)
    write("apache/proxy-edge-fixed.conf", proxy_config(fixed))


def main() -> None:
    if (LAB / "results/original-manifest.json").exists():
        raise SystemExit("Laboratório já preparado; não sobrescrever o snapshot. Execute os scripts existentes.")
    for name in DOCUMENTS:
        if not (ROOT / name).is_file():
            raise SystemExit(f"Referência obrigatória ausente: {name}")
    manifest = original_manifest()
    write("results/original-manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    write("results/lab-metadata.json", json.dumps({"created_at": datetime.now(timezone.utc).isoformat(), "project": "climatis-seo5a-b2-" + uuid.uuid4().hex[:8], "sources": {name: manifest[name] for name in DOCUMENTS}, "production_requests": 0}, indent=2))
    baseline = (ROOT / ".htaccess").read_text(encoding="utf-8")
    assert "Redirect 301 /aparelhos-de-ar-condicionado-e-refrigeracao.html https://www.climatis.com.br/aparelhos-de-ar-condicionado.html" in baseline
    document = (ROOT / DOCUMENTS[1]).read_text(encoding="utf-8")
    diff = re.search(r"```diff\n--- a/\.htaccess\n.*?```", document, re.S).group()
    additions = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    candidate = "\n".join(additions).strip() + "\n"
    assert candidate.count("R=301") == 2
    candidate = candidate.replace("R=301", "R=302")
    write("rules/baseline.htaccess", baseline)
    write("rules/candidate-root.htaccess", baseline.rstrip() + "\n\n" + candidate)
    write("rules/candidate-source-302.conf", candidate)
    vhost_policy = candidate.replace("RewriteRule ^index\\.html$", "RewriteRule ^/index\\.html$")
    write("rules/candidate-vhost-302.conf", vhost_policy)
    for mode in ["baseline", "candidate-root", "candidate-vhost", "merge-baseline", "merge-candidate"]:
        write(f"apache/{mode}.conf", vhosts(mode, vhost_policy if mode == "candidate-vhost" else "", mode.startswith("merge-")))
    write("apache/proxy-naive.conf", proxy_config(""))
    write("apache/proxy-edge.conf", proxy_config(vhost_policy))

    def html(marker: str, canonical: str = "") -> str:
        tags = f'<link rel="canonical" href="{canonical}" /><meta property="og:url" content="{canonical}" />' if canonical else ""
        return f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">{tags}</head><body>Fixture isolada: {marker}</body></html>\n'

    write("fixtures/index.html", html("home", "https://www.climatis.com.br/index.html"))
    write("fixtures/index-candidate.html", html("home", "https://www.climatis.com.br/"))
    for slug in ["limpeza-de-ar-condicionado", "manutencao-de-ar-condicionado", "instalacao-de-ar-condicionado", "pmoc-para-ar-condicionado", "refrigeracao-comercial", "aparelhos-de-ar-condicionado"]:
        write(f"fixtures/{slug}.html", html(slug, f"https://www.climatis.com.br/{slug}.html"))
    write("fixtures/404.html", html("erro-404-personalizado"))
    write("fixtures/css/lab.css", "/* Fixture local */ body { color: #123456; }\n")
    write("fixtures/js/lab.js", "window.climatisFixture = true;\n")
    pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aMZkAAAAASUVORK5CYII=")
    write("fixtures/images/pixel.png", pixel)
    for name in ["arquivo teste.txt", "a#b.txt", "a+b.txt", "a&b.txt", "a%20b.txt"]:
        write("fixtures/encoded/" + name, "Fixture codificada: " + name + "\n")
    write("fixtures/Blog/assets/lab.css", "/* Fixture WordPress CSS */ body{color:blue}\n")
    write("fixtures/Blog/assets/lab.js", "window.blogFixture = true;\n")
    write("fixtures/Blog/assets/pixel.png", pixel)
    write("fixtures/Blog/cache/cached.html", html("cache-simulado"))
    child = '''# RECONSTRUCAO REPRESENTATIVA: arquivo remoto completo nao disponibilizado.
# Este bloco de cache e uma fixture, nao codigo do plugin W3 Total Cache.
RewriteEngine On
RewriteCond %{REQUEST_METHOD} ^(?:GET|HEAD)$
RewriteCond %{REQUEST_URI} ^/Blog/cache-fixture/$
RewriteRule ^cache-fixture/$ /Blog/cache/cached.html [L]

# Estrutura padrao WordPress conhecida, exclusiva do laboratorio.
RewriteBase /Blog/
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteRule ^index\\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /Blog/index.php [L]
'''
    write("fixtures/Blog/.htaccess", child)
    write("fixtures/internals/.htaccess", "RewriteEngine On\nRewriteRule ^route$ /api/echo.php [L]\n")
    echo = '''<?php
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
'''
    write("fixtures/api/echo.php", echo)
    write("fixtures/form.php", echo)
    write("fixtures/Blog/index.php", '''<?php
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
''')
    write("rules/PROVENIENCIA.md", "# Proveniência\n\nRaiz: cópia controlada do .htaccess local. Candidata: diff documentado, somente R=301 novo trocado por R=302. Blog: reconstrução do bloco padrão descrito nos relatórios, com cache sintético explicitamente identificado. O arquivo remoto completo/W3TC não foi fornecido, baixado ou validado. Nenhum PHP comercial, banco, configuração privada ou dado de cliente foi copiado.\n")
    extra_experiments()
    print(json.dumps({"prepared": True, "original_files": len(manifest), "lab": str(LAB)}))


if __name__ == "__main__":
    main()
