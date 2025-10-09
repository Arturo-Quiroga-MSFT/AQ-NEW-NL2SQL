-- ========================================
-- TERADATA-FI Sample Demo Queries
-- Phase 1: Dimension-Only Queries
-- ========================================
-- These queries demonstrate the power of the star schema
-- even with just dimension data populated.
-- ========================================

USE [TERADATA-FI];
GO

-- ========================================
-- 1. CUSTOMER SEGMENTATION ANALYSIS
-- ========================================

-- Q1: How many customers do we have by segment and tier?
SELECT 
    CustomerSegment,
    CustomerTier,
    COUNT(*) AS CustomerCount,
    AVG(AnnualRevenue) AS AvgRevenue,
    AVG(EmployeeCount) AS AvgEmployees
FROM dim.DimCustomer
WHERE IsCurrent = 1
GROUP BY CustomerSegment, CustomerTier
ORDER BY CustomerSegment, CustomerTier;

-- Q2: Show customer distribution by risk rating
SELECT 
    InternalRiskRating,
    COUNT(*) AS CustomerCount,
    AVG(AnnualRevenue) AS AvgRevenue,
    COUNT(CASE WHEN IsHighRisk = 1 THEN 1 END) AS HighRiskCount,
    COUNT(CASE WHEN IsVIP = 1 THEN 1 END) AS VIPCount
FROM dim.DimCustomer
WHERE IsCurrent = 1
GROUP BY InternalRiskRating
ORDER BY InternalRiskRating;

-- Q3: Find all VIP customers in the Corporate segment
SELECT 
    CustomerKey,
    CustomerId,
    CompanyName,
    CustomerTier,
    InternalRiskRating,
    AnnualRevenue,
    EmployeeCount,
    YEAR(GETDATE()) - YearFounded AS YearsInBusiness
FROM dim.DimCustomer
WHERE IsCurrent = 1
    AND IsVIP = 1
    AND CustomerSegment = 'Corporate'
ORDER BY AnnualRevenue DESC;

-- ========================================
-- 2. INDUSTRY ANALYSIS
-- ========================================

-- Q4: What industries do we serve and what are their risk profiles?
SELECT 
    IndustrySector,
    IndustryName,
    RiskProfile,
    DefaultRate_Historical,
    RecoveryRate_Historical,
    CASE 
        WHEN IsRegulated = 1 THEN 'Regulated'
        ELSE 'Unregulated'
    END AS RegulatoryStatus,
    CASE 
        WHEN IsVolatile = 1 THEN 'Volatile'
        ELSE 'Stable'
    END AS Volatility
FROM dim.DimIndustry
ORDER BY DefaultRate_Historical DESC;

-- Q5: Calculate expected loss by industry
SELECT 
    IndustrySector,
    IndustryName,
    DefaultRate_Historical AS PD,
    LGD_Probability AS LGD,
    (DefaultRate_Historical * LGD_Probability) AS ExpectedLoss_Rate,
    CASE 
        WHEN (DefaultRate_Historical * LGD_Probability) < 0.01 THEN 'Low Risk'
        WHEN (DefaultRate_Historical * LGD_Probability) < 0.025 THEN 'Medium Risk'
        ELSE 'High Risk'
    END AS RiskCategory
FROM dim.DimIndustry
ORDER BY ExpectedLoss_Rate DESC;

-- ========================================
-- 3. PRODUCT CATALOG ANALYSIS
-- ========================================

-- Q6: Show all active loan products with key features
SELECT 
    ProductName,
    ProductCategory,
    FORMAT(MinAmount, 'C', 'en-US') AS MinAmount,
    FORMAT(MaxAmount, 'C', 'en-US') AS MaxAmount,
    MinTerm AS MinTermMonths,
    MaxTerm AS MaxTermMonths,
    BaseRateType,
    ReferenceRateType,
    CAST(MarginBps AS DECIMAL(6,2)) / 100 AS Margin_Percent,
    CASE 
        WHEN RequiresCollateral = 1 THEN 'Yes'
        ELSE 'No'
    END AS RequiresCollateral,
    CASE 
        WHEN RequiresPersonalGuarantee = 1 THEN 'Yes'
        ELSE 'No'
    END AS RequiresPersonalGuarantee,
    PrepaymentPenaltyPercent
FROM dim.DimLoanProduct
WHERE IsActive = 1
ORDER BY ProductCategory, ProductName;

-- Q7: Compare fixed vs variable rate products
SELECT 
    BaseRateType,
    COUNT(*) AS ProductCount,
    AVG(MinAmount) AS AvgMinAmount,
    AVG(MaxAmount) AS AvgMaxAmount,
    AVG(CAST(MarginBps AS FLOAT)) AS AvgMarginBps,
    AVG(MinTerm) AS AvgMinTerm,
    AVG(MaxTerm) AS AvgMaxTerm
