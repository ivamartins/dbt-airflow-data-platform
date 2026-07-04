# dbt-airflow-data-platform

> Part of the **Code Solutions Data Platform Foundation** product line. End-to-end data pipeline: Airflow orchestrates dbt (seed → run → test → publish) against Postgres, with Pydantic contracts and Data Quality built in.

Production-ready data platform: **Airflow** orchestrates **dbt** against **PostgreSQL**, with staging/marts models, Pydantic contracts, generic + singular tests, and **Data Mesh by schema**.

## Why this base

- **Airflow + dbt** — the modern data stack combo, working out of the box
- **Pydantic contracts** for type-safe schemas shared between producers and consumers
- **Data Quality built in** — generic + singular tests on every model
- **Data Mesh by schema** — each data product is its own Postgres schema, owned independently
- **CI-friendly** — clean separation of seed → run → test → publish

## Quick start

**Prerequisites:** Python 3.10+, Docker (for Postgres + Airflow).

```bash
# 1) Start Postgres + Airflow
docker compose up -d

# 2) Trigger the DAG
airflow dags trigger dbt_data_platform

# Or run dbt directly
cd dbt
dbt seed
dbt run
dbt test
```

## Architecture

```
Producers (apps) → Postgres schemas (orders, customers, etc.) → dbt models (staging, marts) → Analytics consumers
                                          ↑
                                  Airflow orchestrator
```

Each domain owns its own Postgres schema (Data Mesh by schema). dbt builds staging and marts models, with Pydantic contracts to validate the shape.

## Run the tests

```bash
# dbt tests (data quality)
cd dbt
dbt test

# Python tests (Pydantic contracts)
pytest tests/
```

## Extend for real use

- Add your own data products (one Postgres schema per team)
- Add new Pydantic contracts to validate event payloads
- Add dbt snapshots for slowly-changing dimensions
- Add dbt exposures to document downstream consumers
- Wire to your orchestrator (Airflow, Dagster, Prefect)

## Tech stack

- Python 3.10+
- Apache Airflow 2.x
- dbt Core + dbt-postgres
- PostgreSQL 14+
- Pydantic 2.x
- pytest (Python tests)

> **Português?** Veja [`README.pt-BR.md`](./README.pt-BR.md).

## See also

- **Product line**: [Data Platform Foundation](https://ivamartins.github.io/code-solutions-site/#produtos)
- **Code Solutions on LinkedIn**: [linkedin.com/company/code-solutions-it](https://www.linkedin.com/company/code-solutions-it/)
- **All Code Solutions open source**: [github.com/ivamartins](https://github.com/ivamartins)

## License

MIT — see `LICENSE`.
