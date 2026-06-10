# dbt-airflow-data-platform — Visão geral e fluxo

Plataforma de dados end-to-end **dbt + Airflow + Postgres**. ETL pipelines, Python, Data Mesh (schemas por domínio), Postgres avançado, dbt, Airflow, Data Quality Frameworks.

## Stack (com versões)

- **dbt-postgres 1.7.4** (dbt core + adapter Postgres)
- **Apache Airflow 2.9.0** (imagem `apache/airflow:2.9.0-python3.11`)
- **PostgreSQL 15** (metadata do Airflow + warehouse do dbt)
- **Python 3.11** (Airflow + container dbt `python:3.11-slim`)
- **Docker Compose 3.9** para orquestração local
- **psycopg2** (driver de conexão Airflow ↔ Postgres)
- **pytest** (testes Python de estrutura, em `tests/test_dbt_structure.py`)

---

## Fluxo principal

### 1. Arquitetura
- **Postgres** (porta 5432) — atua como **metadata DB do Airflow** e como **warehouse do dbt** (schemas `staging` e `marts`).
- **Airflow** (webserver :8080, scheduler) — orquestra o pipeline.
- **dbt** — roda dentro do container `dbt`, transformando dados.

### 2. DAG Airflow (`dags/data_platform_daily.py`)
- `dag_id="data_platform_daily"`, `schedule_interval="0 2 * * *"` (02:00 UTC diariamente), `catchup=False`, `retries=2`, `retry_delay=5min`, `execution_timeout=1h`.
- Tasks (BashOperator para dbt + PythonOperator para publish):
  1. **`dbt_deps`** — `dbt deps --no-version-check`
  2. **`dbt_seed`** — `dbt seed` (carrega CSVs de `dbt_project/seeds/`)
  3. **`dbt_run`** — `dbt run` (cria views em `staging` e tables em `marts`)
  4. **`dbt_test`** — `dbt test` (not_null, unique, accepted_values, relationships, singulares)
  5. **`publish_run_results`** — `PythonOperator` que lê `target/run_results.json` e loga o número de modelos executados (em prod: publicar em DataHub/Marquez/Slack).
- Ordenação: `dbt_deps >> dbt_seed >> dbt_run >> dbt_test >> publish`.

### 3. Projeto dbt (`dbt_project/dbt_project.yml`)
- `name: 'data_platform'`, `version: '1.0.0'`, `profile: 'data_platform'`.
- Materializations:
  - `staging` → **view** + `+schema: staging`.
  - `marts` → **table** + `+schema: marts`.
- `target-path: "../target"` (escreve fora do projeto dbt).

### 4. Conexão (`dbt_project/profiles.yml`)
- Targets `dev` (localhost, threads 4) e `prod` (host `postgres`, threads 8) — Postgres driver, env vars para host/port/user/password/db.

### 5. Models
- **Staging** (views, leitura crua):
  - `stg_orders` (de `raw.orders`) — orders tipadas.
  - `stg_customers` (de `raw.customers`) — customers tipados.
  - `_sources.yml` declara `raw.orders` e `raw.customers`.
  - `_stg_models.yml` aplica testes: `not_null` em PKs, FKs, status; `unique` em order_id/customer_id; `accepted_values` em currency/status; `relationships` orders → customers.
- **Marts** (tables, materializadas):
  - `fct_orders` — fact table "wide" de order × customer (CTE + `left join`).
  - `daily_revenue_by_tier` — agregação diária por tier (window function `date_trunc`, `group by 1, 2`, filtra status pagos).
  - `top_customers` — top customers.
  - `_marts_models.yml` — testes de mart.

### 6. Macros e tests
- `macros/cents_to_dollars.sql` — macro de conversão monetária.
- `tests/`:
  - `assert_fct_orders_amount_positive.sql` — singular: `amount > 0` na fact table.
  - `assert_revenue_non_negative.sql` — singular: revenue não-negativa.

### 7. Seeds
- `seeds/raw_orders.csv` e `seeds/raw_customers.csv` — dados de referência carregados por `dbt seed`.

