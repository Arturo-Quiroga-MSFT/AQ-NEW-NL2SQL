/* Verification queries for new 5-company seed (Aurora Robotics AB cohort)
   Run BEFORE and AFTER executing seed_new_companies_loans.sql to validate deltas.
   Optional: capture baseline counts into a temp table to compute differences. */
SET NOCOUNT ON;

/* 1. Basic existence check (idempotence) */
SELECT SeedAlreadyApplied = CASE WHEN EXISTS (SELECT 1 FROM dbo.Company WHERE CompanyName = 'Aurora Robotics AB') THEN 1 ELSE 0 END;

/* 2. Company & profile counts */
SELECT CompanyCount_New5 = COUNT(*)
FROM dbo.Company WHERE CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS');

SELECT Profiles_New5 = COUNT(*)
FROM dbo.CustomerProfile cp JOIN dbo.Company c ON c.CompanyId = cp.CompanyId
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS');

/* 3. Loans summary */
SELECT COUNT(*) AS Loans_New5,
       SUM(PrincipalAmount) AS TotalPrincipal_New5,
       AVG(InterestRatePct) AS AvgRate_New5
FROM dbo.Loan l JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS');

/* 4. Collateral coverage per new loan */
SELECT c.CompanyName, l.LoanId, l.PrincipalAmount, SUM(col.ValueAmount) AS CollateralValue,
       ROUND(SUM(col.ValueAmount)/NULLIF(l.PrincipalAmount,0),2) AS CollateralizationRatio
FROM dbo.Loan l
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
LEFT JOIN dbo.Collateral col ON col.LoanId = l.LoanId
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
GROUP BY c.CompanyName, l.LoanId, l.PrincipalAmount
ORDER BY c.CompanyName;

/* 5. Payment schedule distribution & status */
SELECT c.CompanyName, COUNT(*) AS ScheduleRows, SUM(CASE WHEN Status='Paid' THEN 1 ELSE 0 END) AS PaidRows,
       SUM(CASE WHEN Status='Overdue' THEN 1 ELSE 0 END) AS OverdueRows
FROM dbo.PaymentSchedule ps
JOIN dbo.Loan l ON l.LoanId = ps.LoanId
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
GROUP BY c.CompanyName;

/* 6. Covenant counts & latest status */
SELECT c.CompanyName,
       TotalCovenants = COUNT(*),
       Breached = SUM(CASE WHEN cv.Status='Breached' THEN 1 ELSE 0 END),
       Pending  = SUM(CASE WHEN cv.Status='Pending' THEN 1 ELSE 0 END),
       Met      = SUM(CASE WHEN cv.Status='Met' THEN 1 ELSE 0 END),
       Waived   = SUM(CASE WHEN cv.Status='Waived' THEN 1 ELSE 0 END)
FROM dbo.Covenant cv
JOIN dbo.Loan l ON l.LoanId = cv.LoanId
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
GROUP BY c.CompanyName;

/* 7. Covenant test result recency */
SELECT TOP 50 c.CompanyName, cv.CovenantType, MAX(tr.TestDate) AS LastTestDate, COUNT(*) AS TestPoints
FROM dbo.CovenantTestResult tr
JOIN dbo.Covenant cv ON cv.CovenantId = tr.CovenantId
JOIN dbo.Company c ON c.CompanyId = (SELECT l.CompanyId FROM dbo.Loan l WHERE l.LoanId = tr.LoanId)
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
GROUP BY c.CompanyName, cv.CovenantType
ORDER BY c.CompanyName, cv.CovenantType;

/* 8. Risk metric trend summary */
SELECT c.CompanyName, COUNT(*) AS Points,
       AVG(PD) AS AvgPD, AVG(LGD) AS AvgLGD, AVG(RiskScore) AS AvgRiskScore,
       SUM(CASE WHEN Trend='Improving' THEN 1 ELSE 0 END) AS ImprovingPoints,
       SUM(CASE WHEN Trend='Worsening' THEN 1 ELSE 0 END) AS WorseningPoints,
       SUM(CASE WHEN Trend='Stable' THEN 1 ELSE 0 END)    AS StablePoints
FROM dbo.RiskMetricHistory r
JOIN dbo.Loan l ON l.LoanId = r.LoanId
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
GROUP BY c.CompanyName
ORDER BY c.CompanyName;

/* 9. Idempotence re-run smoke check (no duplicates) */
-- Expect exactly 5 for each dimension of new companies
SELECT Companies=COUNT(DISTINCT CompanyId), Loans=COUNT(DISTINCT LoanId)
FROM dbo.Loan l WHERE l.CompanyId IN (
    SELECT CompanyId FROM dbo.Company WHERE CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
);
