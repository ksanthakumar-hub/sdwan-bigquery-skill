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
| Dataset | `sdwan_dataset` (same name in all regions) |
| Auth | Application Default Credentials (`gcloud`) |
| API | BigQuery REST API v2 |

**Default project:** `pa-sase-insights-prod-01` (US)

### Regional projects

Specify the region in your request: _"use region sg"_ or _"use project pa-sase-insights-sg-prod-01"_

| Region Code | Project ID | Location |
|---|---|---|
| (default) | `pa-sase-insights-prod-01` | United States |
| `ae` | `pa-sase-insights-ae-prod-01` | UAE |
| `au` | `pa-sase-insights-au-prod-01` | Australia |
| `br` | `pa-sase-insights-br-prod-01` | Brazil |
| `ca` | `pa-sase-insights-ca-prod-01` | Canada |
| `ch` | `pa-sase-insights-ch-prod-01` | Switzerland |
| `cn` | `pa-sase-insights-cn-prod-01` | China |
| `de` | `pa-sase-insights-de-prod-01` | Germany |
| `es` | `pa-sase-insights-es-prod-01` | Spain |
| `eu` | `pa-sase-insights-eu-prod-01` | Europe (general) |
| `fr` | `pa-sase-insights-fr-prod-01` | France |
| `id` | `pa-sase-insights-id-prod-01` | Indonesia |
| `il` | `pa-sase-insights-il-prod-01` | Israel |
| `in` | `pa-sase-insights-in-prod-01` | India |
| `it` | `pa-sase-insights-it-prod-01` | Italy |
| `jp` | `pa-sase-insights-jp-prod-01` | Japan |
| `kr` | `pa-sase-insights-kr-prod-01` | South Korea |
| `pl` | `pa-sase-insights-pl-prod-01` | Poland |
| `qa` | `pa-sase-insights-qa-prod-01` | Qatar |
| `sa` | `pa-sase-insights-sa-prod-01` | Saudi Arabia |
| `sg` | `pa-sase-insights-sg-prod-01` | Singapore |
| `tw` | `pa-sase-insights-tw-prod-01` | Taiwan |
| `uk` | `pa-sase-insights-uk-prod-01` | United Kingdom |
| `za` | `pa-sase-insights-za-prod-01` | South Africa |

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

> Total: 286 tables in `sdwan_dataset`. ~130 are customer-useful; the rest are internal ingestion, duplicates, or system-only. Only customer-useful tables are listed below.

### Traffic & Flow Analysis

| Table | Description |
|---|---|
| `flow_stats_view` | Enriched flows — app name, src/dst IP, ports, path, bytes per flow |
| `flow_stats` | Raw flow records |
| `entity_flow_stats_view` | Flow stats scoped to named entities/users |
| `flow_control_stats` | Flow control actions and enforcement |
| `flow_control_active_stats` | Currently active flow control entries |
| `probe_flow_stats` | Probe-based synthetic flow measurements |
| `app_prefix_stats` | Traffic stats broken down by IP prefix + app |

### Application Performance

| Table | Description |
|---|---|
| `app_stats_view` | Enriched per-app traffic (bytes, packets) by site |
| `app_stats_enriched` | App stats with additional context fields |
| `app_stats_site_agg_five_minute_mv` | 5-min aggregated app traffic per site |
| `app_stats_site_agg_hourly_mv` | Hourly aggregated app traffic per site |
| `app_stats_tenant_agg_five_minute_mv` | 5-min aggregated app traffic tenant-wide |
| `app_stats_tenant_agg_hourly_mv` | Hourly aggregated app traffic tenant-wide |
| `app_summary_stats_view` | App-level summary health rollup view |
| `mv_app_stats_topn_tenant_daily` | Daily top-N apps by tenant |
| `mv_app_summary_stats_app_hs_daily` | Daily app health score summary |
| `carrier_app_stats_view` | App stats broken down by WAN carrier |

### Bandwidth & Circuits

| Table | Description |
|---|---|
| `agg_bw_stats` | 5-min aggregated WAN bandwidth per interface (partitioned by `event_time`) |
| `agg_bw_stats_daily` | Daily aggregated WAN bandwidth |
| `bandwidth_stats` | Raw WAN bandwidth utilization |
| `sdwan_circuit_hourly_summary` | Per-circuit hourly utilization summary |
| `sdwan_circuit_daily_summary` | Per-circuit daily utilization summary |
| `carrier_interface_stats_view` | Interface stats grouped by carrier |

### Link Quality (Latency, Loss, Jitter)

| Table | Description |
|---|---|
| `lqm_stats_view` | Link quality metrics — latency, loss, jitter (enriched) |
| `lqm_stats` | Raw LQM stats |
| `synthetic_probe_stats` | Synthetic test results for proactive path quality monitoring |

### Site & Link Health Rollups

