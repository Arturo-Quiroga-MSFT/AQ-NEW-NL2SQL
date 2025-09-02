# CONTOSO-FI Dataset Guide

Date: 2025-08-28

This guide summarizes the structure and key relationships of the CONTOSO-FI Azure SQL Database to help design and test NL→SQL examples.

Related files:
- Question bank: [CONTOSO-FI_EXAMPLE_QUESTIONS.txt](./CONTOSO-FI_EXAMPLE_QUESTIONS.txt)
- Baseline SQL solutions (subset, validated): [CONTOSO-FI_EXAMPLE_SOLUTIONS.md](./CONTOSO-FI_EXAMPLE_SOLUTIONS.md)

## Overview

- Server: aqsqlserver001.database.windows.net
- Database: CONTOSO-FI
- Focus: Commercial lending domain (loans, companies, payment schedules, covenants, collateral) with reference data for country, region, and currency.

## Schemas

- dbo
- ref
(Standard system/role schemas also present: db_*, guest, sys)

## Tables (key columns)

- dbo.Loan
  - LoanId (bigint), CompanyId (bigint), LoanNumber (varchar)
  - OriginationDate (date), MaturityDate (date)
  - PrincipalAmount (decimal), CurrencyCode (char)
  - InterestRatePct (decimal), InterestRateType (varchar), ReferenceRate (varchar), SpreadBps (smallint)
  - AmortizationType (varchar), PaymentFreqMonths (tinyint)
  - Purpose (nvarchar), Status (varchar)

- dbo.Company
  - CompanyId (bigint), CompanyName (nvarchar)
  - CountryCode (char), Industry (nvarchar), CreditRating (varchar)
  - FoundedYear (smallint), EmployeeCount (int)

- dbo.PaymentSchedule
  - ScheduleId (bigint), LoanId (bigint)
  - PaymentNumber (int), DueDate (date)
  - StartingPrincipal (decimal), PrincipalDue (decimal), InterestDue (decimal), TotalDue (decimal)
  - CurrencyCode (char), Status (varchar), PaidFlag (bit), PaidDate (date), EndingPrincipal (decimal)

- dbo.Covenant
  - CovenantId (bigint), LoanId (bigint)
  - CovenantType (varchar), Operator (varchar), Threshold (decimal)
  - Frequency (varchar), LastTestDate (date), Status (varchar), Notes (nvarchar)

- dbo.CovenantTestResult
  - TestResultId (bigint), CovenantId (bigint), LoanId (bigint)
  - TestDate (date), Status (varchar), ObservedValue (decimal), Notes (nvarchar)

- dbo.Collateral
  - CollateralId (bigint), LoanId (bigint)
  - CollateralType (varchar), Description (nvarchar), Jurisdiction (nvarchar)
  - ValueAmount (decimal), CurrencyCode (char), ValuationDate (date), Status (varchar)

- ref.Country
  - CountryCode (char), CountryName (nvarchar), RegionId (tinyint)

- ref.Region
  - RegionId (tinyint), RegionName (nvarchar)

- ref.Currency
  - CurrencyCode (char), CurrencyName (nvarchar), Symbol (nvarchar)

## Views

- dbo.vw_LoanPortfolio (selected columns)
  - LoanId, LoanNumber
  - CompanyName, Industry, CreditRating
  - CountryName, RegionName
  - OriginationDate, MaturityDate
  - PrincipalAmount, CurrencyCode
  - InterestRatePct, InterestRateType, ReferenceRate, SpreadBps
  - AmortizationType, PaymentFreqMonths
  - Status, Purpose

## Relationships (foreign keys)

- Loan.CompanyId → Company.CompanyId
- Loan.CurrencyCode → Currency.CurrencyCode
- Collateral.LoanId → Loan.LoanId
- Collateral.CurrencyCode → Currency.CurrencyCode
- PaymentSchedule.LoanId → Loan.LoanId
- PaymentSchedule.CurrencyCode → Currency.CurrencyCode
- Covenant.LoanId → Loan.LoanId
- CovenantTestResult.CovenantId → Covenant.CovenantId
- CovenantTestResult.LoanId → Loan.LoanId
- Company.CountryCode → Country.CountryCode
- Country.RegionId → Region.RegionId

## Suggested usage with NL2SQL

Leverage `AQ-NEW-NL2SQL/nl2sql_main.py` to:

1) Extract intent/entities from a natural language question
2) Generate a T-SQL query with schema context
3) Sanitize the SQL and execute against CONTOSO-FI
4) Review the formatted table output and saved run log

Tip: For quick demos, prefer the view `dbo.vw_LoanPortfolio` for portfolio-style questions and join to `ref` tables where appropriate for regional/country analysis.

## Next steps

- Use the question bank in `docs/CONTOSO-FI_EXAMPLE_QUESTIONS.txt` for demos and testing across easy/medium/complicated difficulty levels.
- Optionally add more views for common analytics (e.g., payment performance, covenant compliance summaries).
