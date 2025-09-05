# NL2SQL Schema Summary (Multi_Dimentional_Modeling)

This summary is optimized for NL2SQL generation: concise naming, join keys, semantic role hints.

## Core Dimensions
- Customer_Dimension (PK: CustomerID)
  - Natural keys: CustomerName
  - Descriptive: Gender, Age, Country, Segment, LifecycleStage
  - Activity linkage: many facts via CustomerID
- Product_Dimension (PK: ProductID)
  - Category, IsActive, LaunchDate
- Channel_Dimension (PK: ChannelID)
  - ChannelType (Web, Mobile, Branch, CallCenter), IsPrimaryChannel
- Time_Dimension (PK: TimeID)
  - Date, Month, Quarter, Year, DayOfWeek, WeekOfYear, IsWeekend
  - Use as time grain surrogate for facts; supports multiple time roles (open, resolved, acceptance, expiration)
- Network_Dimension (PK: NetworkID)
  - NetworkName, NetworkType, Region

## Semantic / Activation Dimensions
- Task_Type_Dimension (PK: TaskTypeID) ComplexityLevel
- Action_Dimension (PK: ActionID) ActionCategory, IsAutomated
- Offer_Dimension (PK: OfferID, FK ProductID) StartDate/EndDate windows
- Issue_Type_Dimension (PK: IssueTypeID) IssueCategory, IssueDescription
- Risk_Event_Dimension (PK: RiskEventID) RiskCategory, RiskDescription, RiskOwner
- Recommendation_Reason_Dimension (PK: ReasonID) ReasonCategory, ReasonDescription

## Fact Tables (Grains)
- Interaction (InteractionID) one row per customer-channel-network-time interaction session
  - FK: CustomerID, TimeID, ChannelID, NetworkID
  - Metrics: SessionDurationSeconds, SatisfactionScore
  - Descriptive: Outcome, DeviceType
- Transaction_Payment (TransactionID) one row per financial transaction
  - FK: CustomerID, ProductID, TimeID, ChannelID, NetworkID
  - Metrics: Amount
  - Flags / attrs: PaymentMethod, Status, IsRefunded
- Service_Performance (ServicePerfID) performance snapshot per customer-channel-time
  - FK: CustomerID, ChannelID, TimeID
  - Metrics: ResponseTimeMs, AvailabilityPercent, ErrorRatePercent, SatisfactionScore
- FactCustomerTask (CustomerTaskID) customer completing a task
  - FK: CustomerID, TaskTypeID, TimeID, NetworkID, ChannelID
  - Metrics: CompletionTimeSeconds, SuccessFlag
- FactServiceIssue (ServiceIssueID) support / incident ticket life-cycle
  - FK: CustomerID, IssueTypeID, TimeID (opened), TimeResolvedID (resolved), ChannelID
  - Metrics: ResolutionTimeMinutes
  - Status / Severity: Severity, Status, RootCauseCategory
- FactRiskMitigation (RiskMitigationID) risk event tracking instance
  - FK: CustomerID, RiskEventID, TimeID, ChannelID, NetworkID
  - Metrics: MitigationProgressPercent, CalibratedScore
  - Severity & Actions: Severity, MitigationAction, OutcomeStatus
- FactRecommendation (RecommendationID) recommendation exposure instance
  - FK: CustomerID, OfferID, ActionID, ReasonID, TimeID (shown), AcceptanceTimeID, ExpirationTimeID, ChannelPresentedID
  - Flags: WasAcceptedFlag, WasExpiredFlag
- FactOfferPerformance (OfferPerfID) per customer-offer impression period
  - FK: CustomerID, OfferID, TimeID, ChannelID
  - Metrics: ImpressionCount, ClickCount, ConversionCount, RevenueAttributed
- FactBalanceBuild (BalanceBuildID) periodic balance snapshot per customer-product-time
  - FK: CustomerID, ProductID, TimeID
  - Metrics: StartingBalance, EndingBalance, NetChange
- FactEngagementScore (EngagementScoreID) derived engagement KPIs per customer-time
  - FK: CustomerID, TimeID
  - Metrics: InteractionCount, AverageSatisfactionScore, NetPromoterScore, EngagementScore

