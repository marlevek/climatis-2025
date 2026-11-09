"""Cliente restrito a loopback: nenhum URL lógico é resolvido no DNS público."""
from __future__ import annotations

import base64
import hashlib
import http.client
import json
import socket
import ssl
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit

LAB = Path(__file__).resolve().parent
HOSTS = ("climatis.com.br", "www.climatis.com.br")
BASES = tuple(f"{scheme}://{host}" for scheme in ("http", "https") for host in HOSTS)
CANONICAL = "https://www.climatis.com.br"
LEGACY = "/aparelhos-de-ar-condicionado-e-refrigeracao.html"
LEGACY_TARGET = "/aparelhos-de-ar-condicionado.html"
QUERY = "x=1%202&x=2%2B3&vazio=&mais=a+b&cod=a%26b%3Dc&marca=%23&interrogacao=%3F&duplo=%2520"
REDIRECTS = (301, 302, 303, 307, 308)


class LocalTLS(http.client.HTTPConnection):
    def __init__(self, logical_host: str, port: int, context: ssl.SSLContext):
        super().__init__("127.0.0.1", port, timeout=8)
        self.logical_host = logical_host
        self.context = context

    def connect(self) -> None:
        raw = socket.create_connection(("127.0.0.1", self.port), self.timeout)
        try:
            self.sock = self.context.wrap_socket(raw, server_hostname=self.logical_host)
        except BaseException:
            raw.close()
            raise


class Client:
    def __init__(self, ports: dict[str, int]):
        self.ports = ports
        self.context = ssl.create_default_context(cafile=str(LAB / "certs/lab.crt"))
        self.context.check_hostname = True
        self.context.verify_mode = ssl.CERT_REQUIRED

    def once(self, url: str, method: str = "GET", body: bytes = b"", headers: dict | None = None) -> dict:
        parts = urlsplit(url)
        if parts.hostname not in HOSTS or parts.scheme not in ("http", "https") or parts.username or parts.password:
            raise ValueError("URL lógico fora da lista permitida; nenhuma conexão foi realizada")
        if parts.port not in (None, 80 if parts.scheme == "http" else 443):
            raise ValueError("Porta lógica não permitida")
        target = parts.path or "/"
        if parts.query:
            target += "?" + parts.query
        port = self.ports[parts.scheme]
        conn = LocalTLS(parts.hostname, port, self.context) if parts.scheme == "https" else http.client.HTTPConnection("127.0.0.1", port, timeout=8)
        request_headers = {"Host": parts.hostname, "User-Agent": "Climatis-Isolated-Lab/2.0", "Connection": "close"}
        request_headers.update(headers or {})
        try:
            conn.request(method, target, body=body, headers=request_headers)
            response = conn.getresponse()
            payload = response.read(3_000_000)
            raw_headers = response.getheaders()
            header_map = {k.lower(): v for k, v in raw_headers}
            return {"url": url, "method": method, "status": response.status, "location": header_map.get("location"), "headers": header_map, "body": payload, "body_sha256": hashlib.sha256(payload).hexdigest()}
        finally:
            conn.close()

    def chain(self, url: str, method: str = "GET", body: bytes = b"", headers: dict | None = None, follow: bool = True) -> dict:
        hops, seen = [], set()
        current = url
        loop = False
        error = None
        try:
            for _ in range(7):
                if current in seen:
                    loop = True
                    break
                seen.add(current)
                response = self.once(current, method, body, headers)
                hops.append(response)
                if not follow or response["status"] not in REDIRECTS or not response["location"]:
                    break
                current = urljoin(current, response["location"])
            else:
                loop = True
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
        return {"hops": hops, "redirect_count": sum(h["status"] in REDIRECTS and bool(h["location"]) for h in hops), "loop": loop, "error": error, "final_url": hops[-1]["url"] if hops else None, "final_status": hops[-1]["status"] if hops else None}


@dataclass
class Case:
    name: str
    url: str
    method: str = "GET"
    body: bytes = b""
    headers: dict = field(default_factory=dict)
    expected_url: str | None = None
    expected_status: int = 200
    max_redirects: int = 1
    expected_redirects: int | None = None
    initial_status: int | None = None
    contains: bytes | None = None
    content_type: str | None = None
    echo_body: bool = False
    multipart: bool = False
    expected_loop: bool = False
    expectation: str = ""
    limitation: str = "Fixtures; não valida WordPress/HostGator reais"
    canonical: str | None = CANONICAL + "/"
    parent_expected: str | None = None
    transport: str = "normal"
    forwarded_expected: str | None = None


