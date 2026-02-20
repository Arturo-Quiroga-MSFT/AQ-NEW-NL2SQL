"""Few-shot examples for the NL2SQL prompt.

Each example is a (question, sql) pair drawn from the RetailDW schema.
They teach the LLM common patterns: JOINs, aggregation, date filtering,
views vs raw tables, CTEs, TOP N, etc.
"""
from __future__ import annotations

EXAMPLES: list[dict[str, str]] = [
    {
        "question": "What are the top 10 products by total revenue?",
        "sql": (
            "SELECT TOP 10 ProductId, ProductName, Category, Brand, TotalRevenue\n"
            "FROM dbo.vw_ProductPerformance\n"
            "ORDER BY TotalRevenue DESC"
        ),
    },
    {
        "question": "Show monthly sales totals for 2024",
        "sql": (
            "SELECT Year, Month, MonthName, OrderCount, TotalRevenue, TotalProfit\n"
            "FROM dbo.vw_MonthlySales\n"
            "WHERE Year = 2024\n"
            "ORDER BY Month"
        ),
    },
    {
        "question": "Which customers spent the most overall?",
        "sql": (
            "SELECT TOP 10 CustomerId, FullName, TotalOrders, TotalSpent, AvgOrderValue\n"
            "FROM dbo.vw_CustomerLifetimeValue\n"
            "ORDER BY TotalSpent DESC"
        ),
    },
    {
        "question": "How many orders were placed per store last month?",
        "sql": (
            "SELECT s.StoreName, s.City, s.State, COUNT(DISTINCT o.OrderId) AS OrderCount\n"
            "FROM fact.FactOrders o\n"
            "JOIN dim.DimStore s ON o.StoreKey = s.StoreKey\n"
            "JOIN dim.DimDate d ON o.OrderDateKey = d.DateKey\n"
            "WHERE d.Year = YEAR(DATEADD(MONTH, -1, GETDATE()))\n"
            "  AND d.Month = MONTH(DATEADD(MONTH, -1, GETDATE()))\n"
            "GROUP BY s.StoreName, s.City, s.State\n"
            "ORDER BY OrderCount DESC"
        ),
    },
    {
        "question": "What is the return rate by product category?",
        "sql": (
            "WITH OrdersByCategory AS (\n"
            "    SELECT p.Category, COUNT(DISTINCT o.OrderId) AS TotalOrders\n"
            "    FROM fact.FactOrders o\n"
            "    JOIN dim.DimProduct p ON o.ProductKey = p.ProductKey\n"
            "    GROUP BY p.Category\n"
            "),\n"
            "ReturnsByCategory AS (\n"
            "    SELECT p.Category, COUNT(*) AS TotalReturns\n"
            "    FROM fact.FactReturns r\n"
            "    JOIN dim.DimProduct p ON r.ProductKey = p.ProductKey\n"
            "    GROUP BY p.Category\n"
            ")\n"
            "SELECT o.Category,\n"
            "       o.TotalOrders,\n"
            "       ISNULL(r.TotalReturns, 0) AS TotalReturns,\n"
            "       CAST(ISNULL(r.TotalReturns, 0) * 100.0 / o.TotalOrders AS DECIMAL(5,2)) AS ReturnRatePct\n"
            "FROM OrdersByCategory o\n"
            "LEFT JOIN ReturnsByCategory r ON o.Category = r.Category\n"
            "ORDER BY ReturnRatePct DESC"
        ),
    },
    {
        "question": "Which products are low in stock?",
        "sql": (
            "SELECT p.ProductId, p.ProductName, p.Category, i.StockLevel, i.ReorderPoint\n"
            "FROM dbo.vw_InventoryStatus i\n"
            "JOIN dim.DimProduct p ON i.ProductKey = p.ProductKey\n"
            "WHERE i.StockLevel < i.ReorderPoint\n"
            "ORDER BY i.StockLevel ASC"
        ),
    },
]


def format_few_shots() -> str:
    """Format examples for injection into the system prompt."""
    lines = ["EXAMPLES:"]
    for i, ex in enumerate(EXAMPLES, 1):
        lines.append(f"\nExample {i}:")
        lines.append(f"Question: {ex['question']}")
        lines.append(f"SQL:\n{ex['sql']}")
    return "\n".join(lines)
