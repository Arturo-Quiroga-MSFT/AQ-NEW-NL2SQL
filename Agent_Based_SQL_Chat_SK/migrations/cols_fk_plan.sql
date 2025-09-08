ALTER TABLE fact_loan_payments ADD company_key INT NOT NULL;

ALTER TABLE fact_loan_payments ADD date_key INT NOT NULL;

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='fk_fact_loan_payments_company_key') BEGIN
ALTER TABLE fact_loan_payments ADD CONSTRAINT fk_fact_loan_payments_company_key FOREIGN KEY (company_key) REFERENCES dim_company (company_key);
END

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='fk_fact_loan_payments_date_key') BEGIN
ALTER TABLE fact_loan_payments ADD CONSTRAINT fk_fact_loan_payments_date_key FOREIGN KEY (date_key) REFERENCES dim_date (date_key);
END