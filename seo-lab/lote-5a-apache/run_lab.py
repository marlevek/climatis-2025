"""Executa apenas recursos Docker deste projeto e conexões locais controladas."""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from tests import BASES, CANONICAL, LAB, LEGACY, LEGACY_TARGET, QUERY, Case, method_cases, policy_cases

ROOT = LAB.parents[1]
RESULTS = LAB / "results"
IMAGE = "climatis-seo5a-apache-lab:20261109"
BASE_IMAGE = "php@sha256:884f64b47174de2c0e813270fe7b24a18605729fcebe201302d98c38805530d0"
CLIENT_IMAGE = "python@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1"
SCENARIOS = ("baseline", "candidate-root", "candidate-vhost", "merge-baseline", "merge-candidate", "precedence-directory", "precedence-directory-verified", "precedence-vhost", "proxy-root-naive", "proxy-vhost-naive", "proxy-edge", "proxy-edge-fixed", "proxy-edge-fixed-query", "proxy-edge-fixed-headers")


def command(args: list[str], env: dict | None = None, timeout: int = 120, check: bool = True) -> subprocess.CompletedProcess:
    process = subprocess.run(args, cwd=LAB, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if check and process.returncode:
        raise RuntimeError(f"Comando falhou ({process.returncode}): {' '.join(args)}\n{process.stdout}\n{process.stderr}")
    return process


def compose(project: str, args: list[str], settings: dict | None = None, check: bool = True) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update({"LAB_MODE": "baseline", "BACKEND_MODE": "candidate-root", "EDGE_MODE": "proxy-naive", "LAB_CONTENT_CANONICAL": "0"})
    env.update(settings or {})
    return command(["docker", "compose", "-p", project, "-f", str(LAB / "compose.yaml"), *args], env=env, check=check)


def save_json(name: str, value) -> None:
    (RESULTS / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def baseline_cases() -> list[Case]:
    result = []
    statuses = [("/", 200), ("/index.html", 200), ("/limpeza-de-ar-condicionado.html", 200), ("/manutencao-de-ar-condicionado.html", 200), ("/instalacao-de-ar-condicionado.html", 200), ("/pmoc-para-ar-condicionado.html", 200), ("/refrigeracao-comercial.html", 200), ("/css/lab.css", 200), ("/js/lab.js", 200), ("/images/pixel.png", 200), ("/Blog/assets/lab.css", 200), ("/Blog/assets/lab.js", 200), ("/Blog/assets/pixel.png", 200), ("/Blog/cache-fixture/", 200), ("/Blog/wp-json/", 200), ("/Blog/?rest_route=%2Fwp%2Fv2%2Ftypes", 200), ("/inexistente-fixture", 404), ("/Blog/inexistente-fixture/", 404), ("/404.html", 200), ("/encoded/arquivo%20teste.txt", 200), ("/encoded/a%23b.txt", 200), ("/encoded/a%2Bb.txt", 200), ("/encoded/a%26b.txt", 200), ("/encoded/a%2520b.txt", 200), ("/encoded/a%3Fb.txt", 404)]
    for base in BASES:
        for path, status in statuses:
            for method in ("GET", "HEAD"):
                result.append(Case("baseline-rota", base + path, method, expected_url=base + path, expected_status=status, expected_redirects=0, canonical=CANONICAL + "/index.html"))
        for method in ("GET", "HEAD"):
            result.append(Case("baseline-blog-home", base + "/Blog/", method, expected_url=CANONICAL + "/Blog/", expected_redirects=int(base != CANONICAL)))
            result.append(Case("baseline-blog-sem-barra", base + "/Blog", method, expected_url=CANONICAL + "/Blog/", expected_redirects=1 + int(base != CANONICAL), max_redirects=2))
            for path in ("/Blog/artigo-valido/", "/Blog/category/climatizacao/", "/Blog/feed/"):
                scheme = base.split(":")[0]
                target = scheme + "://www.climatis.com.br" + path
                result.append(Case("baseline-blog-aplicacao", base + path, method, expected_url=target, expected_redirects=int(base + path != target)))
            path = LEGACY + "?" + QUERY
            result.append(Case("baseline-lote1", base + path, method, expected_url=CANONICAL + LEGACY_TARGET + "?" + QUERY, expected_redirects=1, initial_status=301))
    return result + method_cases()


def inspect_isolation(project: str, scenario: str) -> dict:
    ids = compose(project, ["ps", "-q"]).stdout.split()
    containers = json.loads(command(["docker", "inspect", *ids]).stdout)
    evidence = []
    for container in containers:
        assert not container["HostConfig"].get("PortBindings"), "Nenhuma porta deve ser publicada nesta topologia"
        for bindings in (container["HostConfig"].get("PortBindings") or {}).values():
            for binding in bindings or []:
                assert binding["HostIp"] == "127.0.0.1", binding
        for mount in container.get("Mounts", []):
            assert mount["Destination"] == "/opt/lab/certs" and mount["RW"] is False, mount
        evidence.append({"name": container["Name"], "image": container["Image"], "ports": container["HostConfig"].get("PortBindings"), "mounts": container.get("Mounts", [])})
    nets = command(["docker", "network", "ls", "-q", "--filter", "label=com.docker.compose.project=" + project]).stdout.split()
    networks = json.loads(command(["docker", "network", "inspect", *nets]).stdout)
    assert networks and all(n["Internal"] for n in networks)
    value = {"containers": evidence, "networks": [{"name": n["Name"], "internal": n["Internal"], "ipam": n["IPAM"]} for n in networks]}
    save_json(scenario + "-isolation.json", value)
    return value


def run_batch(project: str, service: str, scenario: str, cases: list[Case]) -> list[dict]:
    serialized = []
    for case in cases:
        value = asdict(case)
        value["body"] = base64.b64encode(value["body"]).decode()
        value["contains"] = base64.b64encode(value["contains"]).decode() if value["contains"] is not None else None
        serialized.append(value)
    save_json(scenario + "-input.json", serialized)
    container_id = compose(project, ["ps", "-q", service]).stdout.strip()
    assert container_id and "\n" not in container_id
    response = command(["docker", "run", "--rm", "--pull=never", "--network", "container:" + container_id, "--mount", f"type=bind,source={LAB},target=/lab,readonly", "--mount", f"type=bind,source={RESULTS},target=/lab/results", CLIENT_IMAGE, "python", "/lab/batch.py", scenario], timeout=300)
    (RESULTS / (scenario + "-client.log")).write_text(response.stdout + response.stderr, encoding="utf-8")
    return json.loads((RESULTS / (scenario + ".json")).read_text(encoding="utf-8"))


def record_logs(project: str, scenario: str) -> None:
    result = compose(project, ["logs", "--no-color"], check=False)
    (RESULTS / (scenario + "-apache.log")).write_text(result.stdout + result.stderr, encoding="utf-8")


def versions(project: str) -> dict:
    result = {"docker_version": json.loads(command(["docker", "version", "--format", "{{json .}}"]).stdout), "compose_version": command(["docker", "compose", "version"]).stdout.strip(), "python": sys.version, "base_image": BASE_IMAGE}
    for name, args in {"apache": ["apache2", "-v"], "php": ["php", "-v"], "openssl": ["openssl", "version"], "modules": ["apache2ctl", "-M"], "syntax": ["apache2ctl", "-t"]}.items():
        response = compose(project, ["exec", "-T", "direct", *args])
        result[name] = response.stdout + response.stderr
    result["image"] = json.loads(command(["docker", "image", "inspect", IMAGE]).stdout)[0]["Id"]
    save_json("versions.json", result)
    return result


def run_direct(project: str, mode: str, cases: list[Case]) -> list[dict]:
    print("Cenário direto: " + mode, flush=True)
    settings = {"LAB_MODE": mode}
    compose(project, ["--profile", "direct", "up", "-d", "--no-build", "--force-recreate", "direct"], settings)
    try:
        inspect_isolation(project, mode)
        if mode == "baseline":
            versions(project)
        rows = run_batch(project, "direct", mode, cases)
        print(f"{mode}: {sum(r['passed'] for r in rows)}/{len(rows)} aprovados", flush=True)
        return rows
    finally:
        record_logs(project, mode)
        compose(project, ["--profile", "direct", "stop", "direct"])


def run_proxy(project: str, name: str, backend: str, edge: str, cases: list[Case]) -> list[dict]:
    print("Cenário proxy: " + name, flush=True)
    settings = {"BACKEND_MODE": backend, "EDGE_MODE": edge, "LAB_CONTENT_CANONICAL": "1" if edge in ("proxy-edge", "proxy-edge-fixed") else "0"}
    compose(project, ["--profile", "proxy", "up", "-d", "--no-build", "--force-recreate", "backend", "edge"], settings)
    try:
        inspect_isolation(project, name)
        rows = run_batch(project, "edge", name, cases)
        print(f"{name}: {sum(r['passed'] for r in rows)}/{len(rows)} diagnósticos aprovados", flush=True)
        return rows
    finally:
        record_logs(project, name)
        compose(project, ["--profile", "proxy", "stop", "edge", "backend"])


def check_originals() -> dict:
    manifest = json.loads((RESULTS / "original-manifest.json").read_text(encoding="utf-8"))
    changed = [p for p, digest in manifest.items() if not (ROOT / p).is_file() or hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest]
    git = command(["git", "-C", str(ROOT), "-c", "core.excludesFile=", "status", "--short", "--untracked-files=all"]).stdout
    value = {"original_count": len(manifest), "changed_originals": changed, "git_status": git}
    save_json("preservation.json", value)
    assert not changed, changed
    return value


def report(rows: list[dict], error: str | None, cleanup: dict) -> None:
    groups = {}
    for r in rows:
        groups.setdefault(r["scenario"], []).append(r)
    summary = {name: {"executed": len(items), "passed": sum(i["passed"] for i in items), "failed": sum(not i["passed"] for i in items), "failed_groups": dict(Counter(i["test"] for i in items if not i["passed"]))} for name, items in groups.items()}
    save_json("summary.json", {"scenarios": summary, "error": error, "cleanup": cleanup, "executed_cases": len(rows)})
    fields = ["case", "scenario", "method", "original_url", "initial_status", "location", "redirect_count", "final_url", "final_status", "expected", "observed", "passed", "errors", "limitations"]
    with (RESULTS / "matrix.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            values = {k: json.dumps(row[k], ensure_ascii=False) if isinstance(row[k], (dict, list)) else row[k] for k in fields if k != "observed"}
            values["observed"] = json.dumps({"chain": [{k: hop[k] for k in ("url", "status", "location")} for hop in row["observed"]["hops"]], "loop": row["observed"]["loop"], "error": row["observed"]["error"], "negative_passed": row["observed"].get("negative_passed")}, ensure_ascii=False)
            writer.writerow(values)
    print(json.dumps({"executed": len(rows), "summary": summary, "error": error, "cleanup": cleanup}, ensure_ascii=False), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true", help="Construir a imagem a partir do contexto exclusivo do laboratório")
    parser.add_argument("--only", help="Executar apenas cenários nomeados, separados por vírgula, preservando outros resultados já obtidos")
    args = parser.parse_args()
    if not (RESULTS / "lab-metadata.json").exists():
        raise SystemExit("Execute prepare.py primeiro")
    if os.environ.get("DOCKER_HOST") and not os.environ["DOCKER_HOST"].startswith(("unix://", "npipe://")):
        raise SystemExit("Docker remoto não autorizado")
    metadata = json.loads((RESULTS / "lab-metadata.json").read_text(encoding="utf-8"))
    project = metadata["project"]
    assert project.startswith("climatis-seo5a-b2-")
    selected = set(args.only.split(",")) if args.only else set(SCENARIOS)
    if not selected.issubset(SCENARIOS):
        raise SystemExit("Cenário desconhecido")
    command(["docker", "version", "--format", "{{.Server.Version}}"])
    if args.build:
        command(["docker", "build", "--pull=false", "--network=none", "-t", IMAGE, "."], timeout=300)
    if not (LAB / "certs/lab.crt").exists():
        certs = LAB / "certs"
        certs.mkdir(exist_ok=True)
        command(["docker", "run", "--rm", "--network", "none", "--mount", f"type=bind,source={certs},target=/certs", BASE_IMAGE, "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "7", "-keyout", "/certs/lab.key", "-out", "/certs/lab.crt", "-subj", "/CN=www.climatis.com.br", "-addext", "subjectAltName=DNS:www.climatis.com.br,DNS:climatis.com.br,DNS:localhost,IP:127.0.0.1"])
    save_json("compose-resolved.json", json.loads(compose(project, ["--profile", "direct", "--profile", "proxy", "config", "--format", "json"]).stdout))
    rows, error = [], None
    if args.only:
        for name in SCENARIOS:
            previous = RESULTS / (name + ".json")
            if name not in selected and previous.exists():
                rows.extend(json.loads(previous.read_text(encoding="utf-8")))
    save_json("latest-execution.json", {"selected": sorted(selected), "image_id": json.loads(command(["docker", "image", "inspect", IMAGE]).stdout)[0]["Id"], "client_image": CLIENT_IMAGE, "started_at": datetime.now(timezone.utc).isoformat()})
    cleanup = {"attempted": False, "successful": False}
    try:
        loops = [Case("loop-proxy-https", CANONICAL + "/", expected_loop=True, expectation="Detectar loop de 302 quando TLS termina na borda e a origem testa HTTPS=off"), Case("loop-proxy-index", CANONICAL + "/index.html", expected_loop=True, expectation="Detectar normalização de index seguida de loop por HTTPS=off")]
        for name in SCENARIOS:
            if name not in selected:
                continue
            if name == "baseline":
                rows += run_direct(project, name, baseline_cases())
            elif name in ("candidate-root", "candidate-vhost"):
                rows += run_direct(project, name, policy_cases() + method_cases())
            elif name.startswith("merge-"):
                rows += run_direct(project, name, [Case("mesclagem-pai", CANONICAL + "/api/echo.php", expected_url=CANONICAL + "/api/echo.php", expected_redirects=0, echo_body=True, parent_expected="seen" if name == "merge-baseline" else "absent")])
            elif name.startswith("precedence-"):
                target = CANONICAL + ("/alias-order.html" if name == "precedence-directory" else "/rewrite-order.html")
                cases = [Case("precedencia-modulos", CANONICAL + "/module-order", method, expected_url=target, expected_redirects=1, initial_status=302) for method in ("GET", "HEAD")]
                if name == "precedence-directory":
                    for case in cases:
                        case.expectation = "Hipótese anterior, REFUTADA no laboratório: Redirect antecederia RewriteRule no .htaccess"
                if name == "precedence-vhost":
                    cases += [Case("tls-ca-nao-confiavel", CANONICAL + "/", transport="untrusted-ca", expectation="Rejeitar certificado sem CA explícita do laboratório"), Case("tls-sni-incorreto", CANONICAL + "/", transport="wrong-sni", expectation="Rejeitar nome de servidor diferente do SAN"), Case("bloquear-destino-externo", "https://blocked.seo5a.invalid/", transport="blocked-host", expectation="Rejeitar URL antes de qualquer conexão/DNS")]
                rows += run_direct(project, name, cases)
            elif name == "proxy-root-naive":
                rows += run_proxy(project, name, "candidate-root", "proxy-naive", loops)
            elif name == "proxy-vhost-naive":
                rows += run_proxy(project, name, "candidate-vhost", "proxy-naive", loops)
            elif name == "proxy-edge-fixed-query":
                cases = [Case("blog-sem-barra-query", base + "/Blog?" + QUERY, method, expected_url=CANONICAL + "/Blog/?" + QUERY, expected_redirects=1, initial_status=302, contains=b"blog-fixture:/Blog/") for base in BASES for method in ("GET", "HEAD")]
                rows += run_proxy(project, name, "baseline", "proxy-edge-fixed", cases)
            elif name == "proxy-edge-fixed-headers":
                cases = []
                for scheme, spoof in [("http", "https"), ("https", "http")]:
                    url = scheme + "://www.climatis.com.br/api/echo.php"
                    cases.append(Case("proxy-sobrescreve-xfp", url, "POST", b"fixture", {"Content-Type": "text/plain", "X-Forwarded-Proto": spoof}, expected_url=url, expected_redirects=0, echo_body=True, content_type="application/json", forwarded_expected=scheme))
                rows += run_proxy(project, name, "baseline", "proxy-edge-fixed", cases)
            else:
                rows += run_proxy(project, name, "baseline", name, policy_cases() + method_cases())
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
        (RESULTS / "execution-error.txt").write_text(error, encoding="utf-8")
    finally:
        cleanup["attempted"] = True
        response = compose(project, ["--profile", "direct", "--profile", "proxy", "down", "--remove-orphans"], check=False)
        cleanup["successful"] = response.returncode == 0
        cleanup["output"] = response.stdout + response.stderr
        check_originals()
        report(rows, error, cleanup)
    return 1 if error or not cleanup["successful"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
