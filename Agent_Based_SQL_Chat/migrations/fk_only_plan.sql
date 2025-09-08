IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='fk_fact_loan_payments_loan_id') BEGIN
ALTER TABLE fact_loan_payments ADD CONSTRAINT fk_fact_loan_payments_loan_id FOREIGN KEY (loan_id) REFERENCES dim_company (company_key);
END

IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='fk_fact_loan_payments_payment_date') BEGIN
ALTER TABLE fact_loan_payments ADD CONSTRAINT fk_fact_loan_payments_payment_date FOREIGN KEY (payment_date) REFERENCES dim_date (date_key);
END