/*
  Seed script: Adds 5 new companies, loans, collateral, payment schedules, payments, covenants, covenant test results, and risk metric history.
  Idempotent guard: checks for company 'Aurora Robotics AB'.
  Safe to re-run: skips inserts if already applied.
*/
SET NOCOUNT ON;

IF EXISTS (SELECT 1 FROM dbo.Company WHERE CompanyName = 'Aurora Robotics AB')
BEGIN
	PRINT 'Seed already applied: Aurora Robotics AB exists. Skipping.';
	RETURN;
END;

PRINT 'Seeding new companies and related financial data...';

/* 1. Insert Companies */
DECLARE @now DATE = CAST(GETDATE() AS DATE);
INSERT dbo.Company (CompanyName, CountryCode, CreatedDate, Status) VALUES
 ('Aurora Robotics AB','SE','2022-04-15','Active'),
 ('Solaris Grid SpA','ES','2021-11-10','Active'),
 ('Outback Agritech Pty','AU','2020-06-01','Active'),
 ('Andes Lithium SA','CL','2023-03-22','Active'),
 ('Helios BioHealth SAS','FR','2019-02-09','Active');

/* 2. Insert Customer Profiles (basic) */
INSERT dbo.CustomerProfile (CompanyId, LegalName, TaxId, OwnershipType, ESGScore, AnnualRevenueUSD, Headcount, Website, IncorporationDate, CreditOfficer, RiskAppetite)
SELECT CompanyId, CompanyName + ' Ltd.', CONCAT('TAX', RIGHT(CONVERT(varchar(8), CompanyId+900000),6)),
	   'Private', ROUND(RAND(CHECKSUM(NEWID())) * 20 + 60,2),
	   ROUND(RAND(CHECKSUM(NEWID())) * 20000000 + 5000000,0),
	   ABS(CHECKSUM(NEWID())) % 500 + 50, LOWER(REPLACE(CompanyName,' ','-')) + '.example.com',
	   DATEADD(year,-(ABS(CHECKSUM(NEWID())) % 10 + 2), @now), 'Officer ' + LEFT(CompanyName,1),
	   CASE ABS(CHECKSUM(NEWID())) % 3 WHEN 0 THEN 'Low' WHEN 1 THEN 'Medium' ELSE 'High' END
FROM dbo.Company c
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS');

/* 3. Insert Loans (varied structures) */
;WITH base AS (
 SELECT CompanyId, CompanyName
 FROM dbo.Company
 WHERE CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
)
INSERT dbo.Loan (CompanyId, LoanNumber, PrincipalAmount, CurrencyCode, InterestRatePct, AmortizationType, PaymentFreqMonths, OriginationDate, MaturityDate, InterestType, Status)
SELECT b.CompanyId, 'LN-' + LEFT(REPLACE(b.CompanyName,' ',''),12),
	   CASE b.CompanyName
			WHEN 'Aurora Robotics AB' THEN 3500000
			WHEN 'Solaris Grid SpA' THEN 5000000
			WHEN 'Outback Agritech Pty' THEN 2800000
			WHEN 'Andes Lithium SA' THEN 6200000
			WHEN 'Helios BioHealth SAS' THEN 4100000 END AS PrincipalAmount,
	   CASE WHEN b.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA') THEN 'EUR' ELSE 'USD' END AS CurrencyCode,
	   CASE WHEN b.CompanyName = 'Andes Lithium SA' THEN 9.2 WHEN b.CompanyName = 'Outback Agritech Pty' THEN 7.8 ELSE 6.5 END AS InterestRatePct,
	   CASE WHEN b.CompanyName = 'Helios BioHealth SAS' THEN 'Interest-Only' WHEN b.CompanyName = 'Solaris Grid SpA' THEN 'Bullet' ELSE 'Amortizing' END AS AmortizationType,
	   CASE WHEN b.CompanyName IN ('Solaris Grid SpA','Helios BioHealth SAS') THEN 6 ELSE 3 END AS PaymentFreqMonths,
	   DATEADD(year,-1,@now) AS OriginationDate, DATEADD(year,4,@now) AS MaturityDate,
	   CASE WHEN b.CompanyName IN ('Aurora Robotics AB','Andes Lithium SA') THEN 'Floating' ELSE 'Fixed' END AS InterestType,
	   CASE WHEN b.CompanyName = 'Outback Agritech Pty' THEN 'Defaulted' WHEN b.CompanyName = 'Helios BioHealth SAS' THEN 'Closed' ELSE 'Active' END AS Status
