# Fluxo de interação entre classes — dbt-airflow-data-platform

Visualização rápida de como o dado entra, é transformado e validado, da DAG do Airflow até os modelos finais do dbt.

## 1. Trigger da DAG (diariamente 02:00 UTC)

```
Airflow Scheduler
  └─> DAG "data_platform_daily"          [dags/data_platform_daily.py]
        └─> dbt_deps  ──> dbt_seed  ──> dbt_run  ──> dbt_test  ──> publish_run_results
        (encadeamento: dbt_deps >> dbt_seed >> dbt_run >> dbt_test >> publish)
```

## 2. `dbt_seed` — carregar dados de referência

```
seeds/raw_orders.csv
seeds/raw_customers.csv
  └─> dbt seed ──> tabelas `raw.orders`, `raw.customers` (no schema public do Postgres)
```

## 3. `dbt_run` — transformações dbt (DAG interna do dbt)

```
raw.orders  + raw.customers  (declarados em _sources.yml)
  │
  ├─> stg_orders.sql          (view, schema=staging)   ──> SELECT tipado + casts
  ├─> stg_customers.sql       (view, schema=staging)   ──> SELECT tipado + casts
  │
  └─> (stg_orders + stg_customers) ──> ref() ──>
        ├─> fct_orders.sql              (table, schema=marts)  ──> fact table wide (order × customer)
        ├─> daily_revenue_by_tier.sql   (table, schema=marts)  ──> agregação diária
        └─> top_customers.sql           (table, schema=marts)  ──> ranking
```

**Caminho resumido (dbt DAG):**
`raw → stg_orders + stg_customers → fct_orders → (daily_revenue_by_tier + top_customers)`

## 4. `dbt_test` — validação

```
Cada model tem _models.yml declarando tests:
  ├─> not_null      (PKs, FKs, status)
  ├─> unique        (order_id, customer_id)
  ├─> accepted_values (currency, status, tier)
  └─> relationships (orders → customers)

Singular tests (SQL custom em tests/):
  ├─> assert_fct_orders_amount_positive.sql
  └─> assert_revenue_non_negative.sql
```

Se qualquer teste falhar, a task `dbt_test` falha → DAG falha → alerta.

## 5. `publish_run_results` (PythonOperator)

```
publica target/run_results.json
  └─> log: "dbt run completed: N models executed"
        (em prod: enviaria para DataHub/Marquez/Slack)
```

## 6. Testes Python (sem precisar de DB)

```
pytest tests/test_dbt_structure.py
  └─> inspeciona arquivos SQL/YAML diretamente:
        ├─> estrutura do projeto
        ├─> declaração de tests em todos os models
        ├─> conformidade dos seeds (amount > 0, currency ISO-3, status/tier)
        └─> wiring correto da DAG
```

## Mapa de pastas (dbt)

```
dbt_project/
├── dbt_project.yml        ← config (paths, materializations, schemas)
├── profiles.yml           ← conexões dev/prod
├── models/
│   ├── staging/           ← views (1:1 com raw)
│   │   ├── _sources.yml
│   │   ├── _stg_models.yml
│   │   ├── stg_orders.sql
│   │   └── stg_customers.sql
│   └── marts/             ← tables (agregados, facts)
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

## Mapa geral do repo

```
dbt-airflow-data-platform/
├── dags/
│   └── data_platform_daily.py        ← DAG Airflow (5 tasks)
├── dbt_project/                       ← projeto dbt (ver acima)
├── init/
│   └── 01_schemas.sql                 ← DDL inicial Postgres
├── tests/
│   └── test_dbt_structure.py          ← pytest (sem DB)
├── docker-compose.yml                 ← Postgres + Airflow + dbt
└── README.md
```

## Erros

- **dbt_test falhando** → DAG falha → alerta Airflow.
- **DAG falhando** → o Airflow retentará 2x com delay de 5 min; após 2 falhas, callback de falha (a ser adicionado em prod).
- **Singular test falhando** → `dbt test` falha com a query do test que retornou linhas (data quality breach).
