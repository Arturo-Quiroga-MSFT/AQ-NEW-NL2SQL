/*
  CONTOSO-FI extensions: Collateral, Covenant, PaymentSchedule

  - Creates tables if missing
  - Adds helpful indexes
  - Seeds data idempotently for existing loans

  Notes:
  - Assumes base schema already exists: ref.Region, ref.Country, ref.Currency, dbo.Company, dbo.Loan
  - Database name has a hyphen; wrap in [] when using USE.
*/

-- Optional: target database (uncomment if needed)
-- USE [CONTOSO-FI];
SET NOCOUNT ON;

/* =========================
   Collateral
   ========================= */
IF OBJECT_ID(N'dbo.Collateral', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Collateral (
        CollateralId     BIGINT IDENTITY(1,1) PRIMARY KEY,
        LoanId           BIGINT      NOT NULL,
        CollateralType   VARCHAR(30) NOT NULL CHECK (CollateralType IN ('RealEstate','Equipment','Receivables','Inventory','Cash','Securities','Guarantee')),
        Description      NVARCHAR(200) NULL,
        Jurisdiction     NVARCHAR(100) NULL,
        ValueAmount      DECIMAL(18,2) NOT NULL CHECK (ValueAmount > 0),
        CurrencyCode     CHAR(3)      NOT NULL,
        ValuationDate    DATE         NOT NULL,
        Status           VARCHAR(20)  NOT NULL CHECK (Status IN ('Active','Released','Impaired')),
        CONSTRAINT FK_Collateral_Loan FOREIGN KEY (LoanId) REFERENCES dbo.Loan(LoanId),
        CONSTRAINT FK_Collateral_Currency FOREIGN KEY (CurrencyCode) REFERENCES ref.Currency(CurrencyCode)
    );
    CREATE INDEX IX_Collateral_Loan ON dbo.Collateral(LoanId);
    CREATE INDEX IX_Collateral_Type ON dbo.Collateral(CollateralType);
END;

/* =========================
   Covenant
   ========================= */
IF OBJECT_ID(N'dbo.Covenant', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.Covenant (
        CovenantId     BIGINT IDENTITY(1,1) PRIMARY KEY,
        LoanId         BIGINT      NOT NULL,
        CovenantType   VARCHAR(40) NOT NULL CHECK (CovenantType IN ('DSCR_Min','Leverage_Max','InterestCoverage_Min','CurrentRatio_Min','NetWorth_Min')),
        Operator       VARCHAR(2)  NOT NULL CHECK (Operator IN ('>=','<=','>','<','=')),
        Threshold      DECIMAL(18,4) NOT NULL,
        Frequency      VARCHAR(20) NOT NULL CHECK (Frequency IN ('Monthly','Quarterly','Semiannual','Annual')),
        LastTestDate   DATE        NULL,
        Status         VARCHAR(20) NOT NULL CHECK (Status IN ('Met','Breached','Waived','Pending')),
        Notes          NVARCHAR(200) NULL,
        CONSTRAINT FK_Covenant_Loan FOREIGN KEY (LoanId) REFERENCES dbo.Loan(LoanId)
    );
    CREATE INDEX IX_Covenant_Loan ON dbo.Covenant(LoanId);
    CREATE INDEX IX_Covenant_Type ON dbo.Covenant(CovenantType);
END;

/* =========================
   PaymentSchedule
   ========================= */
IF OBJECT_ID(N'dbo.PaymentSchedule', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.PaymentSchedule (
        ScheduleId        BIGINT IDENTITY(1,1) PRIMARY KEY,
        LoanId            BIGINT       NOT NULL,
        PaymentNumber     INT          NOT NULL,
        DueDate           DATE         NOT NULL,
        StartingPrincipal DECIMAL(18,2) NOT NULL,
        PrincipalDue      DECIMAL(18,2) NOT NULL DEFAULT(0),
        InterestDue       DECIMAL(18,2) NOT NULL DEFAULT(0),
        TotalDue          AS (ROUND(PrincipalDue + InterestDue, 2)) PERSISTED,
        CurrencyCode      CHAR(3)      NOT NULL,
        Status            VARCHAR(20)  NOT NULL CHECK (Status IN ('Scheduled','Paid','Overdue','Cancelled')) DEFAULT 'Scheduled',
        PaidFlag          BIT          NOT NULL DEFAULT(0),
        PaidDate          DATE         NULL,
        EndingPrincipal   DECIMAL(18,2) NOT NULL,
        CONSTRAINT UQ_PaymentSchedule UNIQUE (LoanId, PaymentNumber),
        CONSTRAINT FK_Schedule_Loan FOREIGN KEY (LoanId) REFERENCES dbo.Loan(LoanId),
        CONSTRAINT FK_Schedule_Currency FOREIGN KEY (CurrencyCode) REFERENCES ref.Currency(CurrencyCode)
    );
    CREATE INDEX IX_Schedule_Loan ON dbo.PaymentSchedule(LoanId);
    CREATE INDEX IX_Schedule_DueDate ON dbo.PaymentSchedule(DueDate);
END;

/* =========================
   Seed Collateral (idempotent per loan + type)
   ========================= */
DECLARE @today DATE = CAST(GETDATE() AS DATE);
;WITH base AS (
    SELECT l.LoanId, l.PrincipalAmount, l.CurrencyCode,
           c.CompanyName, co.CountryName, r.RegionName
    FROM dbo.Loan l
    JOIN dbo.Company c ON c.CompanyId = l.CompanyId
    JOIN ref.Country co ON co.CountryCode = c.CountryCode
    JOIN ref.Region r ON r.RegionId = co.RegionId
)
INSERT dbo.Collateral (LoanId, CollateralType, Description, Jurisdiction, ValueAmount, CurrencyCode, ValuationDate, Status)
SELECT b.LoanId,
       CASE WHEN b.RegionName = 'Americas' THEN 'Receivables'
            WHEN b.RegionName = 'Europe'   THEN 'Equipment'
            WHEN b.RegionName = 'Asia'     THEN 'Securities'
            ELSE 'RealEstate' END AS CollateralType,
       CONCAT(b.CompanyName, N' collateral package'),
        b.CountryName,
        b.PrincipalAmount * CASE WHEN b.RegionName IN ('Americas','Europe') THEN 1.30 ELSE 1.15 END,
        b.CurrencyCode,
        DATEADD(month, -6, @today),
        'Active'
FROM base b
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.Collateral x
    WHERE x.LoanId = b.LoanId
      AND x.CollateralType IN ('Receivables','Equipment','Securities','RealEstate')
);

-- Second collateral (Guarantee) for every third loan
INSERT dbo.Collateral (LoanId, CollateralType, Description, Jurisdiction, ValueAmount, CurrencyCode, ValuationDate, Status)
SELECT b.LoanId,
       'Guarantee',
       CONCAT(b.CompanyName, N' corporate guarantee'),
       b.CountryName,
       b.PrincipalAmount * 0.50,
       b.CurrencyCode,
       DATEADD(month, -6, @today),
       'Active'
FROM base b
WHERE (b.LoanId % 3) = 0
  AND NOT EXISTS (
        SELECT 1 FROM dbo.Collateral x
        WHERE x.LoanId = b.LoanId AND x.CollateralType = 'Guarantee'
  );

/* =========================
   Seed Covenants (two per loan, idempotent)
   ========================= */
-- DSCR_Min
INSERT dbo.Covenant (LoanId, CovenantType, Operator, Threshold, Frequency, LastTestDate, Status, Notes)
SELECT l.LoanId,
       'DSCR_Min', '>=', 1.2000,
       CASE WHEN r.RegionName IN ('Americas','Europe') THEN 'Quarterly' ELSE 'Semiannual' END,
       DATEFROMPARTS(YEAR(@today), (DATEPART(QUARTER, @today)*3), 1),
       'Pending', N'Minimum DSCR requirement'
FROM dbo.Loan l
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
JOIN ref.Country co ON co.CountryCode = c.CountryCode
JOIN ref.Region r ON r.RegionId = co.RegionId
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.Covenant cv
    WHERE cv.LoanId = l.LoanId AND cv.CovenantType = 'DSCR_Min'
);

-- Leverage_Max
INSERT dbo.Covenant (LoanId, CovenantType, Operator, Threshold, Frequency, LastTestDate, Status, Notes)
SELECT l.LoanId,
       'Leverage_Max', '<=', 3.5000,
       'Annual',
       DATEFROMPARTS(YEAR(@today)-1, 12, 31),
       'Pending', N'Max Net Debt / EBITDA'
FROM dbo.Loan l
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.Covenant cv
    WHERE cv.LoanId = l.LoanId AND cv.CovenantType = 'Leverage_Max'
);

