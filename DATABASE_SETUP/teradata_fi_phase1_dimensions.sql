-- ========================================
-- TERADATA-FI Database Creation Script
-- Phase 1: Core Schema & Dimensions
-- Target: Azure SQL Database
-- ========================================
-- Author: NL2SQL Demo System
-- Date: 2025-10-09
-- Version: 1.0
-- ========================================

-- Create Database
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'TERADATA-FI')
BEGIN
    CREATE DATABASE [TERADATA-FI];
END
GO

USE [TERADATA-FI];
GO

-- ========================================
-- SCHEMA CREATION
-- ========================================

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'dim')
    EXEC('CREATE SCHEMA dim');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'fact')
    EXEC('CREATE SCHEMA fact');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'bridge')
    EXEC('CREATE SCHEMA bridge');
GO

IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'ref')
    EXEC('CREATE SCHEMA ref');
GO

-- ========================================
-- DIMENSION TABLES
-- ========================================

-- ============ DimDate (Shared Temporal Dimension) ============
CREATE TABLE dim.DimDate (
    DateKey INT PRIMARY KEY,  -- Format: YYYYMMDD (e.g., 20250109)
    [Date] DATE NOT NULL UNIQUE,
    
    -- Calendar attributes
    [Year] INT NOT NULL,
    Quarter INT NOT NULL,
    [Month] INT NOT NULL,
    MonthName VARCHAR(20) NOT NULL,
    [Week] INT NOT NULL,
    DayOfYear INT NOT NULL,
    DayOfMonth INT NOT NULL,
    DayOfWeek INT NOT NULL,
    DayName VARCHAR(20) NOT NULL,
    
    -- Flags
    IsWeekend BIT NOT NULL DEFAULT 0,
    IsHoliday BIT NOT NULL DEFAULT 0,
    HolidayName VARCHAR(100) NULL,
    IsQuarterEnd BIT NOT NULL DEFAULT 0,
    IsYearEnd BIT NOT NULL DEFAULT 0,
    IsMonthEnd BIT NOT NULL DEFAULT 0,
    
    -- Fiscal calendar
    FiscalYear INT NOT NULL,
    FiscalQuarter INT NOT NULL,
    FiscalMonth INT NOT NULL,
    
    -- Lookback references
    PriorDay DATE NULL,
    PriorWeek DATE NULL,
    PriorMonth DATE NULL,
    PriorQuarter DATE NULL,
    PriorYear DATE NULL,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimDate_Date ON dim.DimDate([Date]);
CREATE INDEX IX_DimDate_YearMonth ON dim.DimDate([Year], [Month]);
CREATE INDEX IX_DimDate_FiscalYearQuarter ON dim.DimDate(FiscalYear, FiscalQuarter);
GO

-- ============ DimCustomer (SCD Type 2) ============
CREATE TABLE dim.DimCustomer (
    CustomerKey INT IDENTITY(1,1) PRIMARY KEY,
    CustomerId VARCHAR(20) NOT NULL,  -- Business key
    
    -- Company information
    CompanyName NVARCHAR(200) NOT NULL,
    TaxId VARCHAR(50) NULL,
    LegalEntityType VARCHAR(50) NULL,  -- LLC, Corp, Partnership, Sole Proprietorship
    YearFounded INT NULL,
    EmployeeCount INT NULL,
    AnnualRevenue DECIMAL(18,2) NULL,
    
    -- Industry classification
    PrimaryIndustryId INT NULL,
    PrimarySICCode VARCHAR(10) NULL,
    PrimaryNAICSCode VARCHAR(10) NULL,
    
    -- Location
    HeadquartersAddressId INT NULL,
    
    -- Credit & Risk
    CreditRating_SP VARCHAR(10) NULL,
    CreditRating_Moody VARCHAR(10) NULL,
    CreditRating_Fitch VARCHAR(10) NULL,
    InternalRiskRating VARCHAR(10) NULL,
    
    -- Relationship
    RelationshipManagerId INT NULL,
    CustomerSegment VARCHAR(50) NULL,  -- Small Business, Middle Market, Corporate
    CustomerTier VARCHAR(20) NULL,  -- Platinum, Gold, Silver, Bronze
    
    -- Portfolio metrics
    TotalLoansCount INT NOT NULL DEFAULT 0,
    TotalLoanVolume DECIMAL(18,2) NOT NULL DEFAULT 0,
    LifetimeRevenue DECIMAL(18,2) NOT NULL DEFAULT 0,
    DefaultCount INT NOT NULL DEFAULT 0,
    
    -- Flags
    IsActive BIT NOT NULL DEFAULT 1,
    IsHighRisk BIT NOT NULL DEFAULT 0,
    IsVIP BIT NOT NULL DEFAULT 0,
    
    -- SCD Type 2 tracking
    EffectiveDate DATE NOT NULL,
    EndDate DATE NULL,
    IsCurrent BIT NOT NULL DEFAULT 1,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimCustomer_CustomerId ON dim.DimCustomer(CustomerId);
CREATE INDEX IX_DimCustomer_IsCurrent ON dim.DimCustomer(IsCurrent);
CREATE INDEX IX_DimCustomer_CompanyName ON dim.DimCustomer(CompanyName);
CREATE INDEX IX_DimCustomer_Segment ON dim.DimCustomer(CustomerSegment, CustomerTier);
GO

-- ============ DimEmployee (SCD Type 2) ============
CREATE TABLE dim.DimEmployee (
    EmployeeKey INT IDENTITY(1,1) PRIMARY KEY,
    EmployeeId VARCHAR(20) NOT NULL,  -- Business key
    
    -- Personal information
    EmployeeName NVARCHAR(200) NOT NULL,
    Email VARCHAR(100) NULL,
    Phone VARCHAR(20) NULL,
    
    -- Job information
    Title VARCHAR(100) NULL,
    Department VARCHAR(100) NULL,
    [Role] VARCHAR(100) NULL,  -- Loan Officer, Underwriter, Analyst, Manager
    HireDate DATE NULL,
    
    -- Hierarchy
    ManagerId INT NULL,  -- Self-referencing FK
    BranchId INT NULL,
    RegionId INT NULL,
    
    -- Performance metrics
    ProductionTarget_Annual DECIMAL(18,2) NULL,
    ProductionActual_YTD DECIMAL(18,2) NULL,
    LoanCount_Active INT NOT NULL DEFAULT 0,
    PortfolioSize DECIMAL(18,2) NOT NULL DEFAULT 0,
    
    -- Flags
    IsActive BIT NOT NULL DEFAULT 1,
    
    -- SCD Type 2 tracking
    EffectiveDate DATE NOT NULL,
    EndDate DATE NULL,
    IsCurrent BIT NOT NULL DEFAULT 1,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimEmployee_EmployeeId ON dim.DimEmployee(EmployeeId);
CREATE INDEX IX_DimEmployee_IsCurrent ON dim.DimEmployee(IsCurrent);
CREATE INDEX IX_DimEmployee_Role ON dim.DimEmployee([Role]);
CREATE INDEX IX_DimEmployee_Manager ON dim.DimEmployee(ManagerId);
GO

-- ============ DimBranch ============
CREATE TABLE dim.DimBranch (
    BranchKey INT IDENTITY(1,1) PRIMARY KEY,
    BranchId VARCHAR(20) NOT NULL UNIQUE,  -- Business key
    
    -- Branch information
    BranchName VARCHAR(200) NOT NULL,
    BranchCode VARCHAR(20) NOT NULL,
    BranchType VARCHAR(50) NULL,  -- Retail, Commercial, Private Banking
    
    -- Location
    AddressId INT NULL,
    RegionId INT NULL,
    MarketId INT NULL,
    
    -- Operations
    OpenDate DATE NULL,
    EmployeeCount INT NOT NULL DEFAULT 0,
    LoanVolume_YTD DECIMAL(18,2) NOT NULL DEFAULT 0,
    
    -- Flags
    IsActive BIT NOT NULL DEFAULT 1,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimBranch_RegionId ON dim.DimBranch(RegionId);
CREATE INDEX IX_DimBranch_IsActive ON dim.DimBranch(IsActive);
GO

-- ============ DimRegion ============
CREATE TABLE dim.DimRegion (
    RegionKey INT IDENTITY(1,1) PRIMARY KEY,
    RegionId VARCHAR(20) NOT NULL UNIQUE,  -- Business key
    
    -- Region information
    RegionName VARCHAR(100) NOT NULL,
    RegionCode VARCHAR(20) NOT NULL,
    Division VARCHAR(100) NULL,  -- Northeast, Southeast, Midwest, West, Southwest
    
    -- Leadership
    HeadquartersBranchId INT NULL,
    RegionalVP_EmployeeId INT NULL,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimAddress ============
CREATE TABLE dim.DimAddress (
    AddressKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Address components
    AddressLine1 VARCHAR(200) NOT NULL,
    AddressLine2 VARCHAR(200) NULL,
    City VARCHAR(100) NOT NULL,
    StateProvince VARCHAR(100) NOT NULL,
    PostalCode VARCHAR(20) NULL,
    CountryCode VARCHAR(3) NOT NULL DEFAULT 'USA',
    
    -- Geographic attributes
    Latitude DECIMAL(10,7) NULL,
    Longitude DECIMAL(10,7) NULL,
    MSA_Code VARCHAR(10) NULL,  -- Metropolitan Statistical Area
    County VARCHAR(100) NULL,
    TimeZone VARCHAR(50) NULL,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimAddress_StateProvince ON dim.DimAddress(StateProvince);
CREATE INDEX IX_DimAddress_City ON dim.DimAddress(City, StateProvince);
GO

-- ============ DimIndustry ============
CREATE TABLE dim.DimIndustry (
    IndustryKey INT IDENTITY(1,1) PRIMARY KEY,
    IndustryId VARCHAR(20) NOT NULL UNIQUE,  -- Business key
    
    -- Industry classification
    IndustrySector VARCHAR(100) NULL,  -- Manufacturing, Services, Technology, Healthcare
    IndustryGroup VARCHAR(100) NULL,
    IndustryName VARCHAR(200) NOT NULL,
    SICCode VARCHAR(10) NULL,
    NAICSCode VARCHAR(10) NULL,
    
    -- Risk profile
    RiskProfile VARCHAR(50) NULL,  -- Low, Medium, High, Very High
    DefaultRate_Historical DECIMAL(6,4) NULL,
    RecoveryRate_Historical DECIMAL(6,4) NULL,
    
    -- Flags
    IsRegulated BIT NOT NULL DEFAULT 0,
    IsVolatile BIT NOT NULL DEFAULT 0,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimIndustry_Sector ON dim.DimIndustry(IndustrySector);
CREATE INDEX IX_DimIndustry_SICCode ON dim.DimIndustry(SICCode);
CREATE INDEX IX_DimIndustry_NAICSCode ON dim.DimIndustry(NAICSCode);
GO

-- ============ DimLoanProduct ============
CREATE TABLE dim.DimLoanProduct (
    ProductKey INT IDENTITY(1,1) PRIMARY KEY,
    ProductId VARCHAR(20) NOT NULL UNIQUE,  -- Business key
    
    -- Product information
    ProductName VARCHAR(200) NOT NULL,
    ProductCategory VARCHAR(100) NULL,  -- Commercial, Real Estate, SBA, Equipment
    ProductType VARCHAR(100) NULL,
    ProductDescription NVARCHAR(500) NULL,
    
    -- Amount limits
    MinAmount DECIMAL(18,2) NULL,
    MaxAmount DECIMAL(18,2) NULL,
    MinTerm INT NULL,  -- Months
    MaxTerm INT NULL,  -- Months
    
    -- Rate structure
    BaseRateType VARCHAR(50) NULL,  -- Fixed, Variable
    ReferenceRateType VARCHAR(50) NULL,  -- SOFR, Prime, LIBOR (legacy)
    MarginBps INT NULL,  -- Basis points
    
    -- Requirements
    RequiresCollateral BIT NOT NULL DEFAULT 0,
    RequiresPersonalGuarantee BIT NOT NULL DEFAULT 0,
    AllowsPrepayment BIT NOT NULL DEFAULT 1,
    PrepaymentPenaltyPercent DECIMAL(5,2) NULL,
    
    -- Flags
    IsActive BIT NOT NULL DEFAULT 1,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimLoanProduct_Category ON dim.DimLoanProduct(ProductCategory);
CREATE INDEX IX_DimLoanProduct_IsActive ON dim.DimLoanProduct(IsActive);
GO

-- ============ DimLoanPurpose ============
CREATE TABLE dim.DimLoanPurpose (
    PurposeKey INT IDENTITY(1,1) PRIMARY KEY,
    PurposeId VARCHAR(20) NOT NULL UNIQUE,  -- Business key
    
    -- Purpose classification
    PurposeCategory VARCHAR(100) NULL,  -- Working Capital, Expansion, Acquisition
    PurposeName VARCHAR(200) NOT NULL,
    PurposeDescription NVARCHAR(500) NULL,
    
    -- Risk attributes
    RiskWeight DECIMAL(5,2) NULL,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimCollateralType ============
CREATE TABLE dim.DimCollateralType (
    CollateralTypeKey INT IDENTITY(1,1) PRIMARY KEY,
    CollateralTypeId VARCHAR(20) NOT NULL UNIQUE,  -- Business key
    
    -- Collateral classification
    CollateralCategory VARCHAR(100) NULL,  -- Real Estate, Equipment, Inventory, Receivables
    CollateralType VARCHAR(200) NOT NULL,
    CollateralDescription NVARCHAR(500) NULL,
    
    -- Valuation attributes
    TypicalLTV DECIMAL(5,2) NULL,  -- Loan-to-value ratio
    RequiresAppraisal BIT NOT NULL DEFAULT 0,
    AppraisalFrequencyMonths INT NULL,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimRiskRating ============
CREATE TABLE dim.DimRiskRating (
    RiskRatingKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Rating information
    RiskRatingCode VARCHAR(10) NOT NULL UNIQUE,  -- AAA, AA, A, BBB, BB, B, CCC, CC, C, D
    RiskRatingName VARCHAR(100) NOT NULL,
    RiskCategory VARCHAR(50) NULL,  -- Investment Grade, Sub-Investment Grade, Default
    NumericScore INT NULL,  -- 1-10 scale
    
    -- Risk metrics
    PD_Probability DECIMAL(6,4) NULL,  -- Probability of Default (e.g., 0.0250 = 2.5%)
    LGD_Probability DECIMAL(6,4) NULL,  -- Loss Given Default
    RequiredProvision_Percent DECIMAL(6,4) NULL,  -- CECL/Allowance requirement
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimCreditScore ============
CREATE TABLE dim.DimCreditScore (
    CreditScoreKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Score range
    ScoreRange VARCHAR(50) NOT NULL,  -- 800+, 750-799, 700-749, etc.
    ScoreMin INT NOT NULL,
    ScoreMax INT NOT NULL,
    
    -- Risk categorization
    RiskCategory VARCHAR(50) NULL,  -- Excellent, Good, Fair, Poor
    ApprovalLikelihood VARCHAR(50) NULL,  -- Very High, High, Moderate, Low
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimDelinquencyStatus ============
CREATE TABLE dim.DimDelinquencyStatus (
    DelinquencyStatusKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Status information
    StatusCode VARCHAR(20) NOT NULL UNIQUE,  -- CURRENT, DPD30, DPD60, DPD90, NPL, CHARGEOFF
    StatusName VARCHAR(100) NOT NULL,
    MinDaysDelinquent INT NOT NULL,
    MaxDaysDelinquent INT NOT NULL,
    
    -- Classification flags
    IsPerforming BIT NOT NULL DEFAULT 1,
    IsNonPerforming BIT NOT NULL DEFAULT 0,
    RequiresRestructuring BIT NOT NULL DEFAULT 0,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimCovenantType ============
CREATE TABLE dim.DimCovenantType (
    CovenantTypeKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Covenant information
    CovenantCategory VARCHAR(100) NULL,  -- Financial, Affirmative, Negative
    CovenantName VARCHAR(200) NOT NULL,
    CovenantDescription NVARCHAR(1000) NULL,
    
    -- Testing parameters
    TestFrequency VARCHAR(50) NULL,  -- Monthly, Quarterly, Annual
    ThresholdType VARCHAR(50) NULL,  -- Minimum, Maximum, Range
    DefaultSeverity VARCHAR(50) NULL,  -- Material, Non-Material, Technical
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimPaymentMethod ============
CREATE TABLE dim.DimPaymentMethod (
    PaymentMethodKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Method information
    MethodCode VARCHAR(20) NOT NULL UNIQUE,
    MethodName VARCHAR(100) NOT NULL,
    MethodDescription NVARCHAR(500) NULL,
    
    -- Processing attributes
    ProcessingFee DECIMAL(10,2) NULL,
    ProcessingDays INT NULL,
    IsElectronic BIT NOT NULL DEFAULT 0,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimPaymentType ============
CREATE TABLE dim.DimPaymentType (
    PaymentTypeKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Type information
    TypeCode VARCHAR(20) NOT NULL UNIQUE,
    TypeName VARCHAR(100) NOT NULL,
    TypeDescription NVARCHAR(500) NULL,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimApplicationStatus ============
CREATE TABLE dim.DimApplicationStatus (
    StatusKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Status information
    StatusCode VARCHAR(20) NOT NULL UNIQUE,
    StatusName VARCHAR(100) NOT NULL,
    StatusCategory VARCHAR(50) NULL,  -- Pending, Approved, Declined, Withdrawn
    
    -- Workflow flags
    IsActive BIT NOT NULL DEFAULT 1,
    IsTerminal BIT NOT NULL DEFAULT 0,  -- Is this a final state?
    SortOrder INT NULL,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimStatementType ============
CREATE TABLE dim.DimStatementType (
    StatementTypeKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Type information
    TypeCode VARCHAR(20) NOT NULL UNIQUE,  -- Q1, Q2, Q3, Q4, ANNUAL, INTERIM
    TypeName VARCHAR(100) NOT NULL,
    PeriodMonths INT NULL,
    IsAudited BIT NOT NULL DEFAULT 0,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimInteractionType ============
CREATE TABLE dim.DimInteractionType (
    InteractionTypeKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Type information
    TypeCode VARCHAR(20) NOT NULL UNIQUE,
    TypeName VARCHAR(100) NOT NULL,
    Category VARCHAR(100) NULL,  -- Sales, Service, Collections, Compliance
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimInteractionChannel ============
CREATE TABLE dim.DimInteractionChannel (
    ChannelKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Channel information
    ChannelCode VARCHAR(20) NOT NULL UNIQUE,
    ChannelName VARCHAR(100) NOT NULL,
    IsFaceToFace BIT NOT NULL DEFAULT 0,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

-- ============ DimCurrency ============
CREATE TABLE dim.DimCurrency (
    CurrencyKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Currency information
    CurrencyCode VARCHAR(3) NOT NULL UNIQUE,
    CurrencyName VARCHAR(100) NOT NULL,
    Symbol VARCHAR(10) NULL,
    
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

PRINT 'Phase 1: Dimension tables created successfully!';
GO
