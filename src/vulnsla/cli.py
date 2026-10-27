from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path

from . import __version__
from .dashboard import build
from .data import SEVERITIES, DataError, load, parse_sla
from .metrics import compute
from .summary import headline, markdown


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="vulnsla",
        description="Vulnerability remediation metrics: SLA compliance, MTTR, backlog trend and aging.",
    )
    p.add_argument("csv", help="tracker export (see README for columns)")
    p.add_argument("-o", "--output", default="dashboard.html", help="HTML dashboard to write")
    p.add_argument("--summary", metavar="FILE", help="also write a Markdown summary")
    p.add_argument("--json", metavar="FILE", help="also write the metrics as JSON")
    p.add_argument("--as-of", type=date.fromisoformat, default=date.today(), help="report date (default: today)")
    p.add_argument("--window", type=int, default=90, help="days covered by compliance and MTTR (default 90)")
    p.add_argument("--months", type=int, default=12, help="months in the trend charts (default 12)")
    p.add_argument("--sla", help="override SLA days, e.g. critical=7,high=30")
    p.add_argument("--title", default="Vulnerability remediation dashboard")
    p.add_argument("--subtitle", default="")
    p.add_argument(
        "--fail-if-overdue",
        choices=SEVERITIES,
        metavar="SEVERITY",
        help="exit 1 if anything this severity or worse is overdue (for CI)",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        sla = parse_sla(args.sla)
        findings = load(args.csv)
    except DataError as exc:
        print("The input has problems to fix:", file=sys.stderr)
        for problem in exc.problems[:50]:
            print(f"  - {problem}", file=sys.stderr)
        return 2

    m = compute(findings, sla, args.as_of, window_days=args.window, months=args.months)
    Path(args.output).write_text(build(m, args.title, args.subtitle), encoding="utf-8")
    if args.summary:
        Path(args.summary).write_text(markdown(m), encoding="utf-8")
    if args.json:
        Path(args.json).write_text(json.dumps(asdict(m), indent=2, default=str), encoding="utf-8")

    for line in headline(m):
        print(line)
    print(f"wrote {args.output}")

    if args.fail_if_overdue:
        worst = SEVERITIES[: SEVERITIES.index(args.fail_if_overdue) + 1]
        late = [f for f, _ in m.overdue_items if f.severity in worst]
        if late:
            print(f"failing: {len(late)} overdue finding(s) at {args.fail_if_overdue} or worse", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
