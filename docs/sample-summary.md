# Vulnerability remediation summary, 2026-10-27

As of 2026-10-27, 91 findings are open and 25 of them are past their SLA. SLA compliance over the last 90 days is 78% (103 of 132 findings that came due were closed on time). Month to date, compliance is 83%, up 11 points from 72% in 2026-09. The open backlog is 91, down 19% from its peak of 113 at the end of 2026-05. No critical findings are open.

## Recommendations

1. Focus on data-platform: it holds 15 of 25 overdue findings (60%), with a mean time to fix of 116.4 days. Agree a burn-down plan and review it weekly.
2. Low findings have the lowest SLA compliance (67% against a 180-day target). Check whether that SLA is realistic or whether these need clearer owners.
3. 9 risk exception(s) have expired. Each needs re-approval or remediation; an expired exception is an untracked open risk.
4. The longest-overdue item is VULN-0144 (medium, data-platform), 186 days past due.

## By severity (last 90 days)

| Severity | SLA | Open | Overdue | SLA compliance | MTTR mean | MTTR median |
|---|---|---|---|---|---|---|
| Critical | 15 days | 0 | 0 | 75% | 11 days | 10.5 days |
| High | 30 days | 1 | 0 | 91% | 17.8 days | 17 days |
| Medium | 90 days | 34 | 10 | 79% | 70.9 days | 48 days |
| Low | 180 days | 56 | 15 | 67% | 129 days | 119 days |

## By team

| Team | Open | Critical + high open | Overdue | SLA compliance | MTTR mean |
|---|---|---|---|---|---|
| data-platform | 33 | 0 | 15 | 46% | 116.4 days |
| web-frontend | 21 | 0 | 5 | 77% | 76.1 days |
| mobile | 19 | 0 | 4 | 76% | 68.3 days |
| payments-api | 11 | 0 | 1 | 96% | 54.1 days |
| identity | 7 | 1 | 0 | 100% | 46.6 days |

## Trend

| Month | Opened | Fixed | Open at month end | SLA compliance |
|---|---|---|---|---|
| 2025-11 | 44 | 5 | 47 | 83% |
| 2025-12 | 49 | 17 | 76 | 62% |
| 2026-01 | 48 | 31 | 92 | 42% |
| 2026-02 | 37 | 32 | 97 | 71% |
| 2026-03 | 49 | 34 | 109 | 71% |
| 2026-04 | 35 | 33 | 111 | 63% |
| 2026-05 | 41 | 39 | 113 | 74% |
| 2026-06 | 35 | 38 | 109 | 63% |
| 2026-07 | 39 | 45 | 103 | 75% |
| 2026-08 | 40 | 38 | 105 | 82% |
| 2026-09 | 44 | 49 | 97 | 72% |
| 2026-10 | 33 | 39 | 91 | 83% |