FROM base b;

/* 4. Collateral (diverse, over/under collateralization) */
DECLARE @today DATE = @now;
INSERT dbo.Collateral (LoanId, CollateralType, Description, Jurisdiction, ValueAmount, CurrencyCode, ValuationDate, Status)
SELECT l.LoanId, 'Equipment', c.CompanyName + ' robotics & plant', co.CountryName, l.PrincipalAmount * 0.90, l.CurrencyCode, DATEADD(month,-5,@today),'Active'
FROM dbo.Loan l
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
JOIN ref.Country co ON co.CountryCode = c.CountryCode
WHERE c.CompanyName = 'Aurora Robotics AB';

INSERT dbo.Collateral (LoanId, CollateralType, Description, Jurisdiction, ValueAmount, CurrencyCode, ValuationDate, Status)
SELECT l.LoanId, 'Receivables', c.CompanyName + ' solar PPA contracts', co.CountryName, l.PrincipalAmount * 1.40, l.CurrencyCode, DATEADD(month,-6,@today),'Active'
FROM dbo.Loan l JOIN dbo.Company c ON c.CompanyId = l.CompanyId
JOIN ref.Country co ON co.CountryCode = c.CountryCode
WHERE c.CompanyName = 'Solaris Grid SpA';

INSERT dbo.Collateral (LoanId, CollateralType, Description, Jurisdiction, ValueAmount, CurrencyCode, ValuationDate, Status)
SELECT l.LoanId, 'Inventory', c.CompanyName + ' agri sensor stock', co.CountryName, l.PrincipalAmount * 0.65, l.CurrencyCode, DATEADD(month,-4,@today),'Active'
FROM dbo.Loan l JOIN dbo.Company c ON c.CompanyId = l.CompanyId
JOIN ref.Country co ON co.CountryCode = c.CountryCode
WHERE c.CompanyName = 'Outback Agritech Pty';

INSERT dbo.Collateral (LoanId, CollateralType, Description, Jurisdiction, ValueAmount, CurrencyCode, ValuationDate, Status)
SELECT l.LoanId, 'RealEstate', c.CompanyName + ' lithium processing site', co.CountryName, l.PrincipalAmount * 1.10, l.CurrencyCode, DATEADD(month,-3,@today),'Active'
FROM dbo.Loan l JOIN dbo.Company c ON c.CompanyId = l.CompanyId
JOIN ref.Country co ON co.CountryCode = c.CountryCode
WHERE c.CompanyName = 'Andes Lithium SA';

INSERT dbo.Collateral (LoanId, CollateralType, Description, Jurisdiction, ValueAmount, CurrencyCode, ValuationDate, Status)
SELECT l.LoanId, 'Securities', c.CompanyName + ' R&D IP portfolio', co.CountryName, l.PrincipalAmount * 0.55, l.CurrencyCode, DATEADD(month,-2,@today),'Active'
FROM dbo.Loan l JOIN dbo.Company c ON c.CompanyId = l.CompanyId
JOIN ref.Country co ON co.CountryCode = c.CountryCode
WHERE c.CompanyName = 'Helios BioHealth SAS';

/* 5. Payment Schedules (simplified: first 6 periods per loan) */
DECLARE @LoanId2 BIGINT, @Cur CHAR(3), @Rate DECIMAL(6,2), @AmortType VARCHAR(20), @Freq INT, @Orig DATE, @Mat DATE, @Principal DECIMAL(18,2);
DECLARE newloan_cur CURSOR FAST_FORWARD FOR
	SELECT LoanId, CurrencyCode, InterestRatePct, AmortizationType, PaymentFreqMonths, OriginationDate, MaturityDate, PrincipalAmount
	FROM dbo.Loan l
	JOIN dbo.Company c ON c.CompanyId = l.CompanyId
	WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
	  AND NOT EXISTS (SELECT 1 FROM dbo.PaymentSchedule s WHERE s.LoanId = l.LoanId);
