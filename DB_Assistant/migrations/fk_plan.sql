IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_company') BEGIN
CREATE TABLE dim_company (
    company_key INT NOT NULL,
    company_id VARCHAR(50) NOT NULL,
    region VARCHAR(40) NOT NULL,
    industry VARCHAR(60) NULL,
    CONSTRAINT pk_dim_company PRIMARY KEY CLUSTERED (company_key)
);
END

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dim_date') BEGIN
CREATE TABLE dim_date (
    date_key INT NOT NULL,
    calendar_date DATE NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY CLUSTERED (date_key)
);
END

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'fact_loan_payments') BEGIN
CREATE TABLE fact_loan_payments (
    loan_id VARCHAR(50) NOT NULL,
    payment_date DATE NOT NULL,
    principal_paid DECIMAL(18,2) NOT NULL,
    interest_paid DECIMAL(18,2) NOT NULL
);
END