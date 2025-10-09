-- ========================================
-- TERADATA-FI Fact Tables Creation Script
-- Phase 1: Core Fact Tables
-- Target: Azure SQL Database
-- ========================================
-- Author: NL2SQL Demo System
-- Date: 2025-10-09
-- Version: 1.0
-- ========================================

USE [TERADATA-FI];
GO

-- ========================================
-- FACT TABLES
-- ========================================

-- ============ FACT_LOAN_ORIGINATION ============
-- Primary fact table tracking all originated loans
CREATE TABLE fact.FACT_LOAN_ORIGINATION (
    LoanKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Business key
    LoanId VARCHAR(50) NOT NULL UNIQUE,
    
    -- Dimension foreign keys
    CustomerKey INT NOT NULL,
    OriginationDateKey INT NOT NULL,
    MaturityDateKey INT NULL,
    FirstPaymentDateKey INT NULL,
    ProductKey INT NOT NULL,
    PurposeKey INT NULL,
    BranchKey INT NOT NULL,
    LoanOfficerKey INT NOT NULL,
    UnderwriterKey INT NULL,
    RiskRatingKey INT NULL,
    DelinquencyStatusKey INT NOT NULL,
    
    -- Loan amounts
    OriginalAmount DECIMAL(18,2) NOT NULL,
    FundedAmount DECIMAL(18,2) NOT NULL,
    CurrentBalance DECIMAL(18,2) NOT NULL,
    PrincipalPaid DECIMAL(18,2) NOT NULL DEFAULT 0,
    InterestPaid DECIMAL(18,2) NOT NULL DEFAULT 0,
    
    -- Terms
    TermMonths INT NOT NULL,
    RemainingTermMonths INT NOT NULL,
    
    -- Rate information
    InterestRate DECIMAL(8,4) NOT NULL,
    RateType VARCHAR(20) NULL,  -- Fixed, Variable
    ReferenceRate VARCHAR(50) NULL,  -- SOFR, Prime, etc.
    Margin DECIMAL(8,4) NULL,
    APR DECIMAL(8,4) NULL,
    
    -- Fees
    OriginationFee DECIMAL(18,2) NULL DEFAULT 0,
    ProcessingFee DECIMAL(18,2) NULL DEFAULT 0,
    OtherFees DECIMAL(18,2) NULL DEFAULT 0,
    TotalFeesCollected DECIMAL(18,2) NOT NULL DEFAULT 0,
    
    -- Collateral
    CollateralValue DECIMAL(18,2) NULL,
    LTV DECIMAL(5,2) NULL,  -- Loan-to-value ratio
    
    -- Performance metrics
    DaysDelinquent INT NOT NULL DEFAULT 0,
    PaymentsMade INT NOT NULL DEFAULT 0,
    PaymentsScheduled INT NOT NULL DEFAULT 0,
    MissedPayments INT NOT NULL DEFAULT 0,
    LatePayments INT NOT NULL DEFAULT 0,
    
    -- Financial metrics
    NPV DECIMAL(18,2) NULL,  -- Net Present Value
    IRR DECIMAL(8,4) NULL,  -- Internal Rate of Return
    ROE DECIMAL(8,4) NULL,  -- Return on Equity
    Yield DECIMAL(8,4) NULL,  -- Current yield
    
    -- Flags
    IsActive BIT NOT NULL DEFAULT 1,
    IsPaidOff BIT NOT NULL DEFAULT 0,
    IsChargedOff BIT NOT NULL DEFAULT 0,
    IsRestructured BIT NOT NULL DEFAULT 0,
    HasPersonalGuarantee BIT NOT NULL DEFAULT 0,
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FACT_LoanOrigination_CustomerKey ON fact.FACT_LOAN_ORIGINATION(CustomerKey);
CREATE INDEX IX_FACT_LoanOrigination_OriginationDate ON fact.FACT_LOAN_ORIGINATION(OriginationDateKey);
CREATE INDEX IX_FACT_LoanOrigination_ProductKey ON fact.FACT_LOAN_ORIGINATION(ProductKey);
CREATE INDEX IX_FACT_LoanOrigination_BranchKey ON fact.FACT_LOAN_ORIGINATION(BranchKey);
CREATE INDEX IX_FACT_LoanOrigination_LoanOfficerKey ON fact.FACT_LOAN_ORIGINATION(LoanOfficerKey);
CREATE INDEX IX_FACT_LoanOrigination_Status ON fact.FACT_LOAN_ORIGINATION(IsActive, DelinquencyStatusKey);
GO

-- ============ FACT_LOAN_APPLICATION ============
-- Application funnel tracking
CREATE TABLE fact.FACT_LOAN_APPLICATION (
    ApplicationKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Business key
    ApplicationId VARCHAR(50) NOT NULL UNIQUE,
    
    -- Dimension foreign keys
    CustomerKey INT NOT NULL,
    ApplicationDateKey INT NOT NULL,
    DecisionDateKey INT NULL,
    ProductKey INT NOT NULL,
    PurposeKey INT NULL,
    BranchKey INT NOT NULL,
    LoanOfficerKey INT NOT NULL,
    ApplicationStatusKey INT NOT NULL,
    
    -- Application details
    RequestedAmount DECIMAL(18,2) NOT NULL,
    ApprovedAmount DECIMAL(18,2) NULL,
    RequestedTerm INT NOT NULL,
    ApprovedTerm INT NULL,
    
    -- Credit assessment
    CreditScoreAtApplication INT NULL,
    DebtToIncomeRatio DECIMAL(5,2) NULL,
    AnnualRevenue DECIMAL(18,2) NULL,
    InternalRiskScore INT NULL,
    
    -- Decision
    DecisionCode VARCHAR(20) NULL,  -- APPROVED, DECLINED, WITHDRAWN, EXPIRED
    DecisionReason NVARCHAR(500) NULL,
    UnderwriterKey INT NULL,
    ReviewDuration_Days INT NULL,
    
    -- Conversion
    OriginatedLoanKey INT NULL,  -- FK to FACT_LOAN_ORIGINATION
    
    -- Flags
    IsApproved BIT NOT NULL DEFAULT 0,
    IsConverted BIT NOT NULL DEFAULT 0,  -- Did application convert to loan?
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FACT_Application_CustomerKey ON fact.FACT_LOAN_APPLICATION(CustomerKey);
CREATE INDEX IX_FACT_Application_ApplicationDate ON fact.FACT_LOAN_APPLICATION(ApplicationDateKey);
CREATE INDEX IX_FACT_Application_ProductKey ON fact.FACT_LOAN_APPLICATION(ProductKey);
CREATE INDEX IX_FACT_Application_Status ON fact.FACT_LOAN_APPLICATION(ApplicationStatusKey);
CREATE INDEX IX_FACT_Application_Conversion ON fact.FACT_LOAN_APPLICATION(IsConverted, IsApproved);
GO

-- ============ FACT_LOAN_BALANCE_DAILY ============
-- Daily balance snapshots for trend analysis
CREATE TABLE fact.FACT_LOAN_BALANCE_DAILY (
    BalanceKey BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Dimension foreign keys
    LoanKey INT NOT NULL,
    SnapshotDateKey INT NOT NULL,
    DelinquencyStatusKey INT NOT NULL,
    RiskRatingKey INT NULL,
    
    -- Balance components
    PrincipalBalance DECIMAL(18,2) NOT NULL,
    InterestBalance DECIMAL(18,2) NOT NULL DEFAULT 0,
    FeesBalance DECIMAL(18,2) NOT NULL DEFAULT 0,
    TotalBalance DECIMAL(18,2) NOT NULL,
    
    -- Accruals
    AccruedInterest DECIMAL(18,2) NOT NULL DEFAULT 0,
    
    -- Delinquency
    DaysDelinquent INT NOT NULL DEFAULT 0,
    DelinquentAmount DECIMAL(18,2) NOT NULL DEFAULT 0,
    
    -- Allowance (CECL)
    Allowance DECIMAL(18,2) NOT NULL DEFAULT 0,
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE UNIQUE CLUSTERED INDEX IX_FACT_BalanceDaily_LoanDate ON fact.FACT_LOAN_BALANCE_DAILY(LoanKey, SnapshotDateKey);
CREATE INDEX IX_FACT_BalanceDaily_SnapshotDate ON fact.FACT_LOAN_BALANCE_DAILY(SnapshotDateKey);
GO

-- ============ FACT_PAYMENT_TRANSACTION ============
-- Every payment recorded
CREATE TABLE fact.FACT_PAYMENT_TRANSACTION (
    PaymentKey BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Business key
    PaymentId VARCHAR(50) NOT NULL UNIQUE,
    
    -- Dimension foreign keys
    LoanKey INT NOT NULL,
    PaymentDateKey INT NOT NULL,
    ScheduledDateKey INT NULL,
    PaymentMethodKey INT NOT NULL,
    PaymentTypeKey INT NOT NULL,
    
    -- Payment amounts
    TotalPaymentAmount DECIMAL(18,2) NOT NULL,
    PrincipalAmount DECIMAL(18,2) NOT NULL DEFAULT 0,
    InterestAmount DECIMAL(18,2) NOT NULL DEFAULT 0,
    FeesAmount DECIMAL(18,2) NOT NULL DEFAULT 0,
    PenaltyAmount DECIMAL(18,2) NOT NULL DEFAULT 0,
    
    -- Payment tracking
    ScheduledAmount DECIMAL(18,2) NULL,
    PaymentNumber INT NULL,
    DaysLate INT NOT NULL DEFAULT 0,
    
    -- Flags
    IsEarlyPayment BIT NOT NULL DEFAULT 0,
    IsLatePayment BIT NOT NULL DEFAULT 0,
    IsPrepayment BIT NOT NULL DEFAULT 0,
    IsReversed BIT NOT NULL DEFAULT 0,
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FACT_Payment_LoanKey ON fact.FACT_PAYMENT_TRANSACTION(LoanKey);
CREATE INDEX IX_FACT_Payment_PaymentDate ON fact.FACT_PAYMENT_TRANSACTION(PaymentDateKey);
CREATE INDEX IX_FACT_Payment_ScheduledDate ON fact.FACT_PAYMENT_TRANSACTION(ScheduledDateKey);
GO

-- ============ FACT_CUSTOMER_FINANCIALS ============
-- Quarterly/annual financial statements
CREATE TABLE fact.FACT_CUSTOMER_FINANCIALS (
    FinancialKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Dimension foreign keys
    CustomerKey INT NOT NULL,
    StatementDateKey INT NOT NULL,
    StatementTypeKey INT NOT NULL,
    
    -- Income statement
    Revenue DECIMAL(18,2) NULL,
    COGS DECIMAL(18,2) NULL,
    GrossProfit DECIMAL(18,2) NULL,
    OperatingExpenses DECIMAL(18,2) NULL,
    EBITDA DECIMAL(18,2) NULL,
    EBIT DECIMAL(18,2) NULL,
    InterestExpense DECIMAL(18,2) NULL,
    NetIncome DECIMAL(18,2) NULL,
    
    -- Balance sheet
    TotalAssets DECIMAL(18,2) NULL,
    CurrentAssets DECIMAL(18,2) NULL,
    FixedAssets DECIMAL(18,2) NULL,
    TotalLiabilities DECIMAL(18,2) NULL,
    CurrentLiabilities DECIMAL(18,2) NULL,
    LongTermDebt DECIMAL(18,2) NULL,
    TotalEquity DECIMAL(18,2) NULL,
    
    -- Cash flow
    OperatingCashFlow DECIMAL(18,2) NULL,
    InvestingCashFlow DECIMAL(18,2) NULL,
    FinancingCashFlow DECIMAL(18,2) NULL,
    
    -- Calculated ratios
    CurrentRatio DECIMAL(8,4) NULL,
    QuickRatio DECIMAL(8,4) NULL,
    DebtToEquityRatio DECIMAL(8,4) NULL,
    DebtServiceCoverageRatio DECIMAL(8,4) NULL,
    ROA DECIMAL(8,4) NULL,
    ROE DECIMAL(8,4) NULL,
    GrossMargin DECIMAL(8,4) NULL,
    NetMargin DECIMAL(8,4) NULL,
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FACT_Financials_CustomerKey ON fact.FACT_CUSTOMER_FINANCIALS(CustomerKey);
CREATE INDEX IX_FACT_Financials_StatementDate ON fact.FACT_CUSTOMER_FINANCIALS(StatementDateKey);
CREATE INDEX IX_FACT_Financials_Type ON fact.FACT_CUSTOMER_FINANCIALS(StatementTypeKey);
GO

-- ============ FACT_COVENANT_TEST ============
-- Covenant compliance testing
CREATE TABLE fact.FACT_COVENANT_TEST (
    CovenantTestKey INT IDENTITY(1,1) PRIMARY KEY,
    
    -- Dimension foreign keys
    LoanKey INT NOT NULL,
    TestDateKey INT NOT NULL,
    CovenantTypeKey INT NOT NULL,
    
    -- Test details
    ThresholdValue DECIMAL(18,4) NULL,
    ActualValue DECIMAL(18,4) NULL,
    PassFailStatus VARCHAR(20) NOT NULL,  -- PASS, FAIL, WAIVED
    
    -- Severity
    ViolationSeverity VARCHAR(50) NULL,  -- Technical, Material, Curable
    DaysSinceViolation INT NULL,
    
    -- Actions
    ActionRequired VARCHAR(50) NULL,
    ActionTaken VARCHAR(200) NULL,
    WaiverGranted BIT NOT NULL DEFAULT 0,
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FACT_CovenantTest_LoanKey ON fact.FACT_COVENANT_TEST(LoanKey);
CREATE INDEX IX_FACT_CovenantTest_TestDate ON fact.FACT_COVENANT_TEST(TestDateKey);
CREATE INDEX IX_FACT_CovenantTest_Type ON fact.FACT_COVENANT_TEST(CovenantTypeKey);
CREATE INDEX IX_FACT_CovenantTest_Status ON fact.FACT_COVENANT_TEST(PassFailStatus);
GO

-- ============ FACT_CUSTOMER_INTERACTION ============
-- CRM tracking
CREATE TABLE fact.FACT_CUSTOMER_INTERACTION (
    InteractionKey BIGINT IDENTITY(1,1) PRIMARY KEY,
    
    -- Business key
    InteractionId VARCHAR(50) NOT NULL UNIQUE,
    
    -- Dimension foreign keys
    CustomerKey INT NOT NULL,
    InteractionDateKey INT NOT NULL,
    EmployeeKey INT NOT NULL,
    InteractionTypeKey INT NOT NULL,
    InteractionChannelKey INT NOT NULL,
    
    -- Interaction details
    Subject NVARCHAR(500) NULL,
    Notes NVARCHAR(MAX) NULL,
    Duration_Minutes INT NULL,
    Outcome VARCHAR(100) NULL,
    
    -- Related entities
    RelatedLoanKey INT NULL,
    RelatedApplicationKey INT NULL,
    
    -- Follow-up
    RequiresFollowUp BIT NOT NULL DEFAULT 0,
    FollowUpDateKey INT NULL,
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE()
);
GO

CREATE INDEX IX_FACT_Interaction_CustomerKey ON fact.FACT_CUSTOMER_INTERACTION(CustomerKey);
CREATE INDEX IX_FACT_Interaction_InteractionDate ON fact.FACT_CUSTOMER_INTERACTION(InteractionDateKey);
CREATE INDEX IX_FACT_Interaction_EmployeeKey ON fact.FACT_CUSTOMER_INTERACTION(EmployeeKey);
CREATE INDEX IX_FACT_Interaction_Type ON fact.FACT_CUSTOMER_INTERACTION(InteractionTypeKey);
GO

-- ========================================
-- BRIDGE TABLES (Many-to-Many)
-- ========================================

-- ============ Bridge_Loan_Collateral ============
CREATE TABLE bridge.Bridge_Loan_Collateral (
    LoanKey INT NOT NULL,
    CollateralKey INT NOT NULL,
    CollateralTypeKey INT NOT NULL,
    
    -- Collateral details
    CollateralDescription NVARCHAR(500) NULL,
    AppraisedValue DECIMAL(18,2) NULL,
    AppraisalDate DATE NULL,
    LienPosition INT NULL,
    
    -- Flags
    IsPrimary BIT NOT NULL DEFAULT 0,
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    PRIMARY KEY (LoanKey, CollateralKey)
);
GO

-- ============ Bridge_Customer_Industry ============
-- Customers can operate in multiple industries
CREATE TABLE bridge.Bridge_Customer_Industry (
    CustomerKey INT NOT NULL,
    IndustryKey INT NOT NULL,
    
    -- Relationship details
    IsPrimary BIT NOT NULL DEFAULT 0,
    RevenuePercentage DECIMAL(5,2) NULL,
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    PRIMARY KEY (CustomerKey, IndustryKey)
);
GO

-- ============ Bridge_Loan_Guarantor ============
CREATE TABLE bridge.Bridge_Loan_Guarantor (
    LoanKey INT NOT NULL,
    GuarantorKey INT NOT NULL,
    
    -- Guarantee details
    GuaranteePercentage DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    GuaranteeType VARCHAR(50) NULL,  -- Personal, Corporate, Limited
    
    -- Audit
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    
    PRIMARY KEY (LoanKey, GuarantorKey)
);
GO

-- ========================================
-- FOREIGN KEY CONSTRAINTS
-- ========================================

-- FACT_LOAN_ORIGINATION
ALTER TABLE fact.FACT_LOAN_ORIGINATION ADD CONSTRAINT FK_LoanOrig_Customer 
    FOREIGN KEY (CustomerKey) REFERENCES dim.DimCustomer(CustomerKey);
ALTER TABLE fact.FACT_LOAN_ORIGINATION ADD CONSTRAINT FK_LoanOrig_OriginationDate 
    FOREIGN KEY (OriginationDateKey) REFERENCES dim.DimDate(DateKey);
ALTER TABLE fact.FACT_LOAN_ORIGINATION ADD CONSTRAINT FK_LoanOrig_Product 
    FOREIGN KEY (ProductKey) REFERENCES dim.DimLoanProduct(ProductKey);
ALTER TABLE fact.FACT_LOAN_ORIGINATION ADD CONSTRAINT FK_LoanOrig_Purpose 
    FOREIGN KEY (PurposeKey) REFERENCES dim.DimLoanPurpose(PurposeKey);
ALTER TABLE fact.FACT_LOAN_ORIGINATION ADD CONSTRAINT FK_LoanOrig_Branch 
    FOREIGN KEY (BranchKey) REFERENCES dim.DimBranch(BranchKey);
ALTER TABLE fact.FACT_LOAN_ORIGINATION ADD CONSTRAINT FK_LoanOrig_DelinquencyStatus 
    FOREIGN KEY (DelinquencyStatusKey) REFERENCES dim.DimDelinquencyStatus(DelinquencyStatusKey);
GO

-- FACT_LOAN_APPLICATION
ALTER TABLE fact.FACT_LOAN_APPLICATION ADD CONSTRAINT FK_Application_Customer 
    FOREIGN KEY (CustomerKey) REFERENCES dim.DimCustomer(CustomerKey);
ALTER TABLE fact.FACT_LOAN_APPLICATION ADD CONSTRAINT FK_Application_ApplicationDate 
    FOREIGN KEY (ApplicationDateKey) REFERENCES dim.DimDate(DateKey);
ALTER TABLE fact.FACT_LOAN_APPLICATION ADD CONSTRAINT FK_Application_Product 
    FOREIGN KEY (ProductKey) REFERENCES dim.DimLoanProduct(ProductKey);
ALTER TABLE fact.FACT_LOAN_APPLICATION ADD CONSTRAINT FK_Application_Branch 
    FOREIGN KEY (BranchKey) REFERENCES dim.DimBranch(BranchKey);
ALTER TABLE fact.FACT_LOAN_APPLICATION ADD CONSTRAINT FK_Application_Status 
    FOREIGN KEY (ApplicationStatusKey) REFERENCES dim.DimApplicationStatus(StatusKey);
GO

-- FACT_LOAN_BALANCE_DAILY
ALTER TABLE fact.FACT_LOAN_BALANCE_DAILY ADD CONSTRAINT FK_Balance_Loan 
    FOREIGN KEY (LoanKey) REFERENCES fact.FACT_LOAN_ORIGINATION(LoanKey);
ALTER TABLE fact.FACT_LOAN_BALANCE_DAILY ADD CONSTRAINT FK_Balance_SnapshotDate 
    FOREIGN KEY (SnapshotDateKey) REFERENCES dim.DimDate(DateKey);
ALTER TABLE fact.FACT_LOAN_BALANCE_DAILY ADD CONSTRAINT FK_Balance_DelinquencyStatus 
    FOREIGN KEY (DelinquencyStatusKey) REFERENCES dim.DimDelinquencyStatus(DelinquencyStatusKey);
GO

-- FACT_PAYMENT_TRANSACTION
ALTER TABLE fact.FACT_PAYMENT_TRANSACTION ADD CONSTRAINT FK_Payment_Loan 
    FOREIGN KEY (LoanKey) REFERENCES fact.FACT_LOAN_ORIGINATION(LoanKey);
ALTER TABLE fact.FACT_PAYMENT_TRANSACTION ADD CONSTRAINT FK_Payment_PaymentDate 
    FOREIGN KEY (PaymentDateKey) REFERENCES dim.DimDate(DateKey);
ALTER TABLE fact.FACT_PAYMENT_TRANSACTION ADD CONSTRAINT FK_Payment_PaymentMethod 
    FOREIGN KEY (PaymentMethodKey) REFERENCES dim.DimPaymentMethod(PaymentMethodKey);
ALTER TABLE fact.FACT_PAYMENT_TRANSACTION ADD CONSTRAINT FK_Payment_PaymentType 
    FOREIGN KEY (PaymentTypeKey) REFERENCES dim.DimPaymentType(PaymentTypeKey);
GO

-- FACT_CUSTOMER_FINANCIALS
ALTER TABLE fact.FACT_CUSTOMER_FINANCIALS ADD CONSTRAINT FK_Financials_Customer 
    FOREIGN KEY (CustomerKey) REFERENCES dim.DimCustomer(CustomerKey);
ALTER TABLE fact.FACT_CUSTOMER_FINANCIALS ADD CONSTRAINT FK_Financials_StatementDate 
    FOREIGN KEY (StatementDateKey) REFERENCES dim.DimDate(DateKey);
ALTER TABLE fact.FACT_CUSTOMER_FINANCIALS ADD CONSTRAINT FK_Financials_StatementType 
    FOREIGN KEY (StatementTypeKey) REFERENCES dim.DimStatementType(StatementTypeKey);
GO

-- FACT_COVENANT_TEST
ALTER TABLE fact.FACT_COVENANT_TEST ADD CONSTRAINT FK_CovenantTest_Loan 
    FOREIGN KEY (LoanKey) REFERENCES fact.FACT_LOAN_ORIGINATION(LoanKey);
ALTER TABLE fact.FACT_COVENANT_TEST ADD CONSTRAINT FK_CovenantTest_TestDate 
    FOREIGN KEY (TestDateKey) REFERENCES dim.DimDate(DateKey);
ALTER TABLE fact.FACT_COVENANT_TEST ADD CONSTRAINT FK_CovenantTest_CovenantType 
    FOREIGN KEY (CovenantTypeKey) REFERENCES dim.DimCovenantType(CovenantTypeKey);
GO

-- FACT_CUSTOMER_INTERACTION
ALTER TABLE fact.FACT_CUSTOMER_INTERACTION ADD CONSTRAINT FK_Interaction_Customer 
    FOREIGN KEY (CustomerKey) REFERENCES dim.DimCustomer(CustomerKey);
ALTER TABLE fact.FACT_CUSTOMER_INTERACTION ADD CONSTRAINT FK_Interaction_InteractionDate 
    FOREIGN KEY (InteractionDateKey) REFERENCES dim.DimDate(DateKey);
ALTER TABLE fact.FACT_CUSTOMER_INTERACTION ADD CONSTRAINT FK_Interaction_Employee 
    FOREIGN KEY (EmployeeKey) REFERENCES dim.DimEmployee(EmployeeKey);
ALTER TABLE fact.FACT_CUSTOMER_INTERACTION ADD CONSTRAINT FK_Interaction_InteractionType 
    FOREIGN KEY (InteractionTypeKey) REFERENCES dim.DimInteractionType(InteractionTypeKey);
ALTER TABLE fact.FACT_CUSTOMER_INTERACTION ADD CONSTRAINT FK_Interaction_InteractionChannel 
    FOREIGN KEY (InteractionChannelKey) REFERENCES dim.DimInteractionChannel(ChannelKey);
GO

PRINT 'Phase 1: Fact tables created successfully!';
GO
