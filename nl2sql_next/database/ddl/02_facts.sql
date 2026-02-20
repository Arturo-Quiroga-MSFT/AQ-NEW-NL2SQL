-- ========================================================
-- RetailDW — E-Commerce / Retail Star Schema
-- Phase 2: Fact Tables
-- Target: Azure SQL Database (RetailDW)
-- ========================================================

-- ========================================================
-- FACT: FactOrders (grain = one order line item)
-- ========================================================
IF OBJECT_ID('fact.FactOrders', 'U') IS NULL
CREATE TABLE fact.FactOrders (
    OrderLineKey      INT IDENTITY(1,1) PRIMARY KEY,
    OrderId           VARCHAR(20)  NOT NULL,
    LineNumber        INT          NOT NULL,

    -- Dimension FKs
    CustomerKey       INT          NOT NULL,
    ProductKey        INT          NOT NULL,
    OrderDateKey      INT          NOT NULL,
    ShipDateKey       INT          NULL,
    StoreKey          INT          NOT NULL,
    PromotionKey      INT          NULL,
    ShippingMethodKey INT          NULL,
    PaymentMethodKey  INT          NULL,

    -- Measures
    Quantity          INT          NOT NULL DEFAULT 1,
    UnitPrice         DECIMAL(10,2) NOT NULL,
    UnitCost          DECIMAL(10,2) NOT NULL,
    DiscountAmount    DECIMAL(10,2) NOT NULL DEFAULT 0,
    ShippingCost      DECIMAL(10,2) NOT NULL DEFAULT 0,
    TaxAmount         DECIMAL(10,2) NOT NULL DEFAULT 0,
    LineTotal         DECIMAL(12,2) NOT NULL,         -- Quantity * UnitPrice - Discount
    LineCost          DECIMAL(12,2) NOT NULL,         -- Quantity * UnitCost
    LineProfit        DECIMAL(12,2) NOT NULL,         -- LineTotal - LineCost - ShippingCost

    -- Status
    OrderStatus       VARCHAR(20)  NOT NULL DEFAULT 'Completed',  -- Completed, Cancelled, Returned
    IsReturned        BIT          NOT NULL DEFAULT 0,

    -- Audit
    CreatedDate       DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FactOrders_Customer   ON fact.FactOrders(CustomerKey);
CREATE INDEX IX_FactOrders_Product    ON fact.FactOrders(ProductKey);
CREATE INDEX IX_FactOrders_OrderDate  ON fact.FactOrders(OrderDateKey);
CREATE INDEX IX_FactOrders_Store      ON fact.FactOrders(StoreKey);
CREATE INDEX IX_FactOrders_OrderId    ON fact.FactOrders(OrderId);
GO

-- ========================================================
-- FACT: FactReturns (grain = one returned line item)
-- ========================================================
IF OBJECT_ID('fact.FactReturns', 'U') IS NULL
CREATE TABLE fact.FactReturns (
    ReturnKey         INT IDENTITY(1,1) PRIMARY KEY,
    ReturnId          VARCHAR(20)  NOT NULL,
    OrderId           VARCHAR(20)  NOT NULL,
    LineNumber        INT          NOT NULL,

    -- Dimension FKs
    CustomerKey       INT          NOT NULL,
    ProductKey        INT          NOT NULL,
    ReturnDateKey     INT          NOT NULL,
    StoreKey          INT          NOT NULL,
    ReturnReasonKey   INT          NULL,

    -- Measures
    Quantity          INT          NOT NULL DEFAULT 1,
    RefundAmount      DECIMAL(10,2) NOT NULL,

    -- Status
    ReturnStatus      VARCHAR(20)  NOT NULL DEFAULT 'Approved',  -- Approved, Rejected, Pending
    IsRefunded        BIT          NOT NULL DEFAULT 1,

    -- Audit
    CreatedDate       DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FactReturns_Customer  ON fact.FactReturns(CustomerKey);
CREATE INDEX IX_FactReturns_Product   ON fact.FactReturns(ProductKey);
CREATE INDEX IX_FactReturns_ReturnDate ON fact.FactReturns(ReturnDateKey);
GO

-- ========================================================
-- FACT: FactInventory (grain = product × store × date snapshot)
-- ========================================================
IF OBJECT_ID('fact.FactInventory', 'U') IS NULL
CREATE TABLE fact.FactInventory (
    InventoryKey      INT IDENTITY(1,1) PRIMARY KEY,

    -- Dimension FKs
    ProductKey        INT          NOT NULL,
    StoreKey          INT          NOT NULL,
    SnapshotDateKey   INT          NOT NULL,

    -- Measures
    QuantityOnHand    INT          NOT NULL DEFAULT 0,
    QuantityOnOrder   INT          NOT NULL DEFAULT 0,
    ReorderPoint      INT          NOT NULL DEFAULT 0,
    UnitCost          DECIMAL(10,2) NOT NULL,
    InventoryValue    DECIMAL(14,2) NOT NULL,         -- QuantityOnHand × UnitCost

    -- Audit
    CreatedDate       DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FactInventory_Product  ON fact.FactInventory(ProductKey);
CREATE INDEX IX_FactInventory_Store    ON fact.FactInventory(StoreKey);
CREATE INDEX IX_FactInventory_Date     ON fact.FactInventory(SnapshotDateKey);
GO

-- ========================================================
-- FACT: FactWebTraffic (grain = session-level)
-- ========================================================
IF OBJECT_ID('fact.FactWebTraffic', 'U') IS NULL
CREATE TABLE fact.FactWebTraffic (
    SessionKey        INT IDENTITY(1,1) PRIMARY KEY,
    SessionId         VARCHAR(40)  NOT NULL,

    -- Dimension FKs
    CustomerKey       INT          NULL,              -- NULL for anonymous visitors
    VisitDateKey      INT          NOT NULL,

    -- Measures
    PageViews         INT          NOT NULL DEFAULT 1,
    SessionDurationSec INT         NOT NULL DEFAULT 0,
    BounceFlag        BIT          NOT NULL DEFAULT 0,
    ProductsViewed    INT          NOT NULL DEFAULT 0,
    AddedToCart       INT          NOT NULL DEFAULT 0,
    ConvertedFlag     BIT          NOT NULL DEFAULT 0,

    -- Attributes
    TrafficSource     VARCHAR(40)  NULL,              -- Organic, Paid Search, Social, Email, Direct
    DeviceType        VARCHAR(20)  NULL,              -- Desktop, Mobile, Tablet
    Browser           VARCHAR(30)  NULL,
    LandingPage       VARCHAR(200) NULL,

    -- Audit
    CreatedDate       DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FactWebTraffic_Customer ON fact.FactWebTraffic(CustomerKey);
CREATE INDEX IX_FactWebTraffic_Date     ON fact.FactWebTraffic(VisitDateKey);
GO

-- ========================================================
-- FACT: FactCustomerReview (grain = one review)
-- ========================================================
IF OBJECT_ID('fact.FactCustomerReview', 'U') IS NULL
CREATE TABLE fact.FactCustomerReview (
    ReviewKey         INT IDENTITY(1,1) PRIMARY KEY,
    ReviewId          VARCHAR(20)  NOT NULL,

    -- Dimension FKs
    CustomerKey       INT          NOT NULL,
    ProductKey        INT          NOT NULL,
    ReviewDateKey     INT          NOT NULL,

    -- Measures
    Rating            INT          NOT NULL CHECK (Rating BETWEEN 1 AND 5),
    ReviewLength      INT          NOT NULL DEFAULT 0,  -- word count
    HelpfulVotes      INT          NOT NULL DEFAULT 0,

    -- Attributes
    ReviewTitle       NVARCHAR(200) NULL,
    IsVerifiedPurchase BIT         NOT NULL DEFAULT 1,
    SentimentScore    DECIMAL(3,2) NULL,              -- -1.00 to 1.00

    -- Audit
    CreatedDate       DATETIME2    NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FactReview_Customer ON fact.FactCustomerReview(CustomerKey);
CREATE INDEX IX_FactReview_Product  ON fact.FactCustomerReview(ProductKey);
CREATE INDEX IX_FactReview_Date     ON fact.FactCustomerReview(ReviewDateKey);
GO

PRINT 'Phase 2 — Fact tables created successfully.';
GO