def expected_url(base: str, path: str) -> str:
    url = CANONICAL + path
    if path.startswith("/index.html"):
        url = CANONICAL + "/" + path[len("/index.html"):]
    elif path.startswith(LEGACY):
        url = CANONICAL + LEGACY_TARGET + path[len(LEGACY):]
    return url


def policy_cases() -> list[Case]:
    cases = []
    paths = {
        "/": (200, b"Fixture isolada: home", "text/html"),
        "/index.html": (200, b"Fixture isolada: home", "text/html"),
        "/Blog/": (200, b"blog-fixture:/Blog/", "text/html"),
        "/Blog": (200, b"blog-fixture:/Blog/", "text/html"),
        "/Blog/artigo-valido/": (200, b"blog-fixture:", "text/html"),
        "/Blog/category/climatizacao/": (200, b"blog-fixture:", "text/html"),
        "/Blog/feed/": (200, b"<rss", "application/rss+xml"),
        "/Blog/wp-json/": (200, b'"fixture":"echo"', "application/json"),
        "/Blog/?rest_route=%2Fwp%2Fv2%2Ftypes": (200, b'"fixture":"echo"', "application/json"),
        "/Blog/assets/lab.css": (200, b"WordPress CSS", "text/css"),
        "/Blog/assets/lab.js": (200, b"blogFixture", "javascript"),
        "/Blog/assets/pixel.png": (200, b"PNG", "image/png"),
        "/Blog/cache-fixture/": (200, b"cache-simulado", "text/html"),
        "/Blog/inexistente-fixture/": (404, b"blog-fixture-404", "text/html"),
        "/css/lab.css": (200, b"Fixture local", "text/css"),
        "/js/lab.js": (200, b"climatisFixture", "javascript"),
        "/images/pixel.png": (200, b"PNG", "image/png"),
        "/inexistente-fixture": (404, b"erro-404-personalizado", "text/html"),
        "/nested/inexistente-fixture": (404, b"erro-404-personalizado", "text/html"),
        "/404.html": (200, b"erro-404-personalizado", "text/html"),
        "/internals/route": (200, b'"fixture":"echo"', "application/json"),
        LEGACY + "?" + QUERY: (200, b"aparelhos-de-ar-condicionado", "text/html"),
    }
    for slug in ["limpeza-de-ar-condicionado", "manutencao-de-ar-condicionado", "instalacao-de-ar-condicionado", "pmoc-para-ar-condicionado", "refrigeracao-comercial"]:
        paths[f"/{slug}.html"] = (200, slug.encode(), "text/html")
    for base in BASES:
        for path, (status, marker, mime) in paths.items():
            for method in ("GET", "HEAD"):
                final = expected_url(base, path)
                if path == "/Blog":
                    final += "/"
                redirects = None if path == "/Blog" else int(base + path != final)
                cases.append(Case(f"rota:{path}", base + path, method, expected_url=final, expected_status=status, max_redirects=2 if path == "/Blog" else 1, expected_redirects=redirects, initial_status=301 if path.startswith(LEGACY) else (302 if redirects else None), contains=marker, content_type=mime))
        for home_path in ("/?" + QUERY, "/index.html?" + QUERY):
            for method in ("GET", "HEAD"):
                final = CANONICAL + "/?" + QUERY
                cases.append(Case("home-query", base + home_path, method, expected_url=final, expected_redirects=int(base + home_path != final), contains=b'canonical" href="https://www.climatis.com.br/"'))
        for path, code in [("/encoded/arquivo%20teste.txt", 200), ("/encoded/a%23b.txt", 200), ("/encoded/a%2Bb.txt", 200), ("/encoded/a%26b.txt", 200), ("/encoded/a%2520b.txt", 200), ("/encoded/a%3Fb.txt", 404)]:
            for method in ("GET", "HEAD"):
                cases.append(Case("caminho-codificado", base + path, method, expected_url=CANONICAL + path, expected_status=code, expected_redirects=int(base != CANONICAL)))
        for method in ("GET", "HEAD"):
            path = "/api/echo.php?" + QUERY
            cases.append(Case("query-literal", base + path, method, expected_url=CANONICAL + path, expected_redirects=int(base != CANONICAL), content_type="application/json", echo_body=method == "GET"))
    # O Host de entrada não é utilizado para construir destinos arbitrários.
    cases.append(Case("host-desconhecido", CANONICAL + "/", headers={"Host": "host.seo5a.invalid"}, expected_url=CANONICAL + "/", expected_redirects=0, contains=b"home"))
    # Header do visitante não pode substituir HTTPS real no cenário direto.
    cases.append(Case("xfp-forjado-http", "http://www.climatis.com.br/api/echo.php", headers={"X-Forwarded-Proto": "https"}, expected_url=CANONICAL + "/api/echo.php", expected_redirects=1, initial_status=302, content_type="application/json"))
    return cases


