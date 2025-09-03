# CONTOSO-FI Schema Summary and Demo Use Cases

Date: 2025-09-03

This document summarizes the main entities of CONTOSO-FI and offers demo-ready storylines you can run with NL→SQL.

## Domain focus

Commercial lending portfolio analytics for institutional/commercial clients. Core capabilities:
- Portfolio overview (loans, companies, regions, currencies)
- Cashflow and delinquency monitoring (PaymentSchedule, PaymentEvent)
- Risk and compliance (Covenant, CovenantTestResult, RiskMetricHistory)
- Collateral and coverage (Collateral)

## Core entities

- Company: Borrowers with location and industry. Ties to Country/Region/Subregion.
- Loan: Contracts with terms, principal, interest, and purpose. Ties to Company, Currency, ReferenceRate.
- PaymentSchedule: Expected periodic payments (principal/interest/total), with DueDate, PaidFlag, PaidDate, EndingPrincipal.
- PaymentEvent: Recorded events (payments, adjustments) with Amount and DaysDelinquent.
- Collateral: Assets securing loans with type, jurisdiction, value, and valuation date.
- Covenant/CovenantTestResult/CovenantSchedule: Risk/compliance rules, testing outcomes, and future due schedules.
- RiskMetricHistory: Company-level risk indicators over time.
- Reference data: Country/Region/Subregion and Currency (+ FX and reference rates).

## Typical join paths

- Loan → Company → Country → Region/Subregion (geo and industry context)
- Loan → PaymentSchedule (expected cashflows, balances)
- Loan → PaymentEvent (actual events, delinquency)
- Loan → Collateral (coverage)
- Loan → Covenant → CovenantTestResult / CovenantSchedule (compliance)
- Loan → ReferenceRate / Currency (rate context and denomination)

## Demo storylines (NL→SQL)

1) Portfolio pulse
   - "Show the 10 most recent loans by OriginationDate."
   - "Top 5 companies by total principal per region."

2) Cashflows and delinquency
   - "Payment performance overview: counts of Paid vs. Unpaid schedule entries."
   - "Delinquency buckets by region for the last 6 months (PaymentEvent.DaysDelinquent)."

3) Coverage and risk
   - "Total collateral value per loan and company (top 20)."
   - "Covenant compliance rate by industry and quarter."

4) Rate structure and currency
   - "Weighted average interest rate by region and currency (by principal)."
   - "Rate structure mix by region (fixed vs variable; include ReferenceRate)."

## Diagram

See `docs/diagrams/contoso_fi_schema.mmd` for the Mermaid ER diagram reflecting the core tables and relationships.

## Notes

- The demo questions file `docs/CONTOSO-FI_EXAMPLE_QUESTIONS.txt` contains curated prompts that favor broad aggregates and top-N selections to minimize empty result sets.
- Adjust time windows (e.g., last 3/6/12 months) to match the seed data in your environment.