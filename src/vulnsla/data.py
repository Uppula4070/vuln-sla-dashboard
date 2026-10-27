"""Load a vulnerability tracker export (CSV) and check it."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SEVERITIES = ["critical", "high", "medium", "low"]
STATUSES = ["open", "fixed", "risk-accepted", "false-positive"]
DEFAULT_SLA = {"critical": 15, "high": 30, "medium": 90, "low": 180}
REQUIRED_COLUMNS = ["id", "title", "asset", "owner", "severity", "found_date", "status"]


class DataError(Exception):
    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass
class Finding:
    id: str
    title: str
    asset: str
    owner: str
    severity: str
    found: date
    status: str
    closed: date | None = None
    cve: str = ""
    source: str = ""
    exception_expires: date | None = None

    def is_open_on(self, day: date) -> bool:
        """Open on `day`: found by then and not yet fixed or accepted. False positives never count."""
        if self.status == "false-positive" or self.found > day:
            return False
        return self.closed is None or self.closed > day

    def age_on(self, day: date) -> int:
        return ((self.closed if self.closed and self.closed <= day else day) - self.found).days

    def days_to_close(self) -> int | None:
        return (self.closed - self.found).days if self.closed else None


def _date(value: str, field: str, row: int, problems: list[str]) -> date | None:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        problems.append(f"row {row}: {field} '{value}' is not a YYYY-MM-DD date")
        return None


def parse_sla(text: str | None) -> dict[str, int]:
    """'critical=7,high=30' overrides the defaults for the severities given."""
    sla = dict(DEFAULT_SLA)
    for part in (text or "").split(","):
        if not part.strip():
            continue
        name, _, days = part.partition("=")
        name = name.strip().lower()
        if name not in sla or not days.strip().isdigit():
            raise DataError([f"bad SLA setting '{part.strip()}', expected e.g. critical=15"])
        sla[name] = int(days)
    return sla


def load(path: str | Path) -> list[Finding]:
    problems: list[str] = []
    findings: list[Finding] = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise DataError([f"missing column(s): {', '.join(missing)}"])
        seen: set[str] = set()
        for n, row in enumerate(reader, start=2):  # row 1 is the header
            sev = row["severity"].strip().lower()
            status = row["status"].strip().lower()
            if sev not in SEVERITIES:
                problems.append(f"row {n}: severity '{row['severity']}' must be one of {', '.join(SEVERITIES)}")
            if status not in STATUSES:
                problems.append(f"row {n}: status '{row['status']}' must be one of {', '.join(STATUSES)}")
            found = _date(row["found_date"], "found_date", n, problems)
            closed = _date(row.get("closed_date", ""), "closed_date", n, problems)
            expires = _date(row.get("exception_expires", ""), "exception_expires", n, problems)
            if found is None:
                problems.append(f"row {n}: found_date is required")
                continue
            if status in ("fixed", "risk-accepted") and closed is None:
                problems.append(f"row {n}: status '{status}' needs a closed_date")
            if status == "open" and closed is not None:
                problems.append(f"row {n}: status 'open' but closed_date is set")
            if closed and closed < found:
                problems.append(f"row {n}: closed_date is before found_date")
            fid = row["id"].strip()
            if fid in seen:
                problems.append(f"row {n}: duplicate id {fid}")
            seen.add(fid)
            findings.append(
                Finding(
                    id=fid,
                    title=row["title"].strip(),
                    asset=row["asset"].strip(),
                    owner=row["owner"].strip() or "unassigned",
                    severity=sev,
                    found=found,
                    status=status,
                    closed=closed,
                    cve=(row.get("cve") or "").strip(),
                    source=(row.get("source") or "").strip(),
                    exception_expires=expires,
                )
            )
    if problems:
        raise DataError(problems)
    return findings
