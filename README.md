# sdwan_backend_prod_data — Claude Code Skill

A Claude Code custom skill (`/sdwan_backend_prod_data`) for querying the **Prisma SD-WAN production BigQuery dataset** using your own GCP credentials.

## What it does

- Query flow stats, app traffic, bandwidth, health, and events from BigQuery
- Works with any tenant/site — just pass IDs in your request
- Uses Application Default Credentials — your GCP login, not a hardcoded key
- No `bq` CLI required — uses BigQuery REST API directly via Python stdlib

## Install

Copy the skill file into your Claude Code commands directory:

```bash
curl -o ~/.claude/commands/sdwan_backend_prod_data.md \
  https://raw.githubusercontent.com/ksanthakumar-hub/sdwan-bigquery-skill/main/sdwan_backend_prod_data.md
```

## Setup

```bash
# Authenticate with your own GCP account
gcloud auth application-default login

# Verify it works
gcloud auth application-default print-access-token
```

You need **BigQuery Data Viewer** IAM on project `pa-sase-insights-prod-01` (or whichever project you point it at).

## Usage

In Claude Code, invoke the skill:

```
/sdwan_backend_prod_data show flows for tenant 1468 site 1727354501163010608 with private IPs last 24h
/sdwan_backend_prod_data top apps by bandwidth for tenant 1468 last 7 days
/sdwan_backend_prod_data list all tables in sdwan_dataset
/sdwan_backend_prod_data describe the schema of flow_stats_view
/sdwan_backend_prod_data show events for tenant 1468 last 1 hour
```

## Requirements

- Claude Code CLI
- `gcloud` CLI installed and authenticated (`gcloud auth application-default login`)
- Python 3 (stdlib only — no pip installs needed)
- BigQuery read access to the target GCP project

## Notes

- All stats tables require a partition filter on `event_time` — the skill handles this automatically
- `tenant_id` is always treated as a STRING in queries
- Results are summarized by app, path, and traffic volume by default
