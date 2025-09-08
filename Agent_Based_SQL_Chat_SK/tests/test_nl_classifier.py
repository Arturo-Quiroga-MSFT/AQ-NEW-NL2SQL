from DB_Assistant.nl.classifier import classify, to_sql
from DB_Assistant.nl.dsl import NLAction, Unknown

CASES = [
    ("list tables", 'list_tables'),
    ("show schema", 'list_tables'),
    ("show schema of db", 'list_tables'),
    ("describe table dim_customer", 'describe_table'),
    ("row count for fact_loans", 'row_count'),
    ("create table staging.pay with columns id int, amount decimal(18,2)", 'create_table'),
    ("add column notes varchar(100) to staging.pay", 'add_column'),
    ("drop column notes from staging.pay", 'drop_column'),
    ("create index on staging.pay(id, created_at)", 'create_index'),
    ("drop table staging.pay", 'drop_table'),
]


def test_rule_intents():
    for text, expected in CASES:
        act = classify(text)
        assert isinstance(act, NLAction), text
        assert act.intent == expected, (text, act.intent, expected)


def test_unknown():
    act = classify("please optimize this database for analytics")
    assert isinstance(act, Unknown)
