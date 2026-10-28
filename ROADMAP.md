# Roadmap

Small, self-contained improvements, each one commit that keeps CI green.
Size: 🟢 under an hour · 🟡 an evening · 🔴 a weekend.

## Metrics

- [ ] 🟢 Add a `--by-week` option for the trend charts
- [ ] 🟡 SLA compliance trend per team (one small chart per team)
- [ ] 🟡 Asset criticality: shorter SLAs for findings on critical assets, read from a config file
- [ ] 🟡 Exception aging: how long each risk acceptance has been open, and how many times it was renewed

## Inputs

- [ ] 🟢 Accept column-name mapping (`--map found_date=Created`) so Jira and ServiceNow exports work without editing
- [ ] 🟡 Read `.xlsx` files as well as CSV

## Publishing

- [ ] 🟢 Publish the sample dashboard with GitHub Pages so recruiters can open it in one click
