# dbt-airflow-data-platform — Overview & flow

End-to-end **dbt + Airflow + Postgres** data platform. ETL pipelines, Python, Data Mesh (schemas per domain), advanced PostgreSQL, dbt, Airflow, Data Quality Frameworks.

## Stack (with versions)

- **dbt-postgres 1.7.4** (dbt core + Postgres adapter)
- **Apache Airflow 2.9.0** (image `apache/airflow:2.9.0-python3.11`)
- **PostgreSQL 15** (Airflow metadata + dbt warehouse)
- **Python 3.11** (Airflow + dbt container `python:3.11-slim`)
- **Docker Compose 3.9** for local orchestration
- **psycopg2** (Airflow ↔ Postgres connection driver)
- **pytest** (Python structure tests, in `tests/test_dbt_structure.py`)

---

## Main flow

### 1. Architecture
- **Postgres** (port 5432) — acts as **Airflow metadata DB** and as **dbt warehouse** (`staging` and `marts` schemas).
- **Airflow** (webserver :8080, scheduler) — orchestrates the pipeline.
- **dbt** — runs inside the `dbt` container, transforming data.

### 2. Airflow DAG (`dags/data_platform_daily.py`)
- `dag_id="data_platform_daily"`, `schedule_interval="0 2 * * *"` (02:00 UTC daily), `catchup=False`, `retries=2`, `retry_delay=5min`, `execution_timeout=1h`.
- Tasks (BashOperator for dbt + PythonOperator for publish):
  1. **`dbt_deps`** — `dbt deps --no-version-check`
  2. **`dbt_seed`** — `dbt seed` (loads CSVs from `dbt_project/seeds/`)
  3. **`dbt_run`** — `dbt run` (creates views in `staging` and tables in `marts`)
  4. **`dbt_test`** — `dbt test` (not_null, unique, accepted_values, relationships, singular)
  5. **`publish_run_results`** — `PythonOperator` that reads `target/run_results.json` and logs the number of models executed (in prod: publish to DataHub/Marquez/Slack).
- Ordering: `dbt_deps >> dbt_seed >> dbt_run >> dbt_test >> publish`.

### 3. dbt project (`dbt_project/dbt_project.yml`)
- `name: 'data_platform'`, `version: '1.0.0'`, `profile: 'data_platform'`.
- Materializations:
  - `staging` → **view** + `+schema: staging`.
  - `marts` → **table** + `+schema: marts`.
- `target-path: "../target"` (writes outside the dbt project).

### 4. Connection (`dbt_project/profiles.yml`)
- Targets `dev` (localhost, threads 4) and `prod` (host `postgres`, threads 8) — Postgres driver, env vars for host/port/user/password/db.

### 5. Models
- **Staging** (views, raw reading):
  - `stg_orders` (from `raw.orders`) — typed orders.
  - `stg_customers` (from `raw.customers`) — typed customers.
  - `_sources.yml` declares `raw.orders` and `raw.customers`.
  - `_stg_models.yml` applies tests: `not_null` on PKs, FKs, status; `unique` on order_id/customer_id; `accepted_values` on currency/status; `relationships` orders → customers.
- **Marts** (tables, materialized):
  - `fct_orders` — "wide" fact table of order × customer (CTE + `left join`).
  - `daily_revenue_by_tier` — daily aggregation by tier (window function `date_trunc`, `group by 1, 2`, filters paid statuses).
  - `top_customers` — top customers.
  - `_marts_models.yml` — mart tests.

### 6. Macros and tests
- `macros/cents_to_dollars.sql` — currency conversion macro.
- `tests/`:
  - `assert_fct_orders_amount_positive.sql` — singular: `amount > 0` in the fact table.
  - `assert_revenue_non_negative.sql` — singular: non-negative revenue.

### 7. Seeds
- `seeds/raw_orders.csv` and `seeds/raw_customers.csv` — reference data loaded by `dbt seed`.

### 8. Postgres init
- `init/01_schemas.sql` — initial DDL (schemas `staging`, `marts`, etc.) executed on the first start of Postgres.

### 9. Data Quality Frameworks
- `not_null`, `unique`, `accepted_values`, `relationships` (generic dbt).
- Custom singular tests in `tests/`.
- pytest tests in `tests/test_dbt_structure.py` that **inspect SQL/YAML files directly** (no DB needed) and validate: project structure, that all models declare tests, that seeds conform to contracts (amount > 0, ISO-3 currency, valid statuses/tiers), and that the DAG is wired correctly.

### 10. Data Mesh
- Schemas per domain (`staging`, `marts`) following the Data Mesh logical isolation pattern; each layer has a clear owner (staging = typed raw data; marts = data products for BI).

---

## What's in each subfolder

### Root
- `README.md` — quickstart, list of dbt tests.
- `docker-compose.yml` — Postgres 15, Airflow 2.9.0 (webserver, scheduler, init), dbt (Python 3.11 slim).
- `.gitignore`, `.connection-test`.

### `dags/`
- `data_platform_daily.py` — Airflow DAG (5 tasks: `dbt_deps >> dbt_seed >> dbt_run >> dbt_test >> publish_run_results`).

### `dbt_project/`
- `dbt_project.yml` — project config (paths, materializations, schemas).
- `profiles.yml` — profiles `dev` and `prod` (Postgres).

### `dbt_project/models/staging/`
- `_sources.yml` — sources `raw.orders`, `raw.customers`.
- `_stg_models.yml` — schema + staging tests.
- `stg_orders.sql` — typed orders view.
- `stg_customers.sql` — typed customers view.

### `dbt_project/models/marts/`
- `_marts_models.yml` — schema + mart tests.
- `fct_orders.sql` — fact table (orders + customers via `left join`).
- `daily_revenue_by_tier.sql` — daily aggregation with `date_trunc`, `group by`, status filter.
- `top_customers.sql` — top customers ranking.

### `dbt_project/macros/`
- `cents_to_dollars.sql` — currency conversion macro.

### `dbt_project/seeds/`
- `raw_orders.csv`, `raw_customers.csv` — reference data.

### `dbt_project/tests/`
- `assert_fct_orders_amount_positive.sql` — singular: `amount > 0` in `fct_orders`.
- `assert_revenue_non_negative.sql` — singular: non-negative revenue in marts.

### `init/`
- `01_schemas.sql` — initial DDL (creates `staging`/`marts` schemas on the first start of Postgres).

### `tests/` (Python)
- `test_dbt_structure.py` — pytest that validates structure, test declaration, seed contract compliance and DAG wiring **without needing a DB**.

---

## How to run

### E2E with Docker
```bash
docker-compose up -d postgres
docker-compose run --rm dbt   # deps + seed + run + test

docker-compose up -d airflow-init webserver scheduler
# Open http://localhost:8080 (admin/admin) and trigger the DAG manually
```

### Local dbt only
```bash
pip install dbt-postgres
cd dbt_project
dbt seed --profiles-dir .
dbt run  --profiles-dir .
dbt test --profiles-dir .
```

### Python tests (no infra)
```bash
python3 -m pytest tests/ -v
```

## dbt tests applied

| Type | Where | What it catches |
|---|---|---|
| `not_null` | PKs, FKs, status in staging | NULLs in keys/status |
| `unique` | `order_id`, `customer_id` | Duplicates |
| `accepted_values` | currency, status, tier | Invalid enums |
| `relationships` | orders → customers | Orphaned orders |
| Singular | `assert_fct_orders_amount_positive.sql` | Negative amount in fact |
| Singular | `assert_revenue_non_negative.sql` | Negative revenue in marts |