/* =========================
   Seed Payment Schedules (idempotent per loan)
   ========================= */
DECLARE @LoanId BIGINT, @Currency CHAR(3), @Rate DECIMAL(6,3), @Amort VARCHAR(20), @Freq TINYINT,
        @Orig DATE, @Mat DATE, @Principal DECIMAL(18,2);

DECLARE loan_cur CURSOR FAST_FORWARD FOR
    SELECT LoanId, CurrencyCode, InterestRatePct, AmortizationType, PaymentFreqMonths, OriginationDate, MaturityDate, PrincipalAmount
    FROM dbo.Loan
    WHERE NOT EXISTS (SELECT 1 FROM dbo.PaymentSchedule s WHERE s.LoanId = dbo.Loan.LoanId);

OPEN loan_cur;
FETCH NEXT FROM loan_cur INTO @LoanId, @Currency, @Rate, @Amort, @Freq, @Orig, @Mat, @Principal;

WHILE @@FETCH_STATUS = 0
BEGIN
    DECLARE @n INT = NULLIF(DATEDIFF(month, @Orig, @Mat) / NULLIF(@Freq,0), 0);
    IF @n IS NULL OR @n < 1 SET @n = 1;

    DECLARE @i DECIMAL(18,10) = (@Rate/100.0) * (@Freq/12.0); -- approximate periodic rate
    DECLARE @bal DECIMAL(18,2) = @Principal;
    DECLARE @k INT = 1;

    WHILE @k <= @n
    BEGIN
        DECLARE @due DATE = DATEADD(month, @k*@Freq, @Orig);
        DECLARE @interest DECIMAL(18,2) = ROUND(@bal * @i, 2);
        DECLARE @prin DECIMAL(18,2);

        IF @Amort = 'Bullet'
            SET @prin = CASE WHEN @k = @n THEN @bal ELSE 0 END;
        ELSE IF @Amort = 'Interest-Only'
            SET @prin = CASE WHEN @k = @n THEN @bal ELSE 0 END;
        ELSE
        BEGIN
            DECLARE @pmt DECIMAL(18,8);
            IF @i = 0 OR @n = 0
                SET @pmt = @bal / NULLIF(@n,0);
            ELSE
                SET @pmt = (@bal * @i) / (1 - POWER(1 + @i, -@n));
            SET @prin = ROUND(@pmt - @interest, 2);
            IF @prin > @bal SET @prin = @bal;
        END

        DECLARE @endbal DECIMAL(18,2) = @bal - @prin;

        INSERT dbo.PaymentSchedule (LoanId, PaymentNumber, DueDate, StartingPrincipal, PrincipalDue, InterestDue, CurrencyCode, Status, PaidFlag, EndingPrincipal)
        VALUES (@LoanId, @k, @due, @bal, @prin, @interest, @Currency, 'Scheduled', 0, @endbal);

        SET @bal = @endbal;
        SET @k += 1;
    END

    FETCH NEXT FROM loan_cur INTO @LoanId, @Currency, @Rate, @Amort, @Freq, @Orig, @Mat, @Principal;