OPEN newloan_cur;
FETCH NEXT FROM newloan_cur INTO @LoanId2,@Cur,@Rate,@AmortType,@Freq,@Orig,@Mat,@Principal;
WHILE @@FETCH_STATUS = 0
BEGIN
	DECLARE @k2 INT = 1;
	DECLARE @MaxPeriods INT = 6;
	DECLARE @bal2 DECIMAL(18,2) = @Principal;
	DECLARE @i2 DECIMAL(18,10) = (@Rate/100.0) * (@Freq/12.0);
	WHILE @k2 <= @MaxPeriods
	BEGIN
		DECLARE @due2 DATE = DATEADD(month,@k2*@Freq,@Orig);
		DECLARE @interest2 DECIMAL(18,2) = ROUND(@bal2 * @i2,2);
		DECLARE @prin2 DECIMAL(18,2);
		IF @AmortType = 'Bullet' OR @AmortType = 'Interest-Only'
			SET @prin2 = CASE WHEN @k2=@MaxPeriods THEN @bal2 ELSE 0 END;
		ELSE
		BEGIN
			DECLARE @pmt2 DECIMAL(18,8);
			IF @i2 = 0
				SET @pmt2 = @bal2 / @MaxPeriods;
			ELSE
				SET @pmt2 = (@bal2 * @i2) / (1 - POWER(1+@i2,-@MaxPeriods));
			SET @prin2 = ROUND(@pmt2 - @interest2,2);
			IF @prin2 > @bal2 SET @prin2 = @bal2;
		END
		DECLARE @endbal2 DECIMAL(18,2) = @bal2 - @prin2;
		INSERT dbo.PaymentSchedule (LoanId, PaymentNumber, DueDate, StartingPrincipal, PrincipalDue, InterestDue, CurrencyCode, Status, PaidFlag, EndingPrincipal)
		VALUES (@LoanId2,@k2,@due2,@bal2,@prin2,@interest2,@Cur,'Scheduled',0,@endbal2);
		SET @bal2 = @endbal2;
		SET @k2 += 1;
	END
	FETCH NEXT FROM newloan_cur INTO @LoanId2,@Cur,@Rate,@AmortType,@Freq,@Orig,@Mat,@Principal;
END
CLOSE newloan_cur; DEALLOCATE newloan_cur;

/* 6. Payment Events (on time, late, partial) -> Represent via updating schedule rows */
-- Mark first 2 periods paid on time for Aurora Robotics
UPDATE ps SET Status='Paid', PaidFlag=1, PaidDate=DueDate
FROM dbo.PaymentSchedule ps JOIN dbo.Loan l ON l.LoanId = ps.LoanId
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName='Aurora Robotics AB' AND ps.PaymentNumber IN (1,2);
-- Solaris Grid: first payment late
UPDATE ps SET Status='Paid', PaidFlag=1, PaidDate=DATEADD(day,10,DueDate)
FROM dbo.PaymentSchedule ps JOIN dbo.Loan l ON l.LoanId = ps.LoanId
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName='Solaris Grid SpA' AND ps.PaymentNumber=1;
-- Outback Agritech: partial (leave status Overdue)
UPDATE ps SET Status='Overdue'
FROM dbo.PaymentSchedule ps JOIN dbo.Loan l ON l.LoanId = ps.LoanId
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName='Outback Agritech Pty' AND ps.PaymentNumber=1;

/* 7. Covenants (simple DSCR + Leverage) */
INSERT dbo.Covenant (LoanId, CovenantType, Operator, Threshold, Frequency, LastTestDate, Status, Notes)
SELECT l.LoanId, 'DSCR_Min','>=',1.25,'Quarterly',NULL,'Pending','Added for new loan'
FROM dbo.Loan l JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS');

INSERT dbo.Covenant (LoanId, CovenantType, Operator, Threshold, Frequency, LastTestDate, Status, Notes)
SELECT l.LoanId, 'Leverage_Max','<=',3.75,'Annual',NULL,'Pending','Added for new loan'
FROM dbo.Loan l JOIN dbo.Company c ON c.CompanyId = l.CompanyId
WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS');

