/*
Migration 001 - Extend CONTOSO-FI domain with richer customer, geography, and product data
- Adds new reference tables, dimensions, and relationships
- Seeds realistic, diverse sample data

Idempotent: guarded by IF NOT EXISTS checks
*/

-- 1) Reference geography enhancements
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'[ref].[Subregion]') AND type = 'U')
BEGIN
  CREATE TABLE ref.Subregion (
    SubregionId tinyint NOT NULL PRIMARY KEY,
    SubregionName nvarchar(100) NOT NULL,
    RegionId tinyint NOT NULL,
    CONSTRAINT FK_Subregion_Region FOREIGN KEY (RegionId) REFERENCES ref.Region(RegionId)
  );
END

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE Name = N'SubregionId' AND Object_ID = Object_ID(N'ref.Country'))
BEGIN
  ALTER TABLE ref.Country ADD SubregionId tinyint NULL;
  ALTER TABLE ref.Country ADD CONSTRAINT FK_Country_Subregion FOREIGN KEY (SubregionId) REFERENCES ref.Subregion(SubregionId);
END

-- Seed subregions (simple mapping)
IF NOT EXISTS (SELECT 1 FROM ref.Subregion)
BEGIN
  INSERT INTO ref.Subregion (SubregionId, SubregionName, RegionId) VALUES
    (1, 'North America', 2),
    (2, 'Latin America', 2),
    (3, 'Western Europe', 4),
    (4, 'Eastern Europe', 4),
    (5, 'East Asia', 3),
    (6, 'South Asia', 3),
    (7, 'Southeast Asia', 3),
    (8, 'Southern Africa', 1),
    (9, 'West Africa', 1),
    (10, 'North Africa', 1);
END

-- 2) Customer enrichment
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CustomerProfile]') AND type = 'U')
BEGIN
  CREATE TABLE dbo.CustomerProfile (
    CustomerProfileId bigint IDENTITY(1,1) PRIMARY KEY,
    CompanyId bigint NOT NULL,
    LegalName nvarchar(200) NOT NULL,
    TaxId nvarchar(50) NULL,
    ParentCompanyId bigint NULL,
    OwnershipType nvarchar(50) NULL, -- Public, Private, State-Owned, Cooperative
    ESGScore decimal(5,2) NULL,      -- Environmental/Social/Governance composite
    AnnualRevenueUSD decimal(18,2) NULL,
    Headcount int NULL,
    Website nvarchar(200) NULL,
    IncorporationDate date NULL,
    CreditOfficer nvarchar(100) NULL,
    RiskAppetite nvarchar(50) NULL,  -- Low, Medium, High
    CONSTRAINT FK_CustomerProfile_Company FOREIGN KEY (CompanyId) REFERENCES dbo.Company(CompanyId),
    CONSTRAINT FK_CustomerProfile_ParentCompany FOREIGN KEY (ParentCompanyId) REFERENCES dbo.Company(CompanyId)
  );
END

-- 3) Product enrichment
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'[ref].[ReferenceRate]') AND type = 'U')
BEGIN
  CREATE TABLE ref.ReferenceRate (
    ReferenceRateCode varchar(20) NOT NULL PRIMARY KEY, -- e.g., SOFR-1M, SOFR-3M, EURIBOR-6M, TONA-ON
    Description nvarchar(200) NULL,
    TenorMonths tinyint NULL,
    CurrencyCode char(3) NULL REFERENCES ref.Currency(CurrencyCode)
  );
END

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE Name = N'ReferenceRateCode' AND Object_ID = Object_ID(N'dbo.Loan'))
BEGIN
  ALTER TABLE dbo.Loan ADD ReferenceRateCode varchar(20) NULL;
  ALTER TABLE dbo.Loan ADD CONSTRAINT FK_Loan_ReferenceRate FOREIGN KEY (ReferenceRateCode) REFERENCES ref.ReferenceRate(ReferenceRateCode);
END

-- Seed reference rates
IF NOT EXISTS (SELECT 1 FROM ref.ReferenceRate)
BEGIN
  INSERT INTO ref.ReferenceRate (ReferenceRateCode, Description, TenorMonths, CurrencyCode) VALUES
    ('SOFR-1M', 'Secured Overnight Financing Rate - 1 Month', 1, 'USD'),
    ('SOFR-3M', 'Secured Overnight Financing Rate - 3 Months', 3, 'USD'),
    ('EURIBOR-3M', 'Euro Interbank Offered Rate - 3 Months', 3, 'EUR'),
    ('EURIBOR-6M', 'Euro Interbank Offered Rate - 6 Months', 6, 'EUR'),
    ('TONA-ON', 'Tokyo Overnight Average - Overnight', 0, 'JPY');
