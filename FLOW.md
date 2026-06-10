# Class interaction flow — dbt-airflow-data-platform

Quick visualization of how data enters, is transformed and validated, from the Airflow DAG down to the final dbt models.

## 1. DAG trigger (daily at 02:00 UTC)

```
Airflow Scheduler
  └─> DAG "data_platform_daily"          [dags/data_platform_daily.py]
        └─> dbt_deps  ──> dbt_seed  ──> dbt_run  ──> dbt_test  ──> publish_run_results
        (chaining: dbt_deps >> dbt_seed >> dbt_run >> dbt_test >> publish)
```

## 2. `dbt_seed` — load reference data

```
seeds/raw_orders.csv
seeds/raw_customers.csv
  └─> dbt seed ──> tables `raw.orders`, `raw.customers` (in Postgres public schema)
```

## 3. `dbt_run` — dbt transformations (internal dbt DAG)

```
raw.orders  + raw.customers  (declared in _sources.yml)
  │
  ├─> stg_orders.sql          (view, schema=staging)   ──> typed SELECT + casts
  ├─> stg_customers.sql       (view, schema=staging)   ──> typed SELECT + casts
  │
  └─> (stg_orders + stg_customers) ──> ref() ──>
        ├─> fct_orders.sql              (table, schema=marts)  ──> wide fact table (order × customer)
        ├─> daily_revenue_by_tier.sql   (table, schema=marts)  ──> daily aggregation
        └─> top_customers.sql           (table, schema=marts)  ──> ranking
```

**Summary path (dbt DAG):**
`raw → stg_orders + stg_customers → fct_orders → (daily_revenue_by_tier + top_customers)`

## 4. `dbt_test` — validation

```
Each model has _models.yml declaring tests:
  ├─> not_null      (PKs, FKs, status)
  ├─> unique        (order_id, customer_id)
  ├─> accepted_values (currency, status, tier)
  └─> relationships (orders → customers)

Singular tests (custom SQL in tests/):
  ├─> assert_fct_orders_amount_positive.sql
  └─> assert_revenue_non_negative.sql
```

If any test fails, the `dbt_test` task fails → DAG fails → alert.

## 5. `publish_run_results` (PythonOperator)

```
publishes target/run_results.json
  └─> log: "dbt run completed: N models executed"
        (in prod: would send to DataHub/Marquez/Slack)
```

## 6. Python tests (no DB needed)

```
pytest tests/test_dbt_structure.py
  └─> inspects SQL/YAML files directly:
        ├─> project structure
        ├─> test declaration in all models
        ├─> seed contract compliance (amount > 0, ISO-3 currency, valid status/tier)
        └─> correct DAG wiring
```

## Folder map (dbt)

```
dbt_project/
├── dbt_project.yml        ← config (paths, materializations, schemas)
├── profiles.yml           ← dev/prod connections
├── models/
│   ├── staging/           ← views (1:1 with raw)
│   │   ├── _sources.yml
│   │   ├── _stg_models.yml
│   │   ├── stg_orders.sql
│   │   └── stg_customers.sql
│   └── marts/             ← tables (aggregates, facts)
│       ├── _marts_models.yml
│       ├── fct_orders.sql
│       ├── daily_revenue_by_tier.sql
│       └── top_customers.sql
├── macros/
│   └── cents_to_dollars.sql
├── seeds/
│   ├── raw_orders.csv
│   └── raw_customers.csv
└── tests/
    ├── assert_fct_orders_amount_positive.sql
    └── assert_revenue_non_negative.sql
```

## Repo map

```
dbt-airflow-data-platform/
├── dags/
│   └── data_platform_daily.py        ← Airflow DAG (5 tasks)
├── dbt_project/                       ← dbt project (see above)
├── init/
│   └── 01_schemas.sql                 ← Postgres initial DDL
├── tests/
│   └── test_dbt_structure.py          ← pytest (no DB)
├── docker-compose.yml                 ← Postgres + Airflow + dbt
└── README.md
```

## Errors

- **dbt_test failing** → DAG fails → Airflow alert.
- **DAG failing** → Airflow will retry 2x with a 5-min delay; after 2 failures, a failure callback (to be added in prod).
- **Singular test failing** → `dbt test` fails with the query of the test that returned rows (data quality breach).