def method_cases() -> list[Case]:
    result = []
    boundary = "ClimatisLabBoundary20261109"
    multipart = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"nome\"\r\n\r\nFixture local\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"arquivo\"; filename=\"fixture.txt\"\r\nContent-Type: text/plain\r\n\r\nfixture-upload\r\n--{boundary}--\r\n").encode()
    for base in BASES:
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            body = b"nome=Fixture+local&x=1&x=2%2B3" if method != "OPTIONS" else b""
            headers = {"Content-Type": "application/x-www-form-urlencoded"}
            if method == "OPTIONS":
                headers.update({"Origin": "https://client.seo5a.invalid", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type,X-Lab-Test"})
            url = base + "/api/echo.php?" + QUERY
            result.append(Case("metodo-corpo", url, method, body, headers, expected_url=url, expected_redirects=0, echo_body=True, content_type="application/json"))
        for path in ("/api/echo.php", "/form.php"):
            url = base + path
            result.append(Case("post-multipart", url, "POST", multipart, {"Content-Type": f"multipart/form-data; boundary={boundary}"}, expected_url=url, expected_redirects=0, echo_body=path.startswith("/api/"), multipart=path == "/form.php", content_type="application/json"))
        # O front controller filho também não pode gerar normalização de métodos com corpo.
        url = base + "/Blog/wp-json/"
        result.append(Case("post-rest-blog", url, "POST", b'{"fixture":true}', {"Content-Type": "application/json"}, expected_url=url, expected_redirects=0, echo_body=True, content_type="application/json"))
    return result


def evaluate(case: Case, observed: dict) -> tuple[bool, list[str]]:
    errors = []
    if case.transport != "normal":
        return observed.get("negative_passed", False), [] if observed.get("negative_passed") else ["Falha no controle negativo de transporte"]
    hops = observed["hops"]
    if observed["error"]:
        errors.append(observed["error"])
    if case.expected_loop:
        if not observed["loop"]:
            errors.append("Loop esperado não foi demonstrado")
        if not hops or hops[0]["status"] != 302:
            errors.append("Contraexemplo não começou com o 302 novo esperado")
        return not errors, errors
    if observed["loop"]:
        errors.append("Loop detectado")
    if not hops:
        return False, errors + ["Nenhuma resposta HTTP"]
    final = hops[-1]
    if observed["final_status"] != case.expected_status:
        errors.append(f"Status final {observed['final_status']} != {case.expected_status}")
    if case.expected_url is not None and observed["final_url"] != case.expected_url:
        errors.append("URL final diferente do destino literal esperado")
    if observed["redirect_count"] > case.max_redirects:
        errors.append("Número de redirecionamentos excede o limite")
    if case.expected_redirects is not None and observed["redirect_count"] != case.expected_redirects:
        errors.append("Quantidade de redirecionamentos diferente da esperada")
    if case.initial_status and hops[0]["status"] != case.initial_status:
        errors.append(f"Status inicial {hops[0]['status']} != {case.initial_status}")
    if case.content_type and case.content_type not in final["headers"].get("content-type", ""):
        errors.append("Content-Type incorreto")
    if case.method == "HEAD" and final["body"]:
        errors.append("HEAD retornou corpo")
    if case.method != "HEAD" and case.contains and case.contains not in final["body"]:
        errors.append("Conteúdo da fixture não preservado")
    if case.method not in ("GET", "HEAD"):
        if any(h["status"] in REDIRECTS for h in hops):
            errors.append("Método com corpo/preflight recebeu redirecionamento")
    if case.echo_body or case.multipart:
        try:
            data = json.loads(final["body"])
            if data["method"] != case.method:
                errors.append("Método alterado")
            if case.echo_body and (data["body_bytes"] != len(case.body) or data["body_sha256"] != hashlib.sha256(case.body).hexdigest()):
                errors.append("Corpo alterado ou descartado")
            if data["query"] != urlsplit(case.url).query:
                errors.append("Query literal alterada")
            if case.parent_expected is not None:
                expected_parent = None if case.parent_expected == "absent" else case.parent_expected
                if data["parent_marker"] != expected_parent:
                    errors.append("Marcador de mesclagem diferente do esperado")
            if case.forwarded_expected is not None:
                if data["forwarded_proto"] != case.forwarded_expected or data["https"] == "on" or not data["trust_proxy_fixture_only"]:
                    errors.append("Proxy não sobrescreveu o header do cliente ou origem não demonstrou HTTP")
            if case.multipart:
                file = data["files"].get("arquivo", {})
                if data["post"].get("nome") != "Fixture local" or file.get("sha256") != hashlib.sha256(b"fixture-upload").hexdigest() or file.get("error") != 0:
                    errors.append("Multipart/campo/upload sintético alterado")
            if case.method == "OPTIONS" and final["headers"].get("access-control-allow-origin") != "https://client.seo5a.invalid":
                errors.append("Preflight sem CORS esperado")
        except (ValueError, KeyError, TypeError, AttributeError):
            errors.append("Fixture JSON inválida")
    # Metadados da home são conferidos apenas quando o corpo foi solicitado.
    if urlsplit(case.url).path in ("/", "/index.html") and case.method == "GET" and case.canonical:
        if f'rel="canonical" href="{case.canonical}"'.encode() not in final["body"] or f'property="og:url" content="{case.canonical}"'.encode() not in final["body"]:
            errors.append("Metadados da home ainda divergentes")
    return not errors, errors


def run_cases(client: Client, scenario: str, cases: list[Case], path: Path, policy: str = "candidate") -> list[dict]:
    rows = []
    for number, case in enumerate(cases, 1):
        if case.transport == "normal":
            observed = client.chain(case.url, case.method, case.body, case.headers)
        else:
            observed = {"hops": [], "redirect_count": 0, "loop": False, "error": None, "final_url": None, "final_status": None, "negative_passed": False}
            try:
                if case.transport == "blocked-host":
                    client.once(case.url)
                else:
                    context = ssl.create_default_context() if case.transport == "untrusted-ca" else client.context
                    logical = "invalid.seo5a.invalid" if case.transport == "wrong-sni" else "www.climatis.com.br"
                    conn = LocalTLS(logical, client.ports["https"], context)
                    try:
                        conn.connect()
                    finally:
                        conn.close()
            except (ssl.SSLCertVerificationError, ValueError) as exc:
                observed["negative_passed"] = isinstance(exc, ValueError) if case.transport == "blocked-host" else isinstance(exc, ssl.SSLCertVerificationError)
                observed["expected_exception_observed"] = type(exc).__name__
        passed, errors = evaluate(case, observed)
        first = observed["hops"][0] if observed["hops"] else {}
        for h in observed["hops"]:
            h["body_base64"] = base64.b64encode(h.pop("body")).decode()
        row = {"case": f"{scenario}-{number:04d}", "test": case.name, "scenario": scenario, "policy": policy, "method": case.method, "original_url": case.url, "initial_status": first.get("status"), "location": first.get("location"), "redirect_count": observed["redirect_count"], "final_url": observed["final_url"], "final_status": observed["final_status"], "expected": case.expectation or {"url": case.expected_url, "status": case.expected_status, "redirects": case.expected_redirects, "max_redirects": case.max_redirects, "loop": case.expected_loop}, "observed": observed, "passed": passed, "errors": errors, "limitations": case.limitation, "executed_at": datetime.now(timezone.utc).isoformat()}
        rows.append(row)
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return rows