> All health tables are sharded 0–4. Query all shards with `UNION ALL` or filter by shard.

| Table | Description |
|---|---|
| `site_health_data_five_min_agg_[0-4]` | Site health score — 5-min buckets |
| `site_health_data_one_hour_agg_[0-4]` | Site health score — hourly rollup |
| `site_health_data_one_day_agg_[0-4]` | Site health score — daily rollup |
| `link_health_data_five_min_agg_[0-4]` | Link health — 5-min buckets |
| `link_health_data_one_hour_agg_[0-4]` | Link health — hourly rollup |
| `link_health_data_one_day_agg_[0-4]` | Link health — daily rollup |
| `app_summary_stats_health_data_five_min_agg_[0-4]` | App health — 5-min buckets |
| `app_summary_stats_health_data_one_hour_agg_[0-4]` | App health — hourly rollup |
| `app_summary_stats_health_data_one_day_agg_[0-4]` | App health — daily rollup |

### Events, Alerts & Incidents

| Table | Description |
|---|---|
| `events` | All SD-WAN events (link up/down, policy change, failover, etc.) |
| `events_count` | Summarized event counts by type/severity |
| `sdwan_alerts_view` | Active alerts |
| `sdwan_incidents_view` | Active incidents with severity and category (filter by `tenant_service_group`, not `tenant_id`) |
| `flatten_site_sdwan_alerts_view` | Alerts flattened per-site (easier to join with sitedo) |
| `flatten_site_sdwan_incidents_view` | Incidents flattened per-site |
| `connection_status` | ION device connectivity status |

### Interface & WAN

| Table | Description |
|---|---|
| `interface_stats_view` | Per-interface traffic and error stats (enriched) |
| `interface_stats_enriched` | Interface stats with additional context |
| `lacp_stats` | LACP bonding stats for LAG interfaces |
| `lldp_stats` | LLDP neighbor discovery data |
| `poe_stats` | PoE power delivery stats |
| `poe_interface_stats` | Per-port PoE stats |
| `stp_stats` | Spanning Tree Protocol stats |
| `stp_interface_stats` | Per-interface STP state |

### VPN & Tunnels

| Table | Description |
|---|---|
| `vpn_summary_stats` | VPN tunnel health and throughput summary |
| `vpn_data_tunnel_stats` | Data plane tunnel statistics |
| `vpn_control_tunnel_stats` | Control plane tunnel statistics |
| `vpn_global_error_stats` | VPN error counters |

### Cellular / Mobile WAN

| Table | Description |
|---|---|
| `cellular_stats` | Cellular modem signal, data rate, carrier stats |
| `cellular_apn_stats` | Per-APN cellular traffic stats |
| `cellular_apn_v6_stats` | IPv6 cellular APN stats |

### Routing

| Table | Description |
|---|---|
| `route_stats` | Route table change events and prefix counts |
| `ospf_stats` | OSPF protocol stats and neighbor state |
| `multicast_stats` | Multicast group membership and forwarding |
| `multicast_route_stats` | Multicast routing table stats |
| `multicast_control_stats` | Multicast control plane events |

### Device Health (ION)

| Table | Description |
|---|---|
| `cpu_stats_view` | ION CPU utilization (enriched) |
| `memory_stats_view` | ION memory utilization (enriched) |
| `disk_stats_view` | Disk I/O and usage |
| `file_system_stats` | Filesystem utilization per partition |
| `temperature_stats_view` | Device temperature readings |
| `ssd_smart_stats` | SSD health (SMART data) |

### Security

| Table | Description |
|---|---|
| `security_policy_stats` | Security policy hit counts per rule |
| `securitypolicyruledo` | Security policy rule configuration |
| `securityzonedo` | Security zone definitions |
| `urlcategorydo` | URL category definitions used in policy |
| `urlcustomcategorydo` | Custom URL categories defined by tenant |
| `radius_stats` | RADIUS authentication stats |
| `radius_client_stats` | Per-client RADIUS stats |

### QoS & Performance Policy

| Table | Description |
|---|---|
| `qos_stats` | QoS queue stats — drops, bytes per traffic class |
| `performance_policy_stats` | Performance policy enforcement stats |

### Configuration & Inventory (DO tables)

