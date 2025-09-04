# Customer Intelligence Star Schema Extension (PoC)

Date: 2025-09-04  
Database: `Multi_Dimentional_Modeling` (SQL Server)  
Scope: Extend baseline customer interaction schema to support semantic task resolution & activation/personalization layers (inspired by Teradata Customer Intelligence Framework).

---
## 1. Objectives
- Add semantic-layer entities (tasks, issues, risk events, recommendations).
- Add activation-layer entities (actions, offers, performance, balance growth, engagement KPIs).
- Preserve star-schema friendliness (conformed dimensions + additive / semi-additive facts).
- Seed representative sample data to enable NL2SQL experimentation & prompt engineering.

---
## 2. Existing Base (Pre-Extension)
**Dimensions**: `Customer_Dimension`, `Product_Dimension`, `Channel_Dimension`, `Time_Dimension`, `Network_Dimension`  
**Facts**: `Interaction`, `Transaction_Payment`, `Service_Performance`

---
## 3. Minor Enhancements Applied
| Table | Added Columns | Purpose |
|-------|---------------|---------|
| `Customer_Dimension` | `LifecycleStage` | Model journey stage (Prospect, Active, At-Risk, etc.) |
| `Channel_Dimension`  | `IsPrimaryChannel` | Flag main engagement channel per customer segment |
| (Earlier) Several dims/facts | Behavioral / performance attributes | Greater realism for analytics |

---
## 4. New Dimension Tables
| Dimension | Key | Key Attributes (abridged) | Notes |
|-----------|-----|---------------------------|-------|
| `Task_Type_Dimension` | `TaskTypeID` | `TaskCategory`, `TaskName`, `IsRiskRelated` | Classifies customer tasks (transactional, advisory, etc.) |
| `Action_Dimension` | `ActionID` | `ActionName`, `ActionCategory`, `PriorityRank` | Represents possible activation / personalization actions |
| `Offer_Dimension` | `OfferID` | `OfferName`, `ProductID`, `OfferType`, `EligibilityRule`, `ValidFrom/To` | Cross/upsell or advisory offers |
| `Issue_Type_Dimension` | `IssueTypeID` | `IssueCategory`, `SeverityDefault`, `SLA_TargetMinutes` | Service & complaint taxonomy |
| `Risk_Event_Dimension` | `RiskEventID` | `RiskType`, `SubType`, `DefaultScoreWeight`, `EscalationThreshold` | Fraud/compliance drivers |
| `Recommendation_Reason_Dimension` | `ReasonID` | `TriggerType`, `Description`, `ModelVersion`, `ConfidenceBand` | Provenance & explainability of recs |

---
## 5. New Fact Tables
| Fact | Grain (Primary Key) | Foreign Keys | Core Measures / Attributes |
|------|---------------------|--------------|----------------------------|
| `FactCustomerTask` | `CustomerTaskID` (event) | Customer, TaskType, Time, Channel, Network | Status, duration, escalation, satisfaction |
| `FactServiceIssue` | `ServiceIssueID` (issue lifecycle) | Customer, IssueType, Time(open), TimeResolved, Channel | Severity, resolution mins, root cause |
| `FactRiskMitigation` | `RiskMitigationID` (detection) | Customer, RiskEvent, Time, Channel, Network | Raw & calibrated scores, action taken |
| `FactRecommendation` | `RecommendationID` (recommendation instance) | Customer, Action, Offer?, Reason, Time, ChannelPresented, ExpirationTime, AcceptanceTime | Priority, predicted value, confidence, acceptance flags |
| `FactOfferPerformance` | `OfferPerfID` (offer exposure) | Offer, Customer, Time, Channel | Impressions, clicks, conversion, attributed revenue |
| `FactBalanceBuild` | `BalanceBuildID` (period snapshot) | Customer, Product, Time | Starting/Ending, deposits, withdrawals, computed `NetChange` |
| `FactEngagementScore` | `EngagementScoreID` (period aggregate) | Customer, Time | InteractionCount, Tasks, Issues, RecommendationsAccepted, composite score |

---
## 6. Seeded Dimension Data (Representative)
### Task_Type_Dimension
1. Pay Bill (Transactional)  
2. Transfer Funds (Transactional)  
3. Open Dispute (Service Issue)  
4. Report Fraud (Risk, IsRiskRelated=1)  
5. Investment Inquiry (Advisory)

### Action_Dimension
1. Retention Outreach  
2. Offer Savings Upgrade  
3. Fraud Review  
4. Credit Limit Increase  
5. Advisory Appointment

### Offer_Dimension
| ID | Offer | Linked Product | Type | Eligibility (simplified) |
|----|-------|----------------|------|--------------------------|
| 1 | High Yield Savings Bonus | ProductID 3 | Cross-sell | Balance > 1000 |
| 2 | Auto Loan Refinance | ProductID 4 | Advisory | Existing auto loan & good credit |
| 3 | Premium Card Upgrade | ProductID 2 | Upsell | Credit score > 700 |

### Issue_Type_Dimension
Fee Dispute, Service Outage, Fraud Claim

### Risk_Event_Dimension
Fraud(Card Velocity), Fraud(GeoMismatch), Compliance(KYC Refresh)

### Recommendation_Reason_Dimension
Predictive Churn Model v1, Balance Threshold Trigger, Cross-Sell Propensity Model v2

