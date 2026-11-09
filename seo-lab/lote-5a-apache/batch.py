"""Executado em container Python, compartilhando somente a rede do Apache local."""
import argparse
import base64
import hashlib
import json
import sys
import time
from pathlib import Path

from tests import CANONICAL, LAB, Case, Client, run_cases

parser = argparse.ArgumentParser()
parser.add_argument("scenario")
args = parser.parse_args()
scenario = args.scenario
input_file = LAB / "results" / (scenario + "-input.json")
values = json.loads(input_file.read_text(encoding="utf-8"))
cases = []
for value in values:
    value["body"] = base64.b64decode(value["body"])
    value["contains"] = base64.b64decode(value["contains"]) if value["contains"] is not None else None
    cases.append(Case(**value))
client = Client({"http": 80, "https": 443})
deadline = time.monotonic() + 20
while True:
    try:
        response = client.once(CANONICAL + "/api/echo.php", "POST")
        if response["status"] == 200:
            break
        raise RuntimeError(f"Status de readiness={response['status']}")
    except Exception:
        if time.monotonic() >= deadline:
            raise
        time.sleep(0.3)
policy = "baseline" if scenario == "baseline" else "counterexample" if scenario.endswith("naive") else "candidate"
rows = run_cases(client, scenario, cases, LAB / "results" / (scenario + ".json"), policy)
if scenario.startswith("merge-"):
    echo = json.loads(client.once(CANONICAL + "/api/echo.php")["body"])
    (LAB / "results" / (scenario + "-marker.json")).write_text(json.dumps(echo, indent=2), encoding="utf-8")
if scenario in ("proxy-edge", "proxy-edge-fixed"):
    probes = []
    for scheme, spoof in [("https", "http"), ("http", "https")]:
        response = client.once(scheme + "://www.climatis.com.br/api/echo.php", "POST", b"fixture", {"X-Forwarded-Proto": spoof, "Content-Type": "text/plain"})
        value = json.loads(response["body"])
        probes.append({"external_scheme": scheme, "client_xfp": spoof, "backend": value, "passed": value["forwarded_proto"] == scheme and value["https"] != "on" and value["body_sha256"] == hashlib.sha256(b"fixture").hexdigest()})
    (LAB / "results" / (scenario + "-header-overwrite.json")).write_text(json.dumps(probes, indent=2), encoding="utf-8")
    assert all(p['passed'] for p in probes), 'Proxy nao sobrescreveu os headers como esperado'
(LAB / "results" / "client-version.txt").write_text(sys.version, encoding="utf-8")
(LAB / "results" / (scenario + "-client-routes.txt")).write_text(Path('/proc/net/route').read_text(), encoding="utf-8")
assert not any(line.split()[1] == '00000000' for line in Path('/proc/net/route').read_text().splitlines()[1:] if line.strip()), 'Rota externa padrao inesperada'
print(json.dumps({"scenario": scenario, "executed": len(rows), "passed": sum(r["passed"] for r in rows)}))
