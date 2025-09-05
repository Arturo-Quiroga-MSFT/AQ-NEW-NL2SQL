ALTER TABLE dim_company ALTER COLUMN region VARCHAR(40) NOT NULL;

ALTER TABLE dim_company ALTER COLUMN industry VARCHAR(60) NULL;

ALTER TABLE fact_loan_payments DROP COLUMN payment_date;

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_fact_loan_payments_company_key' AND object_id = OBJECT_ID('fact_loan_payments')) BEGIN
CREATE INDEX ix_fact_loan_payments_company_key ON fact_loan_payments (company_key);
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_fact_loan_payments_date_key' AND object_id = OBJECT_ID('fact_loan_payments')) BEGIN
CREATE INDEX ix_fact_loan_payments_date_key ON fact_loan_payments (date_key);
END

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='ix_fact_loan_payments_grain' AND object_id = OBJECT_ID('fact_loan_payments')) BEGIN
CREATE INDEX ix_fact_loan_payments_grain ON fact_loan_payments (loan_id, date_key);
END