END

-- 4) Covenant enrichment
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[CovenantSchedule]') AND type = 'U')
BEGIN
  CREATE TABLE dbo.CovenantSchedule (
    CovenantScheduleId bigint IDENTITY(1,1) PRIMARY KEY,
    CovenantId bigint NOT NULL REFERENCES dbo.Covenant(CovenantId),
    TestDueDate date NOT NULL,
    RequiredOperator varchar(5) NULL,   -- >, >=, <=, =
    RequiredThreshold decimal(18,4) NULL,
    NotificationDays smallint NULL      -- remind N days before due
  );
END

-- 5) Risk/portfolio classification
IF NOT EXISTS (SELECT 1 FROM sys.objects WHERE object_id = OBJECT_ID(N'[ref].[IndustrySector]') AND type = 'U')
BEGIN
  CREATE TABLE ref.IndustrySector (
    SectorCode varchar(10) NOT NULL PRIMARY KEY, -- e.g., ENE, TEC, HLTH, MAN, FIN
    SectorName nvarchar(100) NOT NULL
  );
END

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE Name = N'SectorCode' AND Object_ID = Object_ID(N'dbo.Company'))
BEGIN
  ALTER TABLE dbo.Company ADD SectorCode varchar(10) NULL;
  ALTER TABLE dbo.Company ADD CONSTRAINT FK_Company_Sector FOREIGN KEY (SectorCode) REFERENCES ref.IndustrySector(SectorCode);
END

IF NOT EXISTS (SELECT 1 FROM ref.IndustrySector)
BEGIN
  INSERT INTO ref.IndustrySector (SectorCode, SectorName) VALUES
    ('ENE','Energy'),('TEC','Technology'),('HLTH','Healthcare'),('MAN','Manufacturing'),('FIN','Financial Services'),('TEL','Telecom'),('TRN','Transport');
END

-- 6) Data seeding examples (light-touch, only when empty)
IF NOT EXISTS (SELECT 1 FROM dbo.CustomerProfile)
BEGIN
  INSERT INTO dbo.CustomerProfile (CompanyId, LegalName, TaxId, ParentCompanyId, OwnershipType, ESGScore, AnnualRevenueUSD, Headcount, Website, IncorporationDate, CreditOfficer, RiskAppetite)
  SELECT CompanyId,
         CompanyName + ' Ltd.',
         CONCAT('TAX', RIGHT(CONVERT(varchar(8), CompanyId + 100000), 6)),
         NULL,
         CASE WHEN CompanyName LIKE '%Energy%' THEN 'Public' ELSE 'Private' END,
         ROUND(RAND(CHECKSUM(NEWID())) * 50 + 25, 2),
         ROUND(RAND(CHECKSUM(NEWID())) * 90000000 + 10000000, 0),
         ABS(CHECKSUM(NEWID())) % 50000 + 100,
         LOWER(REPLACE(CompanyName,' ','-')) + '.example.com',
         DATEADD(year, -((ABS(CHECKSUM(NEWID())) % 50) + 5), GETDATE()),
         'Officer ' + LEFT(CompanyName, 1),
         CASE ABS(CHECKSUM(NEWID())) % 3 WHEN 0 THEN 'Low' WHEN 1 THEN 'Medium' ELSE 'High' END
  FROM dbo.Company;
END

-- Map some countries to subregions (example; safe even if no matches)
UPDATE c
SET SubregionId = CASE
  WHEN CountryName IN ('United States','Canada') THEN 1
  WHEN CountryName IN ('Mexico','Brazil') THEN 2
  WHEN CountryName IN ('Germany','France','Netherlands','United Kingdom') THEN 3
  WHEN CountryName IN ('Poland','Czech Republic') THEN 4
  WHEN CountryName IN ('Japan') THEN 5
  WHEN CountryName IN ('India') THEN 6
  WHEN CountryName IN ('Singapore') THEN 7
  WHEN CountryName IN ('South Africa') THEN 8
  WHEN CountryName IN ('Nigeria') THEN 9
  WHEN CountryName IN ('Egypt') THEN 10
  ELSE c.SubregionId END
FROM ref.Country c;
