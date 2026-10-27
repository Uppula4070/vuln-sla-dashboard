from datetime import date

from vulnsla.data import DEFAULT_SLA, load
from vulnsla.metrics import compute

AS_OF = date(2026, 6, 30)


def test_overdue_uses_severity_sla(make_csv):
    findings = load(
        make_csv(
            [
                {"severity": "critical", "found_date": "2026-06-10"},  # 20 days old > 15: overdue
                {"severity": "critical", "found_date": "2026-06-20"},  # 10 days: within SLA
                {"severity": "low", "found_date": "2026-03-01"},  # 121 days < 180: within SLA
            ]
        )
    )
    m = compute(findings, DEFAULT_SLA, AS_OF)
    assert (m.open, m.overdue) == (3, 1)
    assert m.overdue_items[0][0].found == date(2026, 6, 10)
    assert m.overdue_items[0][1] == 5  # days past due


def test_compliance_counts_open_past_due_as_miss(make_csv):
    findings = load(
        make_csv(
            [
                {"severity": "high", "found_date": "2026-04-01", "closed_date": "2026-04-20", "status": "fixed"},  # met
                {
                    "severity": "high",
                    "found_date": "2026-04-01",
                    "closed_date": "2026-06-01",
                    "status": "fixed",
                },  # late
                {"severity": "high", "found_date": "2026-04-15"},  # still open, due 05-15: miss
                {
                    "severity": "high",
                    "found_date": "2026-04-15",
                    "closed_date": "2026-04-20",
                    "status": "risk-accepted",
                },
                {
                    "severity": "high",
                    "found_date": "2026-04-15",
                    "closed_date": "2026-04-16",
                    "status": "false-positive",
                },
            ]
        )
    )
    c = compute(findings, DEFAULT_SLA, AS_OF).compliance
    assert (c.met, c.due) == (2, 4)  # accepted on time counts as met; false positive excluded
    assert c.rate == 0.5


def test_findings_due_after_today_are_not_judged(make_csv):
    findings = load(make_csv([{"severity": "low", "found_date": "2026-06-01"}]))
    assert compute(findings, DEFAULT_SLA, AS_OF).compliance.due == 0


def test_mttr_mean_and_median(make_csv):
    rows = [
        {"found_date": "2026-05-01", "closed_date": f"2026-05-{d:02d}", "status": "fixed", "severity": "medium"}
        for d in (3, 5, 31)  # 2, 4 and 30 days
    ]
    row = next(r for r in compute(load(make_csv(rows)), DEFAULT_SLA, AS_OF).severity_rows if r.severity == "medium")
    assert row.mttr_mean == 12.0
    assert row.mttr_median == 4.0


def test_monthly_backlog_and_flow(make_csv):
    findings = load(
        make_csv(
            [
                {"found_date": "2026-05-10", "closed_date": "2026-06-05", "status": "fixed"},
                {"found_date": "2026-05-20"},
                {"found_date": "2026-06-02"},
            ]
        )
    )
    months = {r.label: r for r in compute(findings, DEFAULT_SLA, AS_OF, months=2).months}
    assert (months["2026-05"].opened, months["2026-05"].fixed, months["2026-05"].backlog) == (2, 0, 2)
    assert (months["2026-06"].opened, months["2026-06"].fixed, months["2026-06"].backlog) == (1, 1, 2)


def test_aging_buckets(make_csv):
    findings = load(make_csv([{"found_date": "2026-06-20"}, {"found_date": "2025-12-01", "severity": "low"}]))
    aging = compute(findings, DEFAULT_SLA, AS_OF).aging
    assert aging["0–30 days"]["high"] == 1
    assert aging["180+"]["low"] == 1


def test_exceptions(make_csv):
    findings = load(
        make_csv(
            [
                {"status": "risk-accepted", "closed_date": "2026-02-01", "exception_expires": "2026-05-01"},
                {"status": "risk-accepted", "closed_date": "2026-02-01", "exception_expires": "2026-07-15"},
                {"status": "risk-accepted", "closed_date": "2026-02-01", "exception_expires": "2026-12-01"},
            ]
        )
    )
    m = compute(findings, DEFAULT_SLA, AS_OF)
    assert [str(f.exception_expires) for f in m.expired_exceptions] == ["2026-05-01"]
    assert [str(f.exception_expires) for f in m.expiring_exceptions] == ["2026-07-15"]


def test_owners_sorted_by_overdue(make_csv):
    findings = load(
        make_csv(
            [
                {"owner": "fast", "found_date": "2026-06-25"},
                {"owner": "slow", "found_date": "2026-01-01"},
                {"owner": "slow", "found_date": "2026-01-02"},
            ]
        )
    )
    owners = compute(findings, DEFAULT_SLA, AS_OF).owners
    assert [o.owner for o in owners] == ["slow", "fast"]
    assert owners[0].overdue == 2


def test_sample_story(sample_csv):
    """The synthetic data is built so data-platform is the slowest team and the backlog has peaked."""
    m = compute(load(sample_csv), DEFAULT_SLA, date(2026, 10, 27))
    assert m.owners[0].owner == "data-platform"
    assert m.months[-1].backlog < max(r.backlog for r in m.months)
