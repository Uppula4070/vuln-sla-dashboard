"""Generate the synthetic sample dataset in samples/findings.csv.

Everything here is made up: teams, assets and dates. It is seeded, so the output is identical on every
run. Two patterns are built in so the dashboard has something to show:
- data-platform remediates much more slowly than the other teams;
- every team gets faster after a CI security pipeline is introduced on 2026-05-01.

Usage: python scripts/make_sample_data.py
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

AS_OF = date(2026, 10, 27)
START = AS_OF - timedelta(days=365)
PIPELINE_LIVE = date(2026, 5, 1)
SLA = {"critical": 15, "high": 30, "medium": 90, "low": 180}

TEAMS = {  # how many times the SLA a typical fix takes, before the pipeline improvement
    "identity": 0.45,
    "payments-api": 0.6,
    "web-frontend": 0.85,
    "mobile": 0.9,
    "data-platform": 1.6,
}
ASSET_KINDS = {
    "identity": ["auth-svc", "sso-gw", "user-db"],
    "payments-api": ["pay-gw", "ledger-svc", "card-vault"],
    "web-frontend": ["web-app", "cdn-edge", "cms"],
    "mobile": ["ios-app", "android-app", "mobile-bff"],
    "data-platform": ["etl-node", "warehouse", "kafka-broker"],
}
# (title, cve, severity, source). CVEs are real, well-known identifiers; their use here is illustrative.
CATALOG = [
    ("Apache Log4j2 remote code execution (Log4Shell)", "CVE-2021-44228", "critical", "Nessus"),
    ("Spring Framework RCE (Spring4Shell)", "CVE-2022-22965", "critical", "Nessus"),
    ("SQL injection in search parameter", "", "critical", "Pentest"),
    ("Default credentials on admin console", "", "critical", "Nuclei"),
    ("libwebp heap buffer overflow", "CVE-2023-4863", "high", "Nessus"),
    ("HTTP/2 Rapid Reset denial of service", "CVE-2023-44487", "high", "Nessus"),
    ("Hardcoded secret in repository", "", "high", "Gitleaks"),
    ("Broken object level authorization on account API", "", "high", "Burp Suite"),
    ("Stored cross-site scripting in comments", "", "high", "Burp Suite"),
    ("Vulnerable dependency with published CVE", "", "high", "pip-audit"),
    ("Storage bucket allows public listing", "", "high", "Prowler"),
    ("TLS 1.0/1.1 enabled", "", "medium", "Nessus"),
    ("Outdated jQuery with known XSS issues", "", "medium", "Semgrep"),
    ("Container image runs as root", "", "medium", "Trivy"),
    ("Missing rate limiting on login endpoint", "", "medium", "Pentest"),
    ("Verbose error messages reveal stack traces", "", "medium", "Burp Suite"),
    ("SSH server allows weak MAC algorithms", "", "medium", "Nessus"),
    ("Missing Content-Security-Policy header", "", "low", "OWASP ZAP"),
    ("Missing HSTS header", "", "low", "OWASP ZAP"),
    ("Server banner discloses version", "", "low", "OWASP ZAP"),
    ("Cookie without SameSite attribute", "", "low", "OWASP ZAP"),
]
SEVERITY_WEIGHTS = {"critical": 5, "high": 22, "medium": 43, "low": 30}


def main() -> None:
    rng = random.Random(4070)
    by_sev = {s: [c for c in CATALOG if c[2] == s] for s in SLA}
    rows = []
    day = START
    n = 0
    while day <= AS_OF:
        for _ in range(rng.choice([0, 1, 1, 1, 2, 2, 3])):
            n += 1
            team = rng.choice(list(TEAMS))
            sev = rng.choices(list(SEVERITY_WEIGHTS), weights=list(SEVERITY_WEIGHTS.values()))[0]
            title, cve, _, source = rng.choice(by_sev[sev])
            asset = f"{rng.choice(ASSET_KINDS[team])}-{rng.randint(1, 12):02d}"
            speed = TEAMS[team] * (0.65 if day >= PIPELINE_LIVE else 1.0)
            days = max(1, round(SLA[sev] * speed * rng.lognormvariate(0, 0.55)))
            closed = day + timedelta(days=days)
            status, expires = "fixed", ""
            roll = rng.random()
            if roll < 0.04:
                status, closed = "false-positive", day + timedelta(days=rng.randint(1, 5))
            elif roll < 0.08 and sev in ("medium", "low", "high"):
                status = "risk-accepted"
                closed = day + timedelta(days=rng.randint(5, 25))
                expires = (closed + timedelta(days=rng.choice([60, 90, 180]))).isoformat()
            if closed > AS_OF:
                status, closed, expires = "open", None, ""
            rows.append(
                {
                    "id": f"VULN-{n:04d}",
                    "title": title,
                    "asset": asset,
                    "owner": team,
                    "severity": sev,
                    "cve": cve,
                    "source": source,
                    "found_date": day.isoformat(),
                    "closed_date": closed.isoformat() if closed else "",
                    "status": status,
                    "exception_expires": expires,
                }
            )
        day += timedelta(days=1)

    out = Path(__file__).resolve().parent.parent / "samples" / "findings.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} findings to {out}")


if __name__ == "__main__":
    main()