FROM dim.DimLoanProduct
WHERE IsActive = 1
GROUP BY BaseRateType;

-- ========================================
-- 4. RISK RATING FRAMEWORK
-- ========================================

-- Q8: Show complete risk rating scale with CECL provisions
SELECT 
    RiskRatingCode,
    RiskRatingName,
    RiskCategory,
    NumericScore,
    CAST(PD_Probability * 100 AS DECIMAL(6,2)) AS PD_Percent,
    CAST(LGD_Probability * 100 AS DECIMAL(6,2)) AS LGD_Percent,
    CAST((PD_Probability * LGD_Probability) * 100 AS DECIMAL(6,2)) AS ExpectedLoss_Percent,
    CAST(RequiredProvision_Percent * 100 AS DECIMAL(6,2)) AS CECL_Provision_Percent
FROM dim.DimRiskRating
ORDER BY NumericScore DESC;

-- Q9: Calculate CECL reserve requirements by rating
SELECT 
    RiskCategory,
    COUNT(*) AS RatingCount,
    AVG(PD_Probability) AS AvgPD,
    AVG(LGD_Probability) AS AvgLGD,
    AVG(RequiredProvision_Percent) AS AvgProvisionRate
FROM dim.DimRiskRating
GROUP BY RiskCategory
ORDER BY AvgProvisionRate DESC;

-- ========================================
-- 5. TEMPORAL ANALYSIS (Date Dimension)
-- ========================================

-- Q10: Show fiscal calendar mapping for Q1 2025
SELECT 
    [Date],
    DayName,
    [Year] AS CalendarYear,
    Quarter AS CalendarQuarter,
    FiscalYear,
    FiscalQuarter,
    FiscalMonth,
    CASE 
        WHEN IsWeekend = 1 THEN 'Weekend'
        WHEN IsHoliday = 1 THEN 'Holiday'
        ELSE 'Business Day'
    END AS DayType,
    CASE 
        WHEN IsQuarterEnd = 1 THEN 'Quarter End'
        WHEN IsMonthEnd = 1 THEN 'Month End'
        WHEN IsYearEnd = 1 THEN 'Year End'
        ELSE ''
    END AS SpecialDate
FROM dim.DimDate
WHERE [Year] = 2025 AND Quarter = 1
ORDER BY [Date];

-- Q11: Count business days by month for 2025
SELECT 
    [Year],
    [Month],
    MonthName,
    COUNT(*) AS TotalDays,
    SUM(CASE WHEN IsWeekend = 0 AND IsHoliday = 0 THEN 1 ELSE 0 END) AS BusinessDays,
    SUM(CASE WHEN IsWeekend = 1 THEN 1 ELSE 0 END) AS WeekendDays
FROM dim.DimDate
WHERE [Year] = 2025
GROUP BY [Year], [Month], MonthName
ORDER BY [Month];

-- ========================================
-- 6. DELINQUENCY STATUS FRAMEWORK
-- ========================================

-- Q12: Show complete delinquency aging buckets
SELECT 
    StatusCode,
    StatusName,
    MinDaysDelinquent,
    MaxDaysDelinquent,
    CASE 
        WHEN IsPerforming = 1 THEN 'Performing'
        WHEN IsNonPerforming = 1 THEN 'Non-Performing'
        ELSE 'Other'
    END AS PerformanceStatus,
    CASE 
        WHEN RequiresRestructuring = 1 THEN 'Yes'
        ELSE 'No'
    END AS RequiresRestructuring
FROM dim.DimDelinquencyStatus
ORDER BY MinDaysDelinquent;

-- ========================================
-- 7. APPLICATION STATUS WORKFLOW
-- ========================================

-- Q13: Show application status workflow
SELECT 
    StatusCode,
    StatusName,
    StatusCategory,
    SortOrder,
    CASE 
        WHEN IsActive = 1 THEN 'Active/Pending'
        ELSE 'Inactive'
    END AS State,
    CASE 
        WHEN IsTerminal = 1 THEN 'Final State'
        ELSE 'In Progress'
    END AS Finality
FROM dim.DimApplicationStatus
ORDER BY SortOrder;

-- ========================================
-- 8. PAYMENT METHODS & PROCESSING
-- ========================================

-- Q14: Compare payment methods by cost and speed
SELECT 
    MethodName,
    MethodDescription,
    FORMAT(ProcessingFee, 'C', 'en-US') AS ProcessingFee,
    ProcessingDays,
    CASE 
        WHEN IsElectronic = 1 THEN 'Electronic'
        ELSE 'Manual'
    END AS ProcessingType,
    CASE 
        WHEN ProcessingDays = 0 THEN 'Same Day'
        WHEN ProcessingDays = 1 THEN 'Next Day'
        ELSE CAST(ProcessingDays AS VARCHAR) + ' Days'
    END AS DeliveryTime