## Analytical Views
- vw_Customer360: Consolidated customer profile & aggregated KPIs (join Customer_Dimension + multiple fact aggregates)
- vw_RecommendationPipeline: Lifecycle metrics of recommendations (FactRecommendation + Offer + Action + Channel)
- vw_RiskAlerts: High severity or aging risk mitigation items needing escalation
- vw_ServiceIssueSLA: SLA evaluation overlay for service issues (elapsed vs severity target)

## Time Role Handling
Multiple foreign keys to Time_Dimension (TimeID, AcceptanceTimeID, ExpirationTimeID, TimeResolvedID) require aliasing. For NL2SQL generation create role labels:
- TimeID => EventTime / OccurrenceTime
- AcceptanceTimeID => AcceptanceTime
- ExpirationTimeID => ExpirationTime
- TimeResolvedID => ResolvedTime

## Join Patterns (Canonical)
- Customer facts: FactX.CustomerID = Customer_Dimension.CustomerID
- Product: Fact.ProductID = Product_Dimension.ProductID
- Channel: Fact.ChannelID or ChannelPresentedID = Channel_Dimension.ChannelID
- Time: Fact.TimeID = Time_Dimension.TimeID (+ additional time roles as needed)
- Offer: FactRecommendation.OfferID OR FactOfferPerformance.OfferID = Offer_Dimension.OfferID
- Offer->Product: Offer_Dimension.ProductID = Product_Dimension.ProductID
- Risk: FactRiskMitigation.RiskEventID = Risk_Event_Dimension.RiskEventID
- Issue: FactServiceIssue.IssueTypeID = Issue_Type_Dimension.IssueTypeID
- Task: FactCustomerTask.TaskTypeID = Task_Type_Dimension.TaskTypeID

## Semantic Role Hints (for NL queries)
- "engagement" -> FactEngagementScore (EngagementScore, InteractionCount, AverageSatisfactionScore)
- "balance" or "net change" -> FactBalanceBuild (NetChange)
- "risk" / "mitigation" / "escalation" -> FactRiskMitigation & vw_RiskAlerts
- "offer performance" / "impressions" / "clicks" / "conversions" -> FactOfferPerformance
- "recommendation" / "accepted" / "expired" -> FactRecommendation & vw_RecommendationPipeline
- "issue" / "ticket" / "SLA" -> FactServiceIssue & vw_ServiceIssueSLA
- "task completion" / "success" -> FactCustomerTask
- "service availability" / "error rate" / "response time" -> Service_Performance
- "transaction" / "payment" / "refund" -> Transaction_Payment
- "interaction" / "session" / "device" -> Interaction

## Example NL2SQL Mapping Snippets
1. "Average response time last quarter by primary channel":
   - Use Service_Performance join Channel_Dimension (IsPrimaryChannel=1) filter Time_Dimension.Quarter, Year
2. "Top 5 offers by conversion rate this month":
   - FactOfferPerformance (ConversionCount / NULLIF(ClickCount,0)) order desc limit 5, filter Time_Dimension.Month
3. "Customers with high risk needing escalation":
   - vw_RiskAlerts WHERE NeedsEscalation=1
4. "SLA breach count by severity":
   - vw_ServiceIssueSLA WHERE IsSLABreached=1 GROUP BY Severity
5. "Net balance change by product category YTD":
   - FactBalanceBuild join Product_Dimension filter Time_Dimension.Year and sum(NetChange)

## Index & Optimization Suggestions (Next Steps)
- Add nonclustered indexes on all FK columns (e.g., FactRecommendation(CustomerID), (OfferID), (TimeID), (ChannelPresentedID))
- Composite indexes for high-frequency filters: Service_Performance(TimeID, ChannelID), FactOfferPerformance(OfferID, TimeID)
- Date range queries: index Time_Dimension(Date)
- Pre-aggregate materialized tables for EngagementScore if query latency high

## Mermaid Diagram
See `schema_er.mmd` for ER representation.

## PDF Export Instructions
If Mermaid CLI is installed:
`mmdc -i star_schema_poc/schema_er.mmd -o star_schema_poc/schema_er.pdf -t neutral`
Or VS Code: Open `.mmd` preview → Export → PDF.

## Coverage Status
All created dimension, fact, and view objects captured. Multiple time role FKs enumerated. Suitable for feeding into NL2SQL prompt engineering as a compact schema dictionary.
