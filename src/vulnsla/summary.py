"""Plain-English findings and recommendations derived from the metrics."""

from __future__ import annotations

from .metrics import Compliance, Metrics


def pct(c: Compliance) -> str:
    return "n/a" if c.rate is None else f"{c.rate:.0%}"


def headline(m: Metrics) -> list[str]:
    lines = [
        f"As of {m.as_of}, {m.open} findings are open and {m.overdue} of them are past their SLA.",
        f"SLA compliance over the last {m.window_days} days is {pct(m.compliance)} "
        f"({m.compliance.met} of {m.compliance.due} findings that came due were closed on time).",
    ]
    if len(m.months) >= 2:
        cur, prev = m.months[-1], m.months[-2]
        if cur.compliance.rate is not None and prev.compliance.rate is not None:
            delta = (cur.compliance.rate - prev.compliance.rate) * 100
            word = "up" if delta > 0 else "down" if delta < 0 else "unchanged"
            change = f"{word} {abs(delta):.0f} points" if delta else word
            lines.append(
                f"Month to date, compliance is {pct(cur.compliance)}, "
                f"{change} from {pct(prev.compliance)} in {prev.label}."
            )
        peak = max(m.months, key=lambda r: r.backlog)
        if peak is not m.months[-1] and peak.backlog > cur.backlog:
            drop = 1 - cur.backlog / peak.backlog
            lines.append(
                f"The open backlog is {cur.backlog}, down {drop:.0%} "
                f"from its peak of {peak.backlog} at the end of {peak.label}."
            )
        else:
            lines.append(f"The open backlog is {cur.backlog}, the highest in the last {len(m.months)} months.")
    crit = next(r for r in m.severity_rows if r.severity == "critical")
    if crit.open:
        lines.append(f"{crit.open} critical finding(s) are open; {crit.overdue} are overdue.")
    else:
        lines.append("No critical findings are open.")
    return lines


def recommendations(m: Metrics) -> list[str]:
    recs = []
    worst = m.owners[0] if m.owners and m.owners[0].overdue else None
    if worst:
        share = worst.overdue / m.overdue
        mttr = f", with a mean time to fix of {worst.mttr_mean:g} days" if worst.mttr_mean is not None else ""
        recs.append(
            f"Focus on {worst.owner}: it holds {worst.overdue} of {m.overdue} overdue findings ({share:.0%}){mttr}. "
            "Agree a burn-down plan and review it weekly."
        )
    graded = [r for r in m.severity_rows if r.compliance.rate is not None]
    if graded:
        low = min(graded, key=lambda r: r.compliance.rate)
        recs.append(
            f"{low.severity.title()} findings have the lowest SLA compliance ({pct(low.compliance)} against a "
            f"{low.sla_days}-day target). Check whether that SLA is realistic or whether these need clearer owners."
        )
    if m.expired_exceptions:
        recs.append(
            f"{len(m.expired_exceptions)} risk exception(s) have expired. Each needs re-approval or remediation; "
            "an expired exception is an untracked open risk."
        )
    if m.expiring_exceptions:
        recs.append(f"{len(m.expiring_exceptions)} risk exception(s) expire in the next 30 days.")
    oldest = max(m.overdue_items, key=lambda pair: pair[1], default=None)
    if oldest:
        f, days = oldest
        recs.append(f"The longest-overdue item is {f.id} ({f.severity}, {f.owner}), {days} days past due.")
    return recs


def markdown(m: Metrics) -> str:
    out = [f"# Vulnerability remediation summary, {m.as_of}", ""]
    out += [" ".join(headline(m)), "", "## Recommendations", ""]
    out += [f"{i}. {r}" for i, r in enumerate(recommendations(m), 1)]
    out += [
        "",
        f"## By severity (last {m.window_days} days)",
        "",
        "| Severity | SLA | Open | Overdue | SLA compliance | MTTR mean | MTTR median |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in m.severity_rows:
        out.append(
            f"| {r.severity.title()} | {r.sla_days} days | {r.open} | {r.overdue} | {pct(r.compliance)} | "
            f"{_days(r.mttr_mean)} | {_days(r.mttr_median)} |"
        )
    out += [
        "",
        "## By team",
        "",
        "| Team | Open | Critical + high open | Overdue | SLA compliance | MTTR mean |",
        "|---|---|---|---|---|---|",
    ]
    for o in m.owners:
        out.append(
            f"| {o.owner} | {o.open} | {o.critical_high_open} | {o.overdue} | "
            f"{pct(o.compliance)} | {_days(o.mttr_mean)} |"
        )
    out += [
        "",
        "## Trend",
        "",
        "| Month | Opened | Fixed | Open at month end | SLA compliance |",
        "|---|---|---|---|---|",
    ]
    for r in m.months:
        out.append(f"| {r.label} | {r.opened} | {r.fixed} | {r.backlog} | {pct(r.compliance)} |")
    return "\n".join(out) + "\n"


def _days(v: float | None) -> str:
    return "–" if v is None else f"{v:g} days"