END

CLOSE loan_cur;
DEALLOCATE loan_cur;

/* =========================
   Quick checks
   ========================= */
SELECT
  (SELECT COUNT(*) FROM dbo.Collateral)     AS CollateralCount,
  (SELECT COUNT(*) FROM dbo.Covenant)       AS CovenantCount,
  (SELECT COUNT(*) FROM dbo.PaymentSchedule) AS ScheduleRows;

/* =========================
   Additional Covenants + Test Results
   ========================= */

-- Add extra covenant types per loan if missing
INSERT dbo.Covenant (LoanId, CovenantType, Operator, Threshold, Frequency, LastTestDate, Status, Notes)
SELECT l.LoanId, 'InterestCoverage_Min', '>=', 2.0000,
       CASE WHEN r.RegionName IN ('Americas','Europe') THEN 'Quarterly' ELSE 'Semiannual' END,
       NULL, 'Pending', N'Minimum EBITDA / Interest expense'
FROM dbo.Loan l
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
JOIN ref.Country co ON co.CountryCode = c.CountryCode
JOIN ref.Region r ON r.RegionId = co.RegionId
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.Covenant cv WHERE cv.LoanId = l.LoanId AND cv.CovenantType = 'InterestCoverage_Min'
);

INSERT dbo.Covenant (LoanId, CovenantType, Operator, Threshold, Frequency, LastTestDate, Status, Notes)
SELECT l.LoanId, 'CurrentRatio_Min', '>=', 1.2000,
       CASE WHEN r.RegionName IN ('Americas','Europe') THEN 'Semiannual' ELSE 'Annual' END,
       NULL, 'Pending', N'Minimum Current Assets / Current Liabilities'
FROM dbo.Loan l
JOIN dbo.Company c ON c.CompanyId = l.CompanyId
JOIN ref.Country co ON co.CountryCode = c.CountryCode
JOIN ref.Region r ON r.RegionId = co.RegionId
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.Covenant cv WHERE cv.LoanId = l.LoanId AND cv.CovenantType = 'CurrentRatio_Min'
);

