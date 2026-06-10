# dbt-airflow-data-platform

End-to-end **dbt + Airflow + Postgres** data platform, demonstrating the second JD for the **Data Engineer** role.

## Why this project?

| JD requirement | Where |
|---|---|
| ETL Data Pipelines | dbt models in `dbt_project/models/` |
| Python for Data Engineering | Airflow DAG, dbt tests |
| Data Mesh Architecture | Schemas per domain (`staging`, `marts`) |
| Advanced PostgreSQL | Window functions, CTEs, joins, accepted_values tests in `fct_orders`, `daily_revenue_by_tier`, `top_customers` |
| dbt | All models + tests + macros + seeds |
| Airflow | `dags/data_platform_daily.py` |
| Data Quality Frameworks | dbt tests + singular tests + accepted_values + relationships |
| AWS | Use Postgres in dev; production would be Redshift/Snowflake/BigQuery — see sibling `flink-data-mesh-pipeline` for the streaming counterpart |

## Project layout

```
dbt-airflow-data-platform/
├── dbt_project/
│   ├── dbt_project.yml         # project config (paths, materializations)
│   ├── profiles.yml            # connection to Postgres
│   ├── models/
│   │   ├── staging/
│   │   │   ├── _sources.yml         # raw.orders, raw.customers
│   │   │   ├── _stg_models.yml      # tests for staging models
│   │   │   ├── stg_orders.sql
│   │   │   └── stg_customers.sql
│   │   └── marts/
│   │       ├── _marts_models.yml
│   │       ├── fct_orders.sql       # enriched fact table
│   │       ├── daily_revenue_by_tier.sql
│   │       └── top_customers.sql
│   ├── macros/cents_to_dollars.sql
│   ├── seeds/
│   │   ├── raw_orders.csv
│   │   └── raw_customers.csv
│   └── tests/
│       ├── assert_fct_orders_amount_positive.sql
│       └── assert_revenue_non_negative.sql
├── dags/
│   └── data_platform_daily.py   # Airflow DAG: deps -> seed -> run -> test -> publish
├── tests/                       # Python tests for project structure
├── init/01_schemas.sql
├── docker-compose.yml           # Postgres + Airflow + dbt
└── README.md
```

## How to run (full E2E with Docker)

```bash
docker-compose up -d postgres
docker-compose run --rm dbt         # runs dbt deps + seed + run + test

# In another shell:
docker-compose up -d airflow-init webserver scheduler
# Open http://localhost:8080 (admin/admin) and trigger the DAG manually
```

## How to run (local dbt only)

```bash
pip install dbt-postgres
cd dbt_project
dbt seed --profiles-dir .
dbt run --profiles-dir .
dbt test --profiles-dir .
```

## How to test (no infrastructure needed)

```bash
python3 -m pytest tests/ -v
```

The Python tests inspect the SQL/YAML files directly, validating:
- Project structure
- That all models declare tests
- That seed data conforms to contracts (positive amounts, ISO-3 currency, valid statuses/tiers)
- That the DAG is wired correctly

## dbt tests included

| Test type | Where | What it catches |
|---|---|---|
| `not_null` | staging PKs, FKs, statuses | NULL primary keys, NULL statuses |
| `unique` | order_id, customer_id | Duplicate records |
| `accepted_values` | currency, status, tier | Bad enum values |
| `relationships` | orders → customers | Orphaned orders |
| Singular (custom) | `assert_fct_orders_amount_positive.sql` | Negative amounts in fact table |
| Singular (custom) | `assert_revenue_non_negative.sql` | Negative revenue in marts |

## See also

- `flink-data-mesh-pipeline` — streaming counterpart with Kafka + Flink
- `akka-scala-base` — Scala/Akka (Senior Software Engineer role)
- `scala-akka-aws-microservice` — AWS deploy (Senior Software Engineer role)