FROM dim.DimPaymentMethod
ORDER BY ProcessingDays, ProcessingFee;

-- ========================================
-- 9. MULTI-DIMENSIONAL ANALYSIS (Joins)
-- ========================================

-- Q15: Customer profile with industry risk correlation
-- (Demonstrates star schema join capability)
SELECT 
    c.CompanyName,
    c.CustomerSegment,
    c.CustomerTier,
    c.InternalRiskRating,
    c.AnnualRevenue,
    c.EmployeeCount,
    c.LegalEntityType,
    YEAR(GETDATE()) - c.YearFounded AS YearsInBusiness
FROM dim.DimCustomer c
WHERE c.IsCurrent = 1
    AND c.CustomerSegment = 'Middle Market'
    AND c.InternalRiskRating IN ('A', 'BBB', 'BB')
ORDER BY c.AnnualRevenue DESC;

-- Q16: Risk rating alignment with customer segments
-- (Shows how different customer segments map to risk ratings)
SELECT 
    c.CustomerSegment,
    c.InternalRiskRating,
    COUNT(*) AS CustomerCount,
    AVG(c.AnnualRevenue) AS AvgRevenue,
    MIN(c.AnnualRevenue) AS MinRevenue,
    MAX(c.AnnualRevenue) AS MaxRevenue
FROM dim.DimCustomer c
WHERE c.IsCurrent = 1
GROUP BY c.CustomerSegment, c.InternalRiskRating
ORDER BY c.CustomerSegment, c.InternalRiskRating;

-- ========================================
-- 10. DATA QUALITY CHECKS
-- ========================================

-- Q17: Verify dimension table record counts
SELECT 'DimDate' AS Dimension, COUNT(*) AS RecordCount FROM dim.DimDate
UNION ALL
SELECT 'DimCustomer', COUNT(*) FROM dim.DimCustomer WHERE IsCurrent = 1
UNION ALL
SELECT 'DimIndustry', COUNT(*) FROM dim.DimIndustry
UNION ALL
SELECT 'DimLoanProduct', COUNT(*) FROM dim.DimLoanProduct
UNION ALL
SELECT 'DimRiskRating', COUNT(*) FROM dim.DimRiskRating
UNION ALL
SELECT 'DimDelinquencyStatus', COUNT(*) FROM dim.DimDelinquencyStatus
UNION ALL
SELECT 'DimApplicationStatus', COUNT(*) FROM dim.DimApplicationStatus
UNION ALL
SELECT 'DimPaymentMethod', COUNT(*) FROM dim.DimPaymentMethod
UNION ALL
SELECT 'DimPaymentType', COUNT(*) FROM dim.DimPaymentType
ORDER BY Dimension;

-- Q18: Check for NULL values in critical customer fields
SELECT 
    'CompanyName' AS FieldName,
    COUNT(CASE WHEN CompanyName IS NULL THEN 1 END) AS NullCount
FROM dim.DimCustomer WHERE IsCurrent = 1
UNION ALL
SELECT 'CustomerSegment', COUNT(CASE WHEN CustomerSegment IS NULL THEN 1 END)
FROM dim.DimCustomer WHERE IsCurrent = 1
UNION ALL
SELECT 'InternalRiskRating', COUNT(CASE WHEN InternalRiskRating IS NULL THEN 1 END)
FROM dim.DimCustomer WHERE IsCurrent = 1;

-- Q19: Verify date dimension coverage
SELECT 
    MIN([Date]) AS StartDate,
    MAX([Date]) AS EndDate,
    DATEDIFF(DAY, MIN([Date]), MAX([Date])) + 1 AS TotalDays,
    COUNT(*) AS RecordCount,
    CASE 
        WHEN DATEDIFF(DAY, MIN([Date]), MAX([Date])) + 1 = COUNT(*) THEN 'Complete'
        ELSE 'Missing Dates'
    END AS DataQuality
FROM dim.DimDate;

-- Q20: Check SCD Type 2 implementation (should all be IsCurrent = 1 in Phase 1)
SELECT 
    IsCurrent,
    COUNT(*) AS CustomerCount,
    COUNT(DISTINCT CustomerId) AS UniqueCustomerIds
FROM dim.DimCustomer
GROUP BY IsCurrent;

-- ========================================
-- NOTES FOR PHASE 2
-- ========================================
-- Once fact tables are populated, you can run queries like:
-- 
-- - Loan origination volume by product and branch
-- - Approval rates by customer segment and risk rating
-- - Payment performance analysis by delinquency bucket
-- - Covenant compliance rates by loan type
-- - CRM interaction analysis by customer tier
-- - Daily balance trends and portfolio growth
-- - Application funnel conversion rates
-- 
-- These dimension-only queries demonstrate the schema design
-- and prepare you for much more powerful analytics once
-- fact data is loaded in Phase 2.
-- ========================================

PRINT 'Sample queries completed successfully!';
GO