---
## 7. Sample Fact Rows (Illustrative Subset)
### FactCustomerTask
| CustomerTaskID | CustomerID | TaskTypeID | Status | DurationSeconds | WasSelfService | Satisfaction |
|----------------|------------|-----------|--------|-----------------|----------------|--------------|
| 1 | 1 | 1 | Completed | 90 | 1 | 9 |
| 2 | 2 | 2 | Completed | 120 | 0 | 8 |
| 3 | 3 | 5 | InProgress | 300 | 1 | NULL |

### FactRecommendation (Acceptance Tracking)
| RecommendationID | CustomerID | ActionID | OfferID | ReasonID | Priority | PredValue | Conf | WasAccepted |
|------------------|------------|---------|--------|----------|---------|----------|------|-------------|
| 1 | 1 | 2 | 1 | 2 | 2 | 35.50 | 0.88 | 1 |
| 2 | 2 | 1 | NULL | 1 | 1 | 120.00 | 0.91 | 0 |
| 3 | 3 | 4 | 3 | 3 | 3 | 200.00 | 0.93 | 0 |

(Additional facts populated for risk, issues, offer performance, balance build, engagement score.)

---
## 8. Conceptual Usage Mapping
| Use Case | Primary Facts | Supporting Dims | Example Outcome |
|----------|---------------|-----------------|-----------------|
| Next Best Action | FactRecommendation | Action, Offer, Reason | Top prioritized actionable recs |
| Customer Retention | FactEngagementScore, FactRecommendation | Action, Reason | Flag at-risk + retention outreach |
| Product Cross-sell | FactRecommendation, Transaction_Payment | Product, Offer | Identify adoption gaps |
| Fraud Remediation | FactRiskMitigation | Risk_Event, Task_Type | Case creation, escalation flow |
| Service Issue SLA | FactServiceIssue | Issue_Type, Time | SLA compliance dashboard |
| Balance Growth | FactBalanceBuild | Product, Time | Track net balance change by strategy |

---
## 9. Sample Analytical Queries
```sql
-- A. Open high severity service issues
SELECT Severity, COUNT(*) AS OpenCount
FROM FactServiceIssue
WHERE Status = 'Open'
GROUP BY Severity;

-- B. Accepted recommendations by action
SELECT a.ActionName, COUNT(*) AS Accepted
FROM FactRecommendation r
JOIN Action_Dimension a ON r.ActionID = a.ActionID
WHERE r.WasAccepted = 1
GROUP BY a.ActionName;

-- C. Fraud mitigation actions distribution
SELECT re.RiskType, re.SubType, f.ActionTaken, COUNT(*) AS Cnt
FROM FactRiskMitigation f
JOIN Risk_Event_Dimension re ON f.RiskEventID = re.RiskEventID
GROUP BY re.RiskType, re.SubType, f.ActionTaken;

-- D. Offer conversion performance
SELECT o.OfferName,
       SUM(op.ImpressionCount) AS Impressions,
       SUM(op.ClickCount) AS Clicks,
       SUM(CASE WHEN op.ConversionFlag = 1 THEN 1 ELSE 0 END) AS Conversions
FROM FactOfferPerformance op
JOIN Offer_Dimension o ON op.OfferID = o.OfferID
GROUP BY o.OfferName;

-- E. Engagement composite score ranking
SELECT c.CustomerName, e.CompositeScore
FROM FactEngagementScore e
JOIN Customer_Dimension c ON e.CustomerID = c.CustomerID
ORDER BY e.CompositeScore DESC;
```

---
## 10. NL2SQL Integration Considerations
| Need | Approach |
|------|----------|
| Fact vs Dimension Recognition | Use naming heuristics (`Fact*`, `*_Dimension`) & FK discovery |
| Join Path Discovery | Build FK graph; prefer shortest path from driving fact to requested attributes |
| Aggregation Suggestions | Map metric-like columns (e.g. `Amount`, `KPI_Value`, `PredictedValue`) to SUM/AVG patterns |
| Semantic Synonyms | Maintain alias dictionary (e.g., "churn" -> `FactEngagementScore.CompositeScore` context) |
| Date Intelligence | Expand `Time_Dimension` (script) & add derived views (`vw_DailyActivity`) |

---
## 11. Recommended Next Steps
1. Populate full `Time_Dimension` (365+ days) & optionally a `Calendar_Dimension` view.
2. Add surrogate IDENTITY keys (avoid manual PK management) & keep natural keys as business attributes.
3. Create semantic views (e.g., `vw_Customer360`, `vw_ActionableRecommendations`).
4. Add CHECK constraints (e.g., `ConfidenceScore BETWEEN 0 AND 1`).
5. Build a prompt-oriented schema summary generator for NL2SQL pipeline.
6. Add Volume Scaling Script: parameterized insert loops for stress testing.
7. Implement lineage/usage logging when NL2SQL queries hit risk or recommendation facts.

---
## 12. Change Log
| Date | Change | Notes |
|------|--------|-------|
| 2025-09-04 | Initial extension created | Dimensions + facts + seed data |

---
## 13. Appendix: DDL (Abbreviated Example)
> Full DDL executed directly on SQL Server; regenerate via schema scripting if needed.

```sql
CREATE TABLE Task_Type_Dimension (...);
CREATE TABLE Action_Dimension (...);
CREATE TABLE Offer_Dimension (...);
CREATE TABLE Issue_Type_Dimension (...);
CREATE TABLE Risk_Event_Dimension (...);
CREATE TABLE Recommendation_Reason_Dimension (...);
CREATE TABLE FactCustomerTask (...);
-- etc.
```

---
**Maintainer Notes:** This file documents the current PoC modeling baseline. Any transformation logic, data generators, or NL2SQL schema summarizers should reference section 10 & 11 for roadmap alignment.
