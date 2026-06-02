# /sdwan_backend_prod_data — Prisma SD-WAN BigQuery Analytics Skill

Query the Prisma SD-WAN production BigQuery dataset (`sdwan_dataset`) using your own GCP credentials. Supports flow analysis, app breakdowns, bandwidth stats, health data, events, and more.

---

## Prerequisites — run these once before using this skill

```bash
# 1. Authenticate with GCP (your own account)
gcloud auth application-default login

# 2. Verify credentials are active
gcloud auth application-default print-access-token
```

> **Your credentials are never stored in this skill.** Each query fetches a fresh token from `gcloud` at runtime. You must have IAM read access to the BigQuery project you want to query.

---

## How to use this skill

Invoke it as `/sdwan_backend_prod_data` followed by a natural-language request. Examples:

```
/sdwan_backend_prod_data show flows for tenant 1468 site 1727354501163010608 with private IPs last 24h
/sdwan_backend_prod_data top apps by bandwidth for tenant 1468 last 7 days
/sdwan_backend_prod_data show all events for tenant 1468 in the last hour
/sdwan_backend_prod_data bandwidth stats for site 1727354501163010608 grouped by hour
/sdwan_backend_prod_data list all tables in sdwan_dataset
/sdwan_backend_prod_data describe the schema of flow_stats_view
```

Provide at minimum: **tenant_id**, **time range**, and a specific question. Site ID is optional but improves query speed (tables are clustered by `tenant_id`, `site_id`, `event_time`).

---

## BigQuery connection details

| Field | Value |
|---|---|
| Project | `pa-sase-insights-prod-01` |
| Dataset | `sdwan_dataset` |
| Auth | Application Default Credentials (`gcloud`) |
| API | BigQuery REST API v2 |

> To use a **different project or dataset**, specify it in your request: _"use project `my-project`, dataset `my_dataset`"_

---

## How queries are executed

All queries run via the **BigQuery REST API** using a Python one-liner — no `bq` CLI, no SDK required.

```bash
TOKEN=$(gcloud auth application-default print-access-token)

python3 << 'PYEOF'
import urllib.request, json, subprocess

token = subprocess.check_output(
    ["gcloud", "auth", "application-default", "print-access-token"]
).decode().strip()

query = """<YOUR SQL HERE>"""

body = json.dumps({"query": query, "useLegacySql": False, "timeoutMs": 60000}).encode()
req = urllib.request.Request(
    "https://bigquery.googleapis.com/bigquery/v2/projects/pa-sase-insights-prod-01/queries",
    data=body,
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    method="POST"
)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read())

rows = data.get("rows", [])
fields = [f["name"] for f in data["schema"]["fields"]]
records = [{fields[i]: row["f"][i]["v"] for i in range(len(fields))} for row in rows]
print(json.dumps(records, indent=2))
PYEOF
```

---

## Key tables and their purpose

### Flow & Traffic

| Table | Description |
|---|---|
| `flow_stats_view` | Enriched flow records with app name, site name, path IDs, src/dst IPs, ports, bytes |
| `flow_stats` | Raw flow stats (no enrichment) |
| `app_stats_view` | Per-app aggregated traffic (bytes, packets) by site/tenant |
| `app_stats` | Raw per-app stats |
| `interface_stats_view` | Per-interface traffic stats |
| `bandwidth_stats` | WAN bandwidth utilization |
| `agg_bw_stats` | Aggregated bandwidth (5-min buckets, partitioned by `event_time`) |
| `agg_bw_stats_daily` | Daily aggregated bandwidth |

### Health & Quality

| Table | Description |
|---|---|
| `lqm_stats_view` | Link quality metrics (latency, loss, jitter) |
| `site_health_data_*_agg_*` | Site health rollups (5-min, 1-hour, 1-day) sharded 0–4 |
| `link_health_data_*_agg_*` | Link health rollups sharded 0–4 |
| `app_summary_stats_health_data_*` | App-level health sharded 0–4 |

### Events & Alerts

| Table | Description |
|---|---|
| `events` | All SD-WAN events (link up/down, policy changes, etc.) |
| `events_count` | Summarized event counts |
| `sdwan_alerts_view` | Active alerts view |
| `sdwan_incidents_view` | Active incidents view |

### Configuration / Dimension (DO tables)

| Table | Description |
|---|---|
| `sitedo` | Site configuration (name, address, coordinates) |
| `elementdo` | ION device configuration |
| `interfacedo` | Interface configuration |
| `waninterfacedo` | WAN interface configuration |
| `wannetworkdo` | WAN network definitions |
| `tenantdo` | Tenant configuration |
| `appdefdo` | Application definition library |
| `policyruledo` | Network policy rules |