### 8. Init do Postgres
- `init/01_schemas.sql` — DDL inicial (schemas `staging`, `marts`, etc.) executado no primeiro start do Postgres.

### 9. Data Quality Frameworks
- `not_null`, `unique`, `accepted_values`, `relationships` (genéricos dbt).
- Singulares custom em `tests/`.
- Testes pytest em `tests/test_dbt_structure.py` que **inspecionam os arquivos SQL/YAML diretamente** (sem precisar de DB) e validam: estrutura do projeto, que todos os models declaram tests, que seeds cumprem contratos (amount > 0, currency ISO-3, status/tier válidos), e que o DAG está cabeado.

### 10. Data Mesh
- Schemas por domínio (`staging`, `marts`) seguindo o padrão de isolamento lógico do Data Mesh; cada camada tem owner claro (staging = dados crus tipados; marts = produtos de dados para BI).

---

## O que tem em cada subpasta

### Raiz
- `README.md` — quickstart, lista de testes dbt.
- `docker-compose.yml` — Postgres 15, Airflow 2.9.0 (webserver, scheduler, init), dbt (Python 3.11 slim).
- `.gitignore`, `.connection-test`.

### `dags/`
- `data_platform_daily.py` — DAG Airflow (5 tasks: `dbt_deps >> dbt_seed >> dbt_run >> dbt_test >> publish_run_results`).

### `dbt_project/`
- `dbt_project.yml` — config do projeto (paths, materializations, schemas).
- `profiles.yml` — perfis `dev` e `prod` (Postgres).

### `dbt_project/models/staging/`
- `_sources.yml` — fontes `raw.orders`, `raw.customers`.
- `_stg_models.yml` — schema + testes de staging.
- `stg_orders.sql` — view de orders tipadas.
- `stg_customers.sql` — view de customers tipados.

### `dbt_project/models/marts/`
- `_marts_models.yml` — schema + testes de marts.
- `fct_orders.sql` — fact table (orders + customers via `left join`).
- `daily_revenue_by_tier.sql` — agregação diária com `date_trunc`, `group by`, filtro de status.
- `top_customers.sql` — ranking de top customers.

### `dbt_project/macros/`
- `cents_to_dollars.sql` — macro de conversão monetária.

### `dbt_project/seeds/`
- `raw_orders.csv`, `raw_customers.csv` — dados de referência.

### `dbt_project/tests/`
- `assert_fct_orders_amount_positive.sql` — singular: `amount > 0` em `fct_orders`.
- `assert_revenue_non_negative.sql` — singular: revenue não-negativa nos marts.

### `init/`
- `01_schemas.sql` — DDL inicial (criação dos schemas `staging`/`marts` no primeiro start do Postgres).

### `tests/` (Python)
- `test_dbt_structure.py` — pytest que valida estrutura, declaração de tests, conformidade de seeds e wiring do DAG **sem precisar de DB**.

---

## Como rodar

### E2E com Docker
```bash
docker-compose up -d postgres
docker-compose run --rm dbt   # deps + seed + run + test

docker-compose up -d airflow-init webserver scheduler
# Abre http://localhost:8080 (admin/admin) e dispara a DAG manualmente
```

### Só dbt local
```bash
pip install dbt-postgres
cd dbt_project
dbt seed --profiles-dir .
dbt run  --profiles-dir .
dbt test --profiles-dir .
```

### Testes Python (sem infra)
```bash
python3 -m pytest tests/ -v
```

## dbt tests aplicados

| Tipo | Onde | O que pega |
|---|---|---|
| `not_null` | PKs, FKs, status em staging | NULLs em chaves/status |
| `unique` | `order_id`, `customer_id` | Duplicatas |
| `accepted_values` | currency, status, tier | Enums inválidos |
| `relationships` | orders → customers | Pedidos órfãos |
| Singular | `assert_fct_orders_amount_positive.sql` | Amount negativo na fact |
| Singular | `assert_revenue_non_negative.sql` | Revenue negativa nos marts |
