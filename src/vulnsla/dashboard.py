"""Build the self-contained HTML dashboard. All text from the CSV is escaped."""

from __future__ import annotations

from html import escape

from . import charts
from .metrics import AGING_BUCKETS, Metrics
from .summary import headline, pct, recommendations

CSS = """
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --series-1: #2a78d6; --series-2: #eb6834; --target: #52514e;
  --critical: #d03b3b; --serious: #ec835a; --warning: #fab219; --good: #0ca30c; --low: #2a78d6;
  --bar: #2a78d6; --bar-over: #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:where(:not([data-theme="light"])) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --series-1: #3987e5; --series-2: #d95926; --target: #c3c2b7; --low: #3987e5;
    --bar: #3987e5; --bar-over: #d03b3b;
  }
}
:root[data-theme="dark"] {
  color-scheme: dark;
  --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
  --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
  --series-1: #3987e5; --series-2: #d95926; --target: #c3c2b7; --low: #3987e5;
  --bar: #3987e5; --bar-over: #d03b3b;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 1120px; margin: 0 auto; padding: 28px 24px 56px; }
header h1 { margin: 0 0 4px; font-size: 26px; }
header p { margin: 0; color: var(--ink-2); }
h2 { font-size: 17px; margin: 0 0 12px; }
.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 22px 0; }
.card { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px 18px; }
.tile .v { font-size: 30px; font-weight: 650; }
.tile .k { color: var(--ink-2); font-size: 13px; }
.tile .s { color: var(--muted); font-size: 12px; margin-top: 2px; }
.grid2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(420px, 100%), 1fr)); gap: 14px; margin-top: 14px; }
.grid2 > * { min-width: 0; } /* let wide tables scroll inside their card instead of stretching the page */
.narrative p { margin: 0 0 6px; }
.narrative ol { margin: 8px 0 0; padding-left: 20px; }
.note { color: var(--muted); font-size: 12px; margin: 6px 0 0; }
.legend { display: flex; gap: 16px; font-size: 13px; color: var(--ink-2); margin-bottom: 4px; }
.legend i { display: inline-block; width: 10px; height: 10px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
svg.chart { width: 100%; height: auto; display: block; }
svg .grid { stroke: var(--grid); stroke-width: 1; }
svg .axis { stroke: var(--axis); stroke-width: 1; }
svg .tick { fill: var(--muted); font-size: 13px; font-variant-numeric: tabular-nums; }
svg .cat { fill: var(--ink-2); font-size: 14px; }
svg .value { fill: var(--ink); font-size: 14px; font-weight: 600; }
svg .line { fill: none; stroke: var(--series-1); stroke-width: 2; stroke-linejoin: round; }
svg .dot { fill: var(--series-1); stroke: var(--surface); stroke-width: 2; }
svg .hit { fill: transparent; }
svg .pt:hover .dot { r: 6; }
svg .target { stroke: var(--target); stroke-width: 1.5; stroke-dasharray: 5 4; }
svg .target-tick { stroke: var(--ink); stroke-width: 2; }
svg .s1 { fill: var(--series-1); } svg .s2 { fill: var(--series-2); }
svg .bar { fill: var(--bar); } svg .bar-over { fill: var(--bar-over); }
svg path:hover, svg rect:hover { opacity: .85; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--grid); white-space: nowrap; }
th { color: var(--ink-2); font-weight: 600; }
td.num, th.num { text-align: right; }
.sev { display: inline-flex; align-items: center; gap: 6px; }
.sev::before { content: ""; width: 9px; height: 9px; border-radius: 2px; background: var(--c); }
details { margin-top: 10px; } summary { cursor: pointer; color: var(--ink-2); font-size: 13px; }
footer { margin-top: 28px; color: var(--muted); font-size: 12px; }
footer dt { font-weight: 600; color: var(--ink-2); margin-top: 6px; }
footer dd { margin: 0; }
@media (max-width: 640px) { main { padding: 18px 16px 40px; } .grid2 { grid-template-columns: minmax(0, 1fr); } }
"""
SEV_VAR = {"critical": "--critical", "high": "--serious", "medium": "--warning", "low": "--low"}


