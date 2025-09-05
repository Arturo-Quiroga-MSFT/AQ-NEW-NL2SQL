import json
from pathlib import Path
from DB_Assistant.core.schema_models import SchemaSpec, Entities, Dimension, Fact, Column, ForeignKey
from DB_Assistant.core.migration_planner import plan_migration
from DB_Assistant.core.impact_analyzer import analyze_impact
from DB_Assistant.core.ddl_renderer import operations_to_sql


def _spec_with_payment_date():
    dim_company = Dimension(name="dim_company", surrogate_key="company_key", columns=[
        Column(name="company_key", type="INT", nullable=False),
        Column(name="region", type="VARCHAR(40)", nullable=False),
    ])
    dim_date = Dimension(name="dim_date", surrogate_key="date_key", columns=[
        Column(name="date_key", type="INT", nullable=False),
        Column(name="calendar_date", type="DATE", nullable=False),
    ])
    fact = Fact(name="fact_loan_payments", columns=[
        Column(name="loan_id", type="VARCHAR(50)", nullable=False),
        Column(name="payment_date", type="DATE", nullable=False),
        Column(name="company_key", type="INT", nullable=False),
        Column(name="date_key", type="INT", nullable=False),
    ], measures=[
    ], foreign_keys=[
        ForeignKey(column="company_key", references="dim_company(company_key)"),
        ForeignKey(column="date_key", references="dim_date(date_key)"),
    ])
    return SchemaSpec(version=1, warehouse=None, entities=Entities(dimensions=[dim_company, dim_date], facts=[fact]))


def _spec_without_payment_date():
    base = _spec_with_payment_date()
    # remove payment_date
    new_fact_cols = [c for c in base.entities.facts[0].columns if c.name != "payment_date"]
    fact2 = Fact(name="fact_loan_payments", columns=new_fact_cols, measures=[], foreign_keys=base.entities.facts[0].foreign_keys)
    return SchemaSpec(version=1, warehouse=None, entities=Entities(dimensions=base.entities.dimensions, facts=[fact2]))


def test_drop_column_detected_and_high_risk():
    cur = _spec_with_payment_date()
    tgt = _spec_without_payment_date()
    ops = plan_migration(cur, tgt)
    kinds = [o.op for o in ops]
    assert "DROP_COLUMN" in kinds, f"Expected DROP_COLUMN in ops: {kinds}"
    impact = analyze_impact(ops)
    high = [c for c in impact if c["risk"] == "high" and c.get("column") == "payment_date"]
    assert high, f"Expected high risk drop for payment_date, impact={impact}"


def test_alter_widen_varchar_low_risk():
    # current region VARCHAR(40) -> target VARCHAR(60)
    cur = _spec_with_payment_date()
    # Modify region type in target
    dim_company = cur.entities.dimensions[0]
    new_cols = [Column(name="company_key", type="INT", nullable=False), Column(name="region", type="VARCHAR(60)", nullable=False)]
    new_dim = Dimension(name="dim_company", surrogate_key="company_key", columns=new_cols)
    tgt = SchemaSpec(version=1, warehouse=None, entities=Entities(dimensions=[new_dim, cur.entities.dimensions[1]], facts=cur.entities.facts))
    ops = plan_migration(cur, tgt)
    impact = analyze_impact(ops)
    alter = [c for c in impact if c.get("column") == "region" and c.get("op") == "ALTER_COLUMN"]
    assert alter, f"Expected ALTER_COLUMN for region, impact={impact}"
    assert alter[0]["risk"] in ("low","medium"), "Widening should not be high risk"


def test_sql_render_no_errors(tmp_path: Path):
    cur = _spec_with_payment_date()
    tgt = _spec_without_payment_date()
    ops = plan_migration(cur, tgt)
    sql = operations_to_sql(ops)
    assert "DROP COLUMN payment_date" in sql
    # Write to ensure file IO works in test context
    p = tmp_path / "plan.sql"
    p.write_text(sql, encoding="utf-8")
    assert p.exists()