| Table | Description |
|---|---|
| `sitedo` | Site list — name, address, coordinates, admin state |
| `elementdo` | ION device inventory — model, SW version, connected state |
| `interfacedo` | Interface config — type, IP, VLAN |
| `waninterfacedo` | WAN interface config — carrier, bandwidth, labels |
| `wannetworkdo` | WAN network definitions |
| `lannetworkdo` | LAN network definitions |
| `appdefdo` | Application definition library |
| `networkpolicyruledo` | Network policy rules |
| `networkpolicysetdo` | Network policy sets |
| `networkpolicysetstackdo` | Network policy stacks |
| `policyruledo` | General policy rules |
| `perfmgmtpolicyruledo` | Performance management policy rules |
| `perfmgmtpolicysetdo` | Performance management policy sets |
| `perfmgmtthresholdprofiledo` | Thresholds for performance alerts |
| `prioritypolicyruledo` | Priority/QoS policy rules |
| `prioritypolicysetdo` | Priority policy sets |
| `serviceendpointdo` | Service endpoint definitions |
| `probeconfigdo` | Probe configuration |
| `anynetlinkdo` | AnyNet link configuration |
| `vpnlinkdo` | VPN link configuration |
| `waninterfacelabeldo` | WAN interface labels |
| `networkcontextdo` | Network context definitions |
| `site_config_view` | Joined site configuration view |
| `entity_sitedo_view` | Entity-to-site mapping |
| `auditlogdo` | Audit log — who changed what and when |
| `eventcorrelationpolicyruledo` | Event correlation rules |
| `tenantlicenseskudo` | License SKU allocation per tenant |
| `prismaaccessconfigdo` | Prisma Access integration config |
| `sdwanappconfigdo` | SD-WAN app-specific config |
| `elementimagedo` | Available ION software images |
| `saseconnectiondo` | SASE connection config |
| `extensiondo` | Extension/plugin configuration |

### AI, Analytics & Forecasting

| Table | Description |
|---|---|
| `an_sdwan_predictions` | AI-generated predictions (path degradation, outage risk) |
| `capacity_forecast` | WAN capacity forecasts per circuit |
| `aiops_cp_stats` | AIOps capacity planning metrics |
| `topology_counts` | Network topology element counts over time |

### Tables to Exclude (Internal / Not Customer-Facing)

| Pattern | Reason |
|---|---|
| `i_*` (~35 tables) | Internal ingestion pipeline staging tables |
| `*_csv` tables | CSV export duplicates of DO tables |
| `*_n` tables (`sitedo_n`, `elementdo_n`, etc.) | Normalized internal copies |
| `datamigration_failed_records`, `failed_records` | Internal ETL error logs |
| `machine_tenant_mapping`, `machinedo` | Internal infrastructure mapping |
| `tenant_shard_map` | Internal sharding configuration |
| `sdwan_copilot_*` | Internal RAG knowledge base for Copilot AI |
| `sdwan_troubleshooting_agent_spans` | Internal AI agent tracing |
| `data_explore_llm_prompts` | Internal LLM prompt history |
| `fc_hyperparameters`, `fc_metrics`, `fc_predictions` | Internal ML model data |
| `timezones` | Internal reference table |
| `manual_data_lookup` | Internal ops lookup |
| `sdwan_flowcount_limits` | Internal capacity enforcement |
| `tenantdo` | Multi-tenant directory — use ONLY as a filter source (JOIN or subquery) to exclude internal/inactive tenants. Never SELECT * or return raw rows from it — it exposes all tenant metadata. |
| `copilot_request_details` | Internal Copilot telemetry |
| `deviceidconfigdo`, `deviceidipmappingdo` | Internal device identity mapping |
| `threattenantversiondo` | Internal threat profile versioning |

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

### Excluding internal tenants (REQUIRED for all fleet-wide queries)

**Never include internal/support tenants** (`tenant_type = 'INTERNAL'`) in any fleet-wide analysis, dashboards, or aggregations. Internal tenants are Palo Alto Networks lab, demo, QA, and CS accounts — including them skews counts and leaks internal infrastructure into customer-facing reports.

`tenantdo` fields that identify non-customer accounts:
- `tenant_type = 'INTERNAL'` — PA Networks internal accounts (labs, CS, QA, demo)
- `is_support = TRUE` — support/TAC access tenants
- `inactive = TRUE` — deactivated tenants (exclude from active fleet counts)
- `disabled = TRUE` — administratively disabled tenants

**Pattern A — exclude when joining `tenantdo` (preferred for fleet-wide queries):**
```sql
FROM `pa-sase-insights-prod-01.sdwan_dataset.elementdo` e
JOIN `pa-sase-insights-prod-01.sdwan_dataset.tenantdo` t
  ON e.tenant_id = t.tenant_id
WHERE t.tenant_type != 'INTERNAL'
  AND t.is_support = FALSE
  AND t.inactive = FALSE
  AND t.disabled = FALSE
```

**Pattern B — subquery exclusion (for stats tables without a tenantdo join):**
```sql
WHERE tenant_id NOT IN (
  SELECT tenant_id
  FROM `pa-sase-insights-prod-01.sdwan_dataset.tenantdo`
  WHERE tenant_type = 'INTERNAL'
     OR is_support = TRUE
     OR inactive = TRUE
     OR disabled = TRUE
)
AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 24 HOUR)
```

> If the user explicitly asks for internal tenants (e.g. "show me the QA tenant") you may query them — but note in your response that they are internal accounts.

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
