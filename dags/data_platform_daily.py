"""
DAG: data_platform_daily
========================
Orchestrates the dbt transformations for the data platform:
  1. dbt seed      (load reference data from CSV)
  2. dbt run       (build staging views + marts tables)
  3. dbt test      (data quality checks)
  4. dbt source freshness (optional, runs dbt source freshness)

Schedule: daily at 02:00 UTC.

The DAG is intentionally simple — for a production setup you'd add:
  - SLA monitoring
  - Failure callbacks (PagerDuty / Slack)
  - Conditional branching on test failure
  - Multiple EL jobs upstream (Kafka -> raw ingestion)
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator


DBT_PROJECT_DIR = "/opt/dbt/dbt_project"
DBT_PROFILES_DIR = "/opt/dbt/dbt_project"

default_args = {
    "owner": "data-platform",
    "depends_on_past": False,
    "start_date": datetime(2024, 1, 1),
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    "execution_timeout": timedelta(hours=1),
}

with DAG(
    dag_id="data_platform_daily",
    default_args=default_args,
    description="Run dbt transformations and tests for the data platform",
    schedule_interval="0 2 * * *",
    catchup=False,
    tags=["dbt", "data-platform", "data-mesh"],
) as dag:

    dbt_deps = BashOperator(
        task_id="dbt_deps",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt deps --profiles-dir {DBT_PROFILES_DIR}",
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt seed --profiles-dir {DBT_PROFILES_DIR}",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt run --profiles-dir {DBT_PROFILES_DIR}",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_PROJECT_DIR} && dbt test --profiles-dir {DBT_PROFILES_DIR}",
    )

    def publish_run_results(**context):
        """Optional: push dbt artifacts (run_results.json) to a metadata store."""
        import json
        import pathlib
        results_path = pathlib.Path(DBT_PROJECT_DIR) / "target" / "run_results.json"
        if results_path.exists():
            with open(results_path) as f:
                results = json.load(f)
            # In prod: publish to DataHub, Marquez, or a Slack webhook.
            print(f"dbt run completed: {len(results.get('results', []))} models executed")

    publish = PythonOperator(
        task_id="publish_run_results",
        python_callable=publish_run_results,
    )

    # DAG ordering
    dbt_deps >> dbt_seed >> dbt_run >> dbt_test >> publish