def _sev(s: str) -> str:
    return f'<span class="sev" style="--c:var({SEV_VAR[s]})">{escape(s.title())}</span>'


def _days(v: float | None) -> str:
    return "–" if v is None else f"{v:g}"


def _table(headers: list[str], rows: list[list[str]], numeric: set[int] = frozenset()) -> str:
    head = "".join(f'<th class="{"num" if i in numeric else ""}">{escape(h)}</th>' for i, h in enumerate(headers))
    body = "".join(
        "<tr>" + "".join(f'<td class="{"num" if i in numeric else ""}">{c}</td>' for i, c in enumerate(r)) + "</tr>"
        for r in rows
    )
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def build(m: Metrics, title: str = "Vulnerability remediation dashboard", subtitle: str = "") -> str:
    months = [r.label[2:].replace("-", "/") for r in m.months]  # "25/11"
    crit = next(r for r in m.severity_rows if r.severity == "critical")

    tiles = [
        (str(m.open), "Open findings", f"{m.total_tracked} tracked in total"),
        (str(m.overdue), "Past SLA", f"{m.overdue / m.open:.0%} of open" if m.open else "none open"),
        (
            pct(m.compliance),
            f"SLA compliance, last {m.window_days} days",
            f"{m.compliance.met} of {m.compliance.due} closed on time",
        ),
        (_days(crit.mttr_median), "Median days to fix a critical", f"target {crit.sla_days} days"),
    ]
    tiles_html = "".join(
        f'<div class="card tile"><div class="v">{escape(v)}</div><div class="k">{escape(k)}</div>'
        f'<div class="s">{escape(s)}</div></div>'
        for v, k, s in tiles
    )
    narrative = "".join(f"<p>{escape(line)}</p>" for line in headline(m))
    recs = "".join(f"<li>{escape(r)}</li>" for r in recommendations(m))

    backlog = charts.line_chart(months, [r.backlog for r in m.months], "Open findings at each month end")
    compliance = charts.line_chart(
        months,
        [None if r.compliance.rate is None else round(r.compliance.rate * 100, 1) for r in m.months],
        "SLA compliance by month",
        pct=True,
        target=90,
        target_label="90% target",
    )
    flow = charts.grouped_bars(
        months,
        [("Opened", [r.opened for r in m.months], "s1"), ("Fixed", [r.fixed for r in m.months], "s2")],
        "Findings opened and fixed per month",
    )
    mttr = charts.target_bars(
        [(r.severity.title(), r.mttr_mean, r.sla_days) for r in m.severity_rows],
        "Mean days to fix by severity, against the SLA target",
    )
    aging_labels = [label for _, _, label in AGING_BUCKETS]
    aging_counts = [sum(m.aging[b].values()) for b in aging_labels]
    aging = charts.grouped_bars(aging_labels, [("Open findings", aging_counts, "s1")], "Age of open findings")

    month_table = _table(
        ["Month", "Opened", "Fixed", "Open at month end", "SLA compliance"],
        [[escape(r.label), str(r.opened), str(r.fixed), str(r.backlog), pct(r.compliance)] for r in m.months],
        numeric={1, 2, 3, 4},
    )
    sev_table = _table(
        ["Severity", "SLA (days)", "Open", "Overdue", "SLA compliance", "MTTR mean", "MTTR median"],
        [
            [
                _sev(r.severity),
                str(r.sla_days),
                str(r.open),
                str(r.overdue),
                pct(r.compliance),
                _days(r.mttr_mean),
                _days(r.mttr_median),
            ]
            for r in m.severity_rows
        ],  # fmt: skip
        numeric={1, 2, 3, 4, 5, 6},
    )
    aging_table = _table(
        ["Age", "Critical", "High", "Medium", "Low", "Total"],
        [
            [escape(b)]
            + [str(m.aging[b][s]) for s in ("critical", "high", "medium", "low")]
            + [str(sum(m.aging[b].values()))]
            for b in aging_labels
        ],  # fmt: skip
        numeric={1, 2, 3, 4, 5},
    )
    owner_table = _table(
        ["Team", "Open", "Critical + high open", "Overdue", "SLA compliance", "MTTR mean (days)"],
        [
            [
                escape(o.owner),
                str(o.open),
                str(o.critical_high_open),
                str(o.overdue),
                pct(o.compliance),
                _days(o.mttr_mean),
            ]
            for o in m.owners
        ],  # fmt: skip
        numeric={1, 2, 3, 4, 5},
    )
    overdue_table = _table(
        ["ID", "Severity", "Finding", "Asset", "Team", "Days past due"],
        [
            [escape(f.id), _sev(f.severity), escape(f.title), escape(f.asset), escape(f.owner), str(days)]
            for f, days in m.overdue_items[:20]
        ],
        numeric={5},
    )
    exception_rows = [
        [escape(f.id), _sev(f.severity), escape(f.title), escape(f.owner), escape(str(f.exception_expires)),
         "Expired" if f.exception_expires < m.as_of else "Expiring soon"]
        for f in m.expired_exceptions + m.expiring_exceptions
    ]  # fmt: skip
    exceptions = (
        _table(["ID", "Severity", "Finding", "Team", "Exception expires", "State"], exception_rows)
        if exception_rows
        else "<p>No risk exceptions are expired or expiring in the next 30 days.</p>"
    )
    sla_text = ", ".join(f"{s} {d} days" for s, d in m.sla.items())

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<main>
<header>
  <h1>{escape(title)}</h1>
  <p>As of {m.as_of}{" · " + escape(subtitle) if subtitle else ""}</p>