/* 8. Covenant Test Results (last 3 periods, mix of status) */
;WITH targets AS (
	SELECT cv.CovenantId, cv.LoanId, cv.CovenantType FROM dbo.Covenant cv
	JOIN dbo.Loan l ON l.LoanId = cv.LoanId
	JOIN dbo.Company c ON c.CompanyId = l.CompanyId
	WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
)
INSERT dbo.CovenantTestResult (CovenantId, LoanId, TestDate, Status, ObservedValue, Notes)
SELECT t.CovenantId, t.LoanId, DATEADD(quarter,-v.k,@now) AS TestDate,
	   CASE (t.CovenantId + v.k) % 5 WHEN 0 THEN 'Breached' WHEN 1 THEN 'Waived' ELSE 'Met' END AS Status,
	   CASE WHEN t.CovenantType = 'DSCR_Min' THEN 1.10 + (v.k*0.05) ELSE 3.00 - (v.k*0.10) END AS ObservedValue,
	   t.CovenantType + ' test'
FROM targets t CROSS JOIN (SELECT 0 AS k UNION ALL SELECT 1 UNION ALL SELECT 2) v
WHERE NOT EXISTS (SELECT 1 FROM dbo.CovenantTestResult x WHERE x.CovenantId = t.CovenantId AND x.TestDate = DATEADD(quarter,-v.k,@now));

/* Update covenant metadata */
;WITH lt AS (SELECT CovenantId, MAX(TestDate) AS LastDate FROM dbo.CovenantTestResult GROUP BY CovenantId), ls AS (
	SELECT r.CovenantId, r.Status FROM dbo.CovenantTestResult r JOIN lt ON lt.CovenantId = r.CovenantId AND lt.LastDate = r.TestDate)
UPDATE cv SET cv.LastTestDate = lt.LastDate, cv.Status = ls.Status
FROM dbo.Covenant cv JOIN lt ON lt.CovenantId = cv.CovenantId JOIN ls ON ls.CovenantId = cv.CovenantId;

/* 9. Risk Metric History (example table create if missing) */
IF OBJECT_ID(N'dbo.RiskMetricHistory', N'U') IS NULL
BEGIN
	CREATE TABLE dbo.RiskMetricHistory (
		RiskMetricHistoryId BIGINT IDENTITY(1,1) PRIMARY KEY,
		LoanId BIGINT NOT NULL,
		AsOfDate DATE NOT NULL,
		PD DECIMAL(9,6) NULL, -- Probability of Default
		LGD DECIMAL(5,2) NULL, -- Loss Given Default %
		EAD DECIMAL(18,2) NULL, -- Exposure at Default
		RiskScore INT NULL,
		Trend VARCHAR(10) NULL CHECK (Trend IN ('Improving','Worsening','Stable'))
	);
	CREATE INDEX IX_RiskMetric_LoanDate ON dbo.RiskMetricHistory(LoanId, AsOfDate DESC);
END;

;WITH nl AS (
	SELECT l.LoanId FROM dbo.Loan l JOIN dbo.Company c ON c.CompanyId = l.CompanyId
	WHERE c.CompanyName IN ('Aurora Robotics AB','Solaris Grid SpA','Outback Agritech Pty','Andes Lithium SA','Helios BioHealth SAS')
), periods AS (SELECT 0 AS k UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3 UNION ALL SELECT 4)
INSERT dbo.RiskMetricHistory (LoanId, AsOfDate, PD, LGD, EAD, RiskScore, Trend)
SELECT nl.LoanId, DATEADD(month,-k.k,@now) AS AsOfDate,
	   ROUND(0.020 + (nl.LoanId % 5) * 0.003 + k.k*0.001,6) AS PD,
	   40 + (nl.LoanId % 7) * 2 AS LGD,
	   0.9 * (SELECT PrincipalAmount FROM dbo.Loan l2 WHERE l2.LoanId = nl.LoanId) AS EAD,
	   700 - ((nl.LoanId % 10) * 5) - (k.k*2) AS RiskScore,
	   CASE WHEN (nl.LoanId % 4)=0 THEN 'Improving' WHEN (nl.LoanId % 3)=0 THEN 'Worsening' ELSE 'Stable' END AS Trend
FROM nl CROSS JOIN periods k
WHERE NOT EXISTS (SELECT 1 FROM dbo.RiskMetricHistory r WHERE r.LoanId = nl.LoanId AND r.AsOfDate = DATEADD(month,-k.k,@now));

PRINT 'Seed complete.';