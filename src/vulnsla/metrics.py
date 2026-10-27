"""Compute remediation metrics as of a given day.

Definitions (also in the README):
- Overdue: still open and older than its severity's SLA.
- SLA compliance: of the findings whose due date (found + SLA) fell inside the window, the share that
  were fixed or formally risk-accepted on or before that due date. Open findings that passed their
  due date count as misses, so a team can't look compliant by simply not closing anything.
- MTTR: days from found to fixed, for findings fixed inside the window. Mean and median are both
  reported because a few very old fixes skew the mean.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from statistics import mean, median

from .data import SEVERITIES, Finding

AGING_BUCKETS = [(0, 30, "0–30 days"), (31, 60, "31–60"), (61, 90, "61–90"), (91, 180, "91–180"), (181, None, "180+")]


@dataclass
class Compliance:
    met: int = 0
    due: int = 0

    @property
    def rate(self) -> float | None:
        return self.met / self.due if self.due else None


@dataclass
class SeverityRow:
    severity: str
    sla_days: int
    open: int
    overdue: int
    compliance: Compliance
    mttr_mean: float | None
    mttr_median: float | None


@dataclass
class MonthRow:
    label: str  # e.g. "2026-10"
    end: date
    opened: int
    fixed: int
    backlog: int
    compliance: Compliance


@dataclass
class OwnerRow:
    owner: str
    open: int
    overdue: int
    critical_high_open: int
    compliance: Compliance
    mttr_mean: float | None


@dataclass
class Metrics:
    as_of: date
    window_days: int
    sla: dict[str, int]
    total_tracked: int
    open: int
    overdue: int
    compliance: Compliance
    severity_rows: list[SeverityRow]
    months: list[MonthRow]
    aging: dict[str, dict[str, int]]
    owners: list[OwnerRow]
    overdue_items: list[tuple[Finding, int]] = field(default_factory=list)  # (finding, days past due)
    expired_exceptions: list[Finding] = field(default_factory=list)
    expiring_exceptions: list[Finding] = field(default_factory=list)


def due_date(f: Finding, sla: dict[str, int]) -> date:
    return f.found + timedelta(days=sla[f.severity])


def compliance(findings: list[Finding], sla: dict[str, int], start: date, end: date) -> Compliance:
    """Findings due in (start, end]: met if closed (fixed or accepted) by the due date."""
    c = Compliance()
    for f in findings:
        if f.status == "false-positive":
            continue
        due = due_date(f, sla)
        if start < due <= end:
            c.due += 1
            if f.closed is not None and f.closed <= due:
                c.met += 1
    return c


def _mttr(findings: list[Finding], start: date, end: date) -> tuple[float | None, float | None]:
    days = [f.days_to_close() for f in findings if f.status == "fixed" and f.closed and start < f.closed <= end]
    days = [d for d in days if d is not None]
    return (round(mean(days), 1), float(median(days))) if days else (None, None)


def _month_ends(as_of: date, count: int) -> list[date]:
    ends, cursor = [], as_of
    for _ in range(count):
        ends.append(cursor)
        cursor = cursor.replace(day=1) - timedelta(days=1)  # last day of previous month
    return list(reversed(ends))


def _bucket(age: int) -> str:
    for low, high, label in AGING_BUCKETS:
        if age >= low and (high is None or age <= high):
            return label
    return AGING_BUCKETS[-1][2]


def compute(
    findings: list[Finding], sla: dict[str, int], as_of: date, window_days: int = 90, months: int = 12
) -> Metrics:
    start = as_of - timedelta(days=window_days)
    open_now = [f for f in findings if f.is_open_on(as_of)]
    overdue_now = [f for f in open_now if f.age_on(as_of) > sla[f.severity]]

    severity_rows = []
    for sev in SEVERITIES:
        group = [f for f in findings if f.severity == sev]
        mttr_mean, mttr_median = _mttr(group, start, as_of)
        severity_rows.append(
            SeverityRow(
                severity=sev,
                sla_days=sla[sev],
                open=sum(f.severity == sev for f in open_now),
                overdue=sum(f.severity == sev for f in overdue_now),
                compliance=compliance(group, sla, start, as_of),
                mttr_mean=mttr_mean,
                mttr_median=mttr_median,
            )
        )

    month_rows = []
    for end in _month_ends(as_of, months):
        first = end.replace(day=1)
        month_rows.append(
            MonthRow(
                label=end.strftime("%Y-%m"),
                end=end,
                opened=sum(first <= f.found <= end and f.status != "false-positive" for f in findings),
                fixed=sum(f.status == "fixed" and f.closed is not None and first <= f.closed <= end for f in findings),
                backlog=sum(f.is_open_on(end) for f in findings),
                compliance=compliance(findings, sla, first - timedelta(days=1), end),
            )
        )

    aging = {label: dict.fromkeys(SEVERITIES, 0) for _, _, label in AGING_BUCKETS}
    for f in open_now:
        aging[_bucket(f.age_on(as_of))][f.severity] += 1

    owners = []
    for owner in sorted({f.owner for f in findings}):
        group = [f for f in findings if f.owner == owner]
        owners.append(
            OwnerRow(
                owner=owner,
                open=sum(f.owner == owner for f in open_now),
                overdue=sum(f.owner == owner for f in overdue_now),
                critical_high_open=sum(f.owner == owner and f.severity in ("critical", "high") for f in open_now),
                compliance=compliance(group, sla, start, as_of),
                mttr_mean=_mttr(group, start, as_of)[0],
            )
        )
    owners.sort(key=lambda o: (-o.overdue, -o.open, o.owner))

    overdue_items = sorted(
        ((f, (as_of - due_date(f, sla)).days) for f in overdue_now),
        key=lambda pair: (SEVERITIES.index(pair[0].severity), -pair[1]),
    )
    accepted = [f for f in findings if f.status == "risk-accepted" and f.exception_expires]
    return Metrics(
        as_of=as_of,
        window_days=window_days,
        sla=sla,
        total_tracked=sum(f.status != "false-positive" for f in findings),
        open=len(open_now),
        overdue=len(overdue_now),
        compliance=compliance(findings, sla, start, as_of),
        severity_rows=severity_rows,
        months=month_rows,
        aging=aging,
        owners=owners,
        overdue_items=overdue_items,
        expired_exceptions=sorted(
            (f for f in accepted if f.exception_expires < as_of), key=lambda f: f.exception_expires
        ),
        expiring_exceptions=sorted(
            (f for f in accepted if as_of <= f.exception_expires <= as_of + timedelta(days=30)),
            key=lambda f: f.exception_expires,
        ),
    )
