from datetime import date

import pytest

from vulnsla.data import DEFAULT_SLA, DataError, load, parse_sla


def test_loads_sample(sample_csv):
    findings = load(sample_csv)
    assert len(findings) > 400
    assert {f.severity for f in findings} == {"critical", "high", "medium", "low"}


def test_is_open_on(make_csv):
    f = load(make_csv([{"found_date": "2026-01-10", "closed_date": "2026-02-01", "status": "fixed"}]))[0]
    assert not f.is_open_on(date(2026, 1, 9))  # not found yet
    assert f.is_open_on(date(2026, 1, 31))
    assert not f.is_open_on(date(2026, 2, 1))  # closed that day


def test_false_positive_never_open(make_csv):
    f = load(make_csv([{"closed_date": "2026-01-02", "status": "false-positive"}]))[0]
    assert not f.is_open_on(date(2026, 1, 1))


@pytest.mark.parametrize(
    ("row", "message"),
    [
        ({"severity": "urgent"}, "severity 'urgent'"),
        ({"status": "done"}, "status 'done'"),
        ({"found_date": "01/02/2026"}, "not a YYYY-MM-DD date"),
        ({"status": "fixed"}, "needs a closed_date"),
        ({"closed_date": "2026-02-01"}, "status 'open' but closed_date is set"),
        ({"found_date": "2026-03-01", "closed_date": "2026-02-01", "status": "fixed"}, "before found_date"),
    ],
)
def test_rejects_bad_rows(make_csv, row, message):
    with pytest.raises(DataError) as exc:
        load(make_csv([row]))
    assert any(message in p for p in exc.value.problems)


def test_reports_row_numbers_and_duplicates(make_csv):
    with pytest.raises(DataError) as exc:
        load(make_csv([{"id": "X"}, {"id": "X", "severity": "nope"}]))
    problems = exc.value.problems
    assert any(p.startswith("row 3:") and "duplicate id X" in p for p in problems)
    assert any(p.startswith("row 3:") and "severity" in p for p in problems)


def test_missing_columns(tmp_path):
    path = tmp_path / "bad.csv"
    path.write_text("id,title\n1,x\n", encoding="utf-8")
    with pytest.raises(DataError, match="missing column"):
        load(path)


def test_parse_sla():
    assert parse_sla(None) == DEFAULT_SLA
    assert parse_sla("critical=7, low=365") == {**DEFAULT_SLA, "critical": 7, "low": 365}
    with pytest.raises(DataError):
        parse_sla("urgent=1")
    with pytest.raises(DataError):
        parse_sla("critical=soon")