</header>

<section class="tiles">{tiles_html}</section>

<section class="card narrative">
  <h2>Summary</h2>
  {narrative}
  <h2 style="margin-top:14px">Recommendations</h2>
  <ol>{recs}</ol>
</section>

<section class="grid2">
  <div class="card"><h2>Open backlog at month end</h2>{backlog}</div>
  <div class="card"><h2>SLA compliance by month</h2>{compliance}
    <p class="note">Share of findings due that month that were closed by their due date.</p></div>
  <div class="card"><h2>Opened vs fixed per month</h2>
    <div class="legend"><span><i style="background:var(--series-1)"></i>Opened</span><span><i style="background:var(--series-2)"></i>Fixed</span></div>
    {flow}
    <details><summary>Show as table</summary>{month_table}</details></div>
  <div class="card"><h2>Mean days to fix vs SLA, last {m.window_days} days</h2>{mttr}
    <p class="note">The vertical tick is the SLA target. Bars past it are marked "over".</p></div>
  <div class="card"><h2>Age of open findings</h2>{aging}
    <details><summary>Show as table, by severity</summary>{aging_table}</details></div>
  <div class="card"><h2>By severity</h2>{sev_table}</div>
</section>

<section class="card" style="margin-top:14px"><h2>By team</h2>{owner_table}</section>
<section class="card" style="margin-top:14px"><h2>Overdue findings ({m.overdue}){" – top 20" if m.overdue > 20 else ""}</h2>{overdue_table}</section>
<section class="card" style="margin-top:14px"><h2>Risk exceptions needing review</h2>{exceptions}</section>

<footer>
  <dl>
    <dt>SLA targets</dt><dd>{escape(sla_text)}, counted from the date a finding was first seen.</dd>
    <dt>SLA compliance</dt><dd>Of findings whose due date fell in the period, the share fixed or formally risk-accepted by that date. Open findings past due count as misses.</dd>
    <dt>MTTR</dt><dd>Days from first seen to fixed, for findings fixed in the last {m.window_days} days. False positives are excluded everywhere.</dd>
  </dl>
  <p>Generated by vulnsla.</p>
</footer>
</main>
</body>
</html>
"""
