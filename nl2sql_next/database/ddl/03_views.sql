-- ========================================================
-- RetailDW — Analytical Views
-- Convenience views for common query patterns
-- ========================================================

-- ========================================================
-- VIEW: vw_OrderSummary — denormalized order-level view
-- ========================================================
IF OBJECT_ID('dbo.vw_OrderSummary', 'V') IS NOT NULL DROP VIEW dbo.vw_OrderSummary;
GO

CREATE VIEW dbo.vw_OrderSummary AS
SELECT
    o.OrderId,
    o.LineNumber,
    d.[Date]            AS OrderDate,
    d.[Year]            AS OrderYear,
    d.Quarter           AS OrderQuarter,
    d.MonthName         AS OrderMonth,
    c.CustomerId,
    c.FirstName + ' ' + c.LastName AS CustomerName,
    c.Region            AS CustomerRegion,
    c.MembershipTier,
    p.ProductId,
    p.ProductName,
    p.Category          AS ProductCategory,
    p.Subcategory       AS ProductSubcategory,
    p.Brand,
    s.StoreName,
    s.StoreType,
    s.Region            AS StoreRegion,
    pr.PromotionName,
    pr.PromotionType,
    sm.MethodName       AS ShippingMethod,
    pm.MethodName       AS PaymentMethod,
    o.Quantity,
    o.UnitPrice,
    o.DiscountAmount,
    o.ShippingCost,
    o.TaxAmount,
    o.LineTotal,
    o.LineCost,
    o.LineProfit,
    o.OrderStatus,
    o.IsReturned
FROM fact.FactOrders o
JOIN dim.DimDate      d  ON o.OrderDateKey     = d.DateKey
JOIN dim.DimCustomer  c  ON o.CustomerKey      = c.CustomerKey
JOIN dim.DimProduct   p  ON o.ProductKey       = p.ProductKey
JOIN dim.DimStore     s  ON o.StoreKey         = s.StoreKey
LEFT JOIN dim.DimPromotion      pr ON o.PromotionKey     = pr.PromotionKey
LEFT JOIN dim.DimShippingMethod sm ON o.ShippingMethodKey = sm.ShippingMethodKey
LEFT JOIN dim.DimPaymentMethod  pm ON o.PaymentMethodKey  = pm.PaymentMethodKey;
GO

-- ========================================================
-- VIEW: vw_MonthlySales — aggregated monthly sales
-- ========================================================
IF OBJECT_ID('dbo.vw_MonthlySales', 'V') IS NOT NULL DROP VIEW dbo.vw_MonthlySales;
GO

CREATE VIEW dbo.vw_MonthlySales AS
SELECT
    d.[Year],
    d.[Month],
    d.MonthName,
    COUNT(DISTINCT o.OrderId)  AS OrderCount,
    SUM(o.Quantity)            AS TotalUnits,
    SUM(o.LineTotal)           AS TotalRevenue,
    SUM(o.LineCost)            AS TotalCost,
    SUM(o.LineProfit)          AS TotalProfit,
    SUM(o.DiscountAmount)      AS TotalDiscount,
    CAST(SUM(o.LineProfit) * 100.0 / NULLIF(SUM(o.LineTotal), 0) AS DECIMAL(5,2)) AS ProfitMarginPct
FROM fact.FactOrders o
JOIN dim.DimDate d ON o.OrderDateKey = d.DateKey
WHERE o.OrderStatus = 'Completed'
GROUP BY d.[Year], d.[Month], d.MonthName;
GO

-- ========================================================
-- VIEW: vw_ProductPerformance
-- ========================================================
IF OBJECT_ID('dbo.vw_ProductPerformance', 'V') IS NOT NULL DROP VIEW dbo.vw_ProductPerformance;
GO

CREATE VIEW dbo.vw_ProductPerformance AS
SELECT
    p.ProductId,
    p.ProductName,
    p.Category,
    p.Subcategory,
    p.Brand,
    COUNT(DISTINCT o.OrderId)  AS OrderCount,
    SUM(o.Quantity)            AS TotalUnitsSold,
    SUM(o.LineTotal)           AS TotalRevenue,
    SUM(o.LineProfit)          AS TotalProfit,
    AVG(r.Rating)              AS AvgRating,
    COUNT(r.ReviewKey)         AS ReviewCount,
    SUM(CAST(o.IsReturned AS INT)) AS ReturnCount,
    CAST(SUM(CAST(o.IsReturned AS INT)) * 100.0
         / NULLIF(COUNT(*), 0) AS DECIMAL(5,2)) AS ReturnRatePct
FROM dim.DimProduct p
LEFT JOIN fact.FactOrders         o ON p.ProductKey = o.ProductKey
LEFT JOIN fact.FactCustomerReview r ON p.ProductKey = r.ProductKey
GROUP BY p.ProductId, p.ProductName, p.Category, p.Subcategory, p.Brand;
GO

-- ========================================================
-- VIEW: vw_CustomerLifetimeValue
-- ========================================================
IF OBJECT_ID('dbo.vw_CustomerLifetimeValue', 'V') IS NOT NULL DROP VIEW dbo.vw_CustomerLifetimeValue;
GO

CREATE VIEW dbo.vw_CustomerLifetimeValue AS
SELECT
    c.CustomerKey,
    c.CustomerId,
    c.FirstName + ' ' + c.LastName AS CustomerName,
    c.Region,
    c.MembershipTier,
    COUNT(DISTINCT o.OrderId)  AS TotalOrders,
    SUM(o.LineTotal)           AS LifetimeRevenue,
    SUM(o.LineProfit)          AS LifetimeProfit,
    MIN(d.[Date])              AS FirstOrderDate,
    MAX(d.[Date])              AS LastOrderDate,
    DATEDIFF(DAY, MIN(d.[Date]), MAX(d.[Date])) AS CustomerTenureDays,
    AVG(o.LineTotal)           AS AvgOrderValue
FROM dim.DimCustomer c
JOIN fact.FactOrders o ON c.CustomerKey = o.CustomerKey
JOIN dim.DimDate     d ON o.OrderDateKey = d.DateKey
WHERE o.OrderStatus = 'Completed'
GROUP BY c.CustomerKey, c.CustomerId, c.FirstName, c.LastName, c.Region, c.MembershipTier;
GO

PRINT 'Phase 3 — Views created successfully.';
GO