### AI / Analytics

| Table | Description |
|---|---|
| `an_sdwan_predictions` | AI/ML-generated SD-WAN predictions |
| `capacity_forecast` | WAN capacity forecasts |
| `fc_predictions` | Flow classifier predictions |
| `sdwan_copilot_*` | Copilot RAG knowledge base |
| `data_explore_llm_prompts` | Stored LLM prompt history |

---

## Important query rules

> **All stats tables require a partition filter on `event_time`** (`requirePartitionFilter: true`).  
> Always include: `WHERE DATE(event_time) >= ...` or `event_time >= TIMESTAMP_SUB(...)`.

```sql
-- CORRECT
WHERE tenant_id = '1468'
  AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)

-- WRONG — will fail with partition filter error
WHERE tenant_id = '1468'
```

**Clustering keys** (put these in WHERE for best performance):
- Most stats tables: `tenant_id`, `site_id`, `event_time`
- Always filter by `tenant_id` and `event_time` at minimum

**tenant_id is a STRING** — always quote it: `tenant_id = '1468'` not `tenant_id = 1468`

---

## Common query patterns

### Private IP filter (RFC 1918)
```sql
AND (
  STARTS_WITH(src_ip, '10.') OR
  STARTS_WITH(src_ip, '192.168.') OR
  REGEXP_CONTAINS(src_ip, r'^172\.(1[6-9]|2[0-9]|3[01])\.')
)
```

### Top apps by traffic
```sql
SELECT app_name,
       COUNT(*) AS flow_count,
       SUM(traffic_volume) AS total_bytes
FROM `pa-sase-insights-prod-01.sdwan_dataset.flow_stats_view`
WHERE tenant_id = '<tenant_id>'
  AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY app_name
ORDER BY total_bytes DESC
LIMIT 20
```

### Bandwidth per site per hour
```sql
SELECT site_id, TIMESTAMP_TRUNC(event_time, HOUR) AS hour,
       SUM(bw_bytes) AS total_bytes
FROM `pa-sase-insights-prod-01.sdwan_dataset.agg_bw_stats`
WHERE tenant_id = '<tenant_id>'
  AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
GROUP BY site_id, hour
ORDER BY hour DESC
```

### Recent events for a tenant
```sql
SELECT event_time, severity, type, site_id, description
FROM `pa-sase-insights-prod-01.sdwan_dataset.events`
WHERE tenant_id = '<tenant_id>'
  AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)
ORDER BY event_time DESC
LIMIT 100
```

### List tables in dataset
```bash
TOKEN=$(gcloud auth application-default print-access-token)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://bigquery.googleapis.com/bigquery/v2/projects/pa-sase-insights-prod-01/datasets/sdwan_dataset/tables?maxResults=300" \
  | python3 -c "import sys,json; [print(t['tableReference']['tableId']) for t in json.load(sys.stdin).get('tables',[])]"
```

### Describe table schema
```bash
TOKEN=$(gcloud auth application-default print-access-token)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://bigquery.googleapis.com/bigquery/v2/projects/pa-sase-insights-prod-01/datasets/sdwan_dataset/tables/<TABLE_NAME>" \
  | python3 -c "import sys,json; [print(f['name'],'-',f['type']) for f in json.load(sys.stdin)['schema']['fields']]"
```

---

## Output format

Always present results as:
1. **Row count** returned vs total in BigQuery
2. **Summary tables** grouped by the most relevant dimension (app, site, path, etc.)
3. **Sample rows** (first 10–15) for spot-checking
4. **Key observations** — what stands out, anomalies, dominant traffic patterns

---

## Troubleshooting

| Error | Fix |
|---|---|
| `Request had invalid authentication credentials` | Run `gcloud auth application-default login` again |
| `partitionRequired: partition filter required` | Add `event_time` filter to the WHERE clause |
| `Access Denied` | Your GCP account lacks BigQuery read IAM on this project |
| `totalRows: 0` | Widen the time range or check tenant_id/site_id values |
| `bq: You do not have an active account` | Use the REST API pattern above — don't rely on `bq` CLI |

---

## Pagination for large result sets

BigQuery REST queries return up to 50,000 rows per call. For larger sets:

```python
job_id = data["jobReference"]["jobId"]
page_token = data.get("pageToken")
while page_token:
    url = f"https://bigquery.googleapis.com/bigquery/v2/projects/pa-sase-insights-prod-01/queries/{job_id}?pageToken={page_token}&maxResults=10000"
    # fetch next page...
```
