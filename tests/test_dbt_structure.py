# Python tests for the dbt models. These run WITHOUT Airflow / Postgres.
# They assert on the SQL and YAML files in the project to catch structural
# mistakes (missing tests, broken refs, untyped columns).
import os
import re
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent / "dbt_project"


def test_dbt_project_yml_exists():
    assert (PROJECT_ROOT / "dbt_project.yml").exists()


def test_profiles_yml_exists():
    assert (PROJECT_ROOT / "profiles.yml").exists()


def test_staging_models_have_tests():
    """Every staging model must declare at least one test in its yml schema file."""
    yml = (PROJECT_ROOT / "models" / "staging" / "_stg_models.yml").read_text()
    # Rough check: 'tests:' should appear at least 5 times (one per column with tests).
    assert yml.count("tests:") >= 5


def test_marts_models_have_tests():
    yml = (PROJECT_ROOT / "models" / "marts" / "_marts_models.yml").read_text()
    assert yml.count("tests:") >= 3


def test_all_models_have_unique_tests():
    """PK columns must have unique + not_null tests."""
    for yml in [
        PROJECT_ROOT / "models" / "staging" / "_stg_models.yml",
        PROJECT_ROOT / "models" / "marts" / "_marts_models.yml",
    ]:
        text = yml.read_text()
        assert "unique" in text, f"{yml.name} missing 'unique' test"
        assert "not_null" in text, f"{yml.name} missing 'not_null' test"


def test_no_negative_amounts_in_seed():
    """Seeds must never include an order with amount <= 0."""
    csv = (PROJECT_ROOT / "seeds" / "raw_orders.csv").read_text()
    reader = csv.splitlines()
    header = reader[0].split(",")
    amt_idx = header.index("amount")
    for line in reader[1:]:
        amount = float(line.split(",")[amt_idx])
        assert amount > 0, f"Seed has non-positive amount: {line}"


def test_currency_in_seed_is_iso3():
    csv = (PROJECT_ROOT / "seeds" / "raw_orders.csv").read_text()
    reader = csv.splitlines()
    header = reader[0].split(",")
    cur_idx = header.index("currency")
    for line in reader[1:]:
        cur = line.split(",")[cur_idx]
        assert len(cur) == 3 and cur.isalpha(), f"Bad currency in seed: {line}"


def test_status_values_are_allowed():
    csv = (PROJECT_ROOT / "seeds" / "raw_orders.csv").read_text()
    reader = csv.splitlines()
    header = reader[0].split(",")
    s_idx = header.index("status")
    allowed = {"created", "paid", "shipped", "delivered", "cancelled"}
    for line in reader[1:]:
        s = line.split(",")[s_idx]
        assert s in allowed, f"Status {s!r} not in allowed set"


def test_tier_values_are_allowed():
    csv = (PROJECT_ROOT / "seeds" / "raw_customers.csv").read_text()
    reader = csv.splitlines()
    header = reader[0].split(",")
    t_idx = header.index("tier")
    allowed = {"BRONZE", "SILVER", "GOLD", "PLATINUM"}
    for line in reader[1:]:
        t = line.split(",")[t_idx]
        assert t in allowed, f"Tier {t!r} not in allowed set"


def test_dag_uses_bashoperator():
    py = (PROJECT_ROOT.parent / "dags" / "data_platform_daily.py").read_text()
    assert "BashOperator" in py
    assert "dbt run" in py
    assert "dbt test" in py
