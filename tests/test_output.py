import json
from datetime import date

from vulnsla.charts import line_chart, nice_max, target_bars
from vulnsla.cli import main
from vulnsla.dashboard import build
from vulnsla.data import DEFAULT_SLA, load
from vulnsla.metrics import compute
from vulnsla.summary import headline, recommendations


def test_nice_max():
    assert [nice_max(v) for v in (0, 7, 11, 113, 450)] == [1, 10, 20, 200, 500]


def test_charts_have_tooltips_and_labels():
    svg = line_chart(["a", "b"], [10, 20], "Backlog")
    assert svg.count("<title>") == 2 and 'aria-label="Backlog"' in svg
    bars = target_bars([("Critical", 20, 15), ("Low", 50, 180)], "MTTR")
    assert "20 · over" in bars and "bar-over" in bars
    assert "50 · over" not in bars


def test_dashboard_escapes_csv_text(make_csv):
    path = make_csv([{"title": "<img src=x onerror=alert(1)>", "found_date": "2025-01-01"}])
    html = build(compute(load(path), DEFAULT_SLA, date(2026, 6, 30)))
    assert "<img src=x" not in html
    assert "&lt;img src=x" in html


def test_summary_text(sample_csv):
    m = compute(load(sample_csv), DEFAULT_SLA, date(2026, 10, 27))
    text = " ".join(headline(m))
    assert "findings are open" in text and "SLA compliance over the last 90 days" in text
    assert recommendations(m)[0].startswith("Focus on data-platform")


def test_cli_writes_all_outputs(sample_csv, tmp_path, capsys):
    html, md, js = tmp_path / "d.html", tmp_path / "s.md", tmp_path / "m.json"
    code = main([str(sample_csv), "--as-of", "2026-10-27", "-o", str(html), "--summary", str(md), "--json", str(js)])
    assert code == 0
    assert html.read_text(encoding="utf-8").startswith("<!doctype html>")
    assert md.read_text(encoding="utf-8").startswith("# Vulnerability remediation summary")
    assert json.loads(js.read_text(encoding="utf-8"))["open"] > 0
    assert "past their SLA" in capsys.readouterr().out


def test_cli_ci_gate(sample_csv, tmp_path):
    out = str(tmp_path / "d.html")
    assert main([str(sample_csv), "--as-of", "2026-10-27", "-o", out, "--fail-if-overdue", "low"]) == 1
    assert main([str(sample_csv), "--as-of", "2026-10-27", "-o", out, "--fail-if-overdue", "critical"]) == 0


def test_cli_reports_bad_input(make_csv, tmp_path, capsys):
    path = make_csv([{"severity": "urgent"}])
    assert main([str(path), "-o", str(tmp_path / "d.html")]) == 2
    assert "severity 'urgent'" in capsys.readouterr().err
