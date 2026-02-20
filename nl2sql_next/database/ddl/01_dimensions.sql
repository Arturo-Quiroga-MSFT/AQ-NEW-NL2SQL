-- ========================================================
-- RetailDW — E-Commerce / Retail Star Schema
-- Phase 1: Schemas + Dimension Tables
-- Target: Azure SQL Database (RetailDW)
-- ========================================================
-- Author: NL2SQL Next Pipeline
-- Date: 2026-02-19
-- ========================================================

-- ========================================================
-- SCHEMA CREATION
-- ========================================================

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'dim')
    EXEC('CREATE SCHEMA dim');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'fact')
    EXEC('CREATE SCHEMA fact');
GO

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'ref')
    EXEC('CREATE SCHEMA ref');
GO

-- ========================================================
-- DIMENSION: DimDate
-- ========================================================
IF OBJECT_ID('dim.DimDate', 'U') IS NULL
CREATE TABLE dim.DimDate (
    DateKey          INT          PRIMARY KEY,   -- YYYYMMDD
    [Date]           DATE         NOT NULL UNIQUE,
    [Year]           INT          NOT NULL,
    Quarter          INT          NOT NULL,
    [Month]          INT          NOT NULL,
    MonthName        VARCHAR(20)  NOT NULL,
    [Week]           INT          NOT NULL,
    DayOfYear        INT          NOT NULL,
    DayOfMonth       INT          NOT NULL,
    DayOfWeek        INT          NOT NULL,
    DayName          VARCHAR(20)  NOT NULL,
    IsWeekend        BIT          NOT NULL DEFAULT 0,
    IsHoliday        BIT          NOT NULL DEFAULT 0,
    HolidayName      VARCHAR(100) NULL,
    FiscalYear       INT          NOT NULL,
    FiscalQuarter    INT          NOT NULL,
    CreatedDate      DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimDate_YearMonth ON dim.DimDate([Year], [Month]);
GO

-- ========================================================
-- DIMENSION: DimCustomer
-- ========================================================
IF OBJECT_ID('dim.DimCustomer', 'U') IS NULL
CREATE TABLE dim.DimCustomer (
    CustomerKey      INT IDENTITY(1,1) PRIMARY KEY,
    CustomerId       VARCHAR(20)  NOT NULL,          -- business key
    FirstName        NVARCHAR(100) NOT NULL,
    LastName         NVARCHAR(100) NOT NULL,
    Email            NVARCHAR(200) NULL,
    Gender           VARCHAR(10)  NULL,
    BirthDate        DATE         NULL,
    AgeGroup         VARCHAR(20)  NULL,              -- 18-24, 25-34 …
    City             NVARCHAR(100) NULL,
    [State]          NVARCHAR(60) NULL,
    Country          VARCHAR(60)  NOT NULL DEFAULT 'United States',
    PostalCode       VARCHAR(20)  NULL,
    Region           VARCHAR(40)  NULL,              -- Northeast, West …
    MembershipTier   VARCHAR(20)  NULL,              -- Bronze, Silver, Gold, Platinum
    SignupDate       DATE         NULL,
    IsActive         BIT          NOT NULL DEFAULT 1,
    CreatedDate      DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimCustomer_Region   ON dim.DimCustomer(Region);
CREATE INDEX IX_DimCustomer_Tier     ON dim.DimCustomer(MembershipTier);
GO

-- ========================================================
-- DIMENSION: DimProduct
-- ========================================================
IF OBJECT_ID('dim.DimProduct', 'U') IS NULL
CREATE TABLE dim.DimProduct (
    ProductKey       INT IDENTITY(1,1) PRIMARY KEY,
    ProductId        VARCHAR(20)  NOT NULL,          -- SKU / business key
    ProductName      NVARCHAR(200) NOT NULL,
    Category         VARCHAR(60)  NOT NULL,          -- Electronics, Clothing …
    Subcategory      VARCHAR(60)  NULL,
    Brand            NVARCHAR(100) NULL,
    UnitCost         DECIMAL(10,2) NOT NULL,
    UnitPrice        DECIMAL(10,2) NOT NULL,
    [Weight]         DECIMAL(8,2) NULL,
    Color            VARCHAR(30)  NULL,
    Size             VARCHAR(20)  NULL,
    IsActive         BIT          NOT NULL DEFAULT 1,
    LaunchDate       DATE         NULL,
    CreatedDate      DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_DimProduct_Category ON dim.DimProduct(Category);
CREATE INDEX IX_DimProduct_Brand    ON dim.DimProduct(Brand);
GO

-- ========================================================
-- DIMENSION: DimStore
-- ========================================================
IF OBJECT_ID('dim.DimStore', 'U') IS NULL
CREATE TABLE dim.DimStore (
    StoreKey         INT IDENTITY(1,1) PRIMARY KEY,
    StoreId          VARCHAR(20)  NOT NULL,
    StoreName        NVARCHAR(150) NOT NULL,
    StoreType        VARCHAR(30)  NOT NULL,          -- Online, Flagship, Outlet, Warehouse
    City             NVARCHAR(100) NULL,
    [State]          NVARCHAR(60) NULL,
    Country          VARCHAR(60)  NOT NULL DEFAULT 'United States',
    Region           VARCHAR(40)  NULL,
    OpenDate         DATE         NULL,
    SquareFootage    INT          NULL,
    ManagerName      NVARCHAR(120) NULL,
    IsActive         BIT          NOT NULL DEFAULT 1,
    CreatedDate      DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

-- ========================================================
-- DIMENSION: DimPromotion
-- ========================================================
IF OBJECT_ID('dim.DimPromotion', 'U') IS NULL
CREATE TABLE dim.DimPromotion (
    PromotionKey     INT IDENTITY(1,1) PRIMARY KEY,
    PromotionId      VARCHAR(20)  NOT NULL,
    PromotionName    NVARCHAR(150) NOT NULL,
    PromotionType    VARCHAR(40)  NOT NULL,          -- Percentage Off, BOGO, Free Shipping, Bundle
    DiscountPercent  DECIMAL(5,2) NULL,
    DiscountAmount   DECIMAL(10,2) NULL,
    StartDate        DATE         NOT NULL,
    EndDate          DATE         NOT NULL,
    MinOrderAmount   DECIMAL(10,2) NULL,
    IsActive         BIT          NOT NULL DEFAULT 1,
    CreatedDate      DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

-- ========================================================
-- DIMENSION: DimShippingMethod
-- ========================================================
IF OBJECT_ID('dim.DimShippingMethod', 'U') IS NULL
CREATE TABLE dim.DimShippingMethod (
    ShippingMethodKey INT IDENTITY(1,1) PRIMARY KEY,
    MethodName        VARCHAR(60)  NOT NULL,         -- Standard, Express, Same-Day, In-Store Pickup
    CarrierName       VARCHAR(60)  NULL,
    AvgDeliveryDays   INT          NULL,
    BaseCost          DECIMAL(8,2) NOT NULL DEFAULT 0,
    CreatedDate       DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

-- ========================================================
-- DIMENSION: DimPaymentMethod
-- ========================================================
IF OBJECT_ID('dim.DimPaymentMethod', 'U') IS NULL
CREATE TABLE dim.DimPaymentMethod (
    PaymentMethodKey INT IDENTITY(1,1) PRIMARY KEY,
    MethodName       VARCHAR(40)  NOT NULL,          -- Credit Card, Debit Card, PayPal, Gift Card, BNPL
    Provider         VARCHAR(40)  NULL,              -- Visa, Mastercard, Amex …
    CreatedDate      DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

-- ========================================================
-- REFERENCE: RefReturnReason
-- ========================================================
IF OBJECT_ID('ref.RefReturnReason', 'U') IS NULL
CREATE TABLE ref.RefReturnReason (
    ReturnReasonKey  INT IDENTITY(1,1) PRIMARY KEY,
    ReasonCode       VARCHAR(20)  NOT NULL,
    ReasonName       VARCHAR(80)  NOT NULL,          -- Defective, Wrong Size, Changed Mind …
    CreatedDate      DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

PRINT 'Phase 1 — Dimension tables created successfully.';
GO