-- Covenant test result table
IF OBJECT_ID(N'dbo.CovenantTestResult', N'U') IS NULL
BEGIN
    CREATE TABLE dbo.CovenantTestResult (
        TestResultId  BIGINT IDENTITY(1,1) PRIMARY KEY,
        CovenantId    BIGINT      NOT NULL,
        LoanId        BIGINT      NOT NULL,
        TestDate      DATE        NOT NULL,
        Status        VARCHAR(20) NOT NULL CHECK (Status IN ('Met','Breached','Waived')),
        ObservedValue DECIMAL(18,4) NULL,
        Notes         NVARCHAR(200) NULL,
        CONSTRAINT FK_CovTest_Covenant FOREIGN KEY (CovenantId) REFERENCES dbo.Covenant(CovenantId),
        CONSTRAINT FK_CovTest_Loan FOREIGN KEY (LoanId) REFERENCES dbo.Loan(LoanId)
    );
    CREATE INDEX IX_CovTest_Covenant ON dbo.CovenantTestResult(CovenantId);
    CREATE INDEX IX_CovTest_LoanDate ON dbo.CovenantTestResult(LoanId, TestDate DESC);
END;

-- Seed last 4 period test results per covenant (idempotent)
;WITH k AS (
    SELECT 0 AS k UNION ALL SELECT 1 UNION ALL SELECT 2 UNION ALL SELECT 3
), base AS (
    SELECT cv.CovenantId, cv.LoanId, cv.CovenantType, cv.Operator, cv.Threshold, cv.Frequency
    FROM dbo.Covenant cv
)
INSERT dbo.CovenantTestResult (CovenantId, LoanId, TestDate, Status, ObservedValue, Notes)
SELECT b.CovenantId,
       b.LoanId,
       CASE b.Frequency
           WHEN 'Quarterly'  THEN EOMONTH(DATEADD(quarter,  -k.k, CAST(GETDATE() AS DATE)))
           WHEN 'Semiannual' THEN EOMONTH(DATEADD(month,   -6*k.k, CAST(GETDATE() AS DATE)))
           WHEN 'Annual'     THEN EOMONTH(DATEFROMPARTS(YEAR(GETDATE())-k.k, 12, 1))
           ELSE EOMONTH(DATEADD(quarter, -k.k, CAST(GETDATE() AS DATE)))
       END AS TestDate,
       CASE WHEN ((b.CovenantId + k.k) % 9) = 0 THEN 'Breached'
            WHEN ((b.CovenantId + k.k) % 13) = 0 THEN 'Waived'
            ELSE 'Met' END AS Status,
       CASE b.Operator
            WHEN '>=' THEN b.Threshold * CASE WHEN ((b.CovenantId + k.k) % 9) = 0 THEN 0.85 WHEN ((b.CovenantId + k.k) % 13) = 0 THEN 0.95 ELSE 1.10 END
            WHEN '<=' THEN b.Threshold * CASE WHEN ((b.CovenantId + k.k) % 9) = 0 THEN 1.15 WHEN ((b.CovenantId + k.k) % 13) = 0 THEN 1.05 ELSE 0.90 END
            ELSE b.Threshold
       END AS ObservedValue,
       CONCAT(b.CovenantType, N' test') AS Notes
FROM base b
CROSS JOIN k
WHERE NOT EXISTS (
    SELECT 1 FROM dbo.CovenantTestResult t
    WHERE t.CovenantId = b.CovenantId
      AND t.TestDate = CASE b.Frequency
           WHEN 'Quarterly'  THEN EOMONTH(DATEADD(quarter,  -k.k, CAST(GETDATE() AS DATE)))
           WHEN 'Semiannual' THEN EOMONTH(DATEADD(month,   -6*k.k, CAST(GETDATE() AS DATE)))
           WHEN 'Annual'     THEN EOMONTH(DATEFROMPARTS(YEAR(GETDATE())-k.k, 12, 1))
           ELSE EOMONTH(DATEADD(quarter, -k.k, CAST(GETDATE() AS DATE)))
      END
);

-- Update Covenant last test metadata
;WITH last_test AS (
    SELECT CovenantId, MAX(TestDate) AS LastDate
    FROM dbo.CovenantTestResult
    GROUP BY CovenantId
), last_status AS (
    SELECT ctr.CovenantId, ctr.Status
    FROM dbo.CovenantTestResult ctr
    JOIN last_test lt ON lt.CovenantId = ctr.CovenantId AND lt.LastDate = ctr.TestDate
)
UPDATE cv
SET cv.LastTestDate = lt.LastDate,
    cv.Status = ls.Status
FROM dbo.Covenant cv
JOIN last_test lt ON lt.CovenantId = cv.CovenantId
JOIN last_status ls ON ls.CovenantId = cv.CovenantId;
