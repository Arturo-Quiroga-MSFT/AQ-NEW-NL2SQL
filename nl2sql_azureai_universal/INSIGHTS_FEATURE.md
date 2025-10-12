# Data Insights Feature Documentation

## Overview

The NL2SQL Teams Bot now includes a **third AI agent** dedicated to generating business insights from query results. This mirrors the intelligence layer present in the original Streamlit UI.

## Three-Agent Architecture

### 1. Intent Extraction Agent
- **Purpose**: Convert natural language to structured intent JSON
- **Input**: User's natural language query
- **Output**: JSON with tables, columns, filters, aggregations
- **Example**: "Show top 5 customers" → `{"table": "customers", "limit": 5, "sort": "desc"}`

### 2. SQL Generation Agent
- **Purpose**: Generate executable SQL from intent + schema context
- **Input**: Intent JSON + database schema
- **Output**: Clean, executable SQL query
- **Example**: Intent → `SELECT TOP 5 customer_id, name, total_revenue FROM customers ORDER BY total_revenue DESC`

### 3. Data Insights Agent ⭐ **NEW**
- **Purpose**: Analyze query results and provide business intelligence
- **Input**: Query results + original question + executed SQL
- **Output**: 3-5 concise business insights with emoji indicators
- **Example**: 
  - 📊 Top 5 customers represent $2.5M in revenue (45% of total)
  - 📈 Revenue concentrated in CA and NY states
  - ⚠️ 2 customers showing delinquency patterns
  - 💡 Opportunity to expand in underrepresented regions

## Emoji Indicator System

The insights agent uses visual indicators for quick comprehension:

| Emoji | Meaning | Example Use Case |
|-------|---------|------------------|
| 📊 | Statistics/Overview | "Total rows returned: 156" |
| 📈 | Growth/Increase | "Sales up 23% vs last quarter" |
| 📉 | Decline/Decrease | "Customer retention down 5%" |
| ⚠️ | Warning/Concern | "3 accounts past due >90 days" |
| ✅ | Positive/Success | "All targets met or exceeded" |
| 💡 | Recommendation | "Consider increasing credit limits" |
| 🎯 | Key Takeaway | "Focus on high-value segments" |
| 🔍 | Observation | "Unusual pattern in Q3 data" |

## Implementation Details

### Code Structure

#### 1. Agent Creation (`nl2sql_main.py`)
```python
_INSIGHTS_AGENT_ID = None

def _get_or_create_insights_agent() -> str:
    """Create or retrieve persistent insights agent."""
    if _INSIGHTS_AGENT_ID is None:
        agent = project_client.agents.create_agent(
            model=MODEL_DEPLOYMENT_NAME,
            name="data-insights-persistent",
            instructions="""Expert data analyst providing business insights.
            
            Analyze query results for patterns, trends, anomalies.
            Provide 3-5 concise insights (one sentence each).
            Use emoji indicators: 📊📈📉⚠️✅💡🎯🔍
            Focus on business value and actionable observations."""
        )
        _INSIGHTS_AGENT_ID = agent.id
    return _INSIGHTS_AGENT_ID
```

#### 2. Insights Generation (`nl2sql_main.py`)
```python
def generate_insights(results: Dict[str, Any], query: str, sql: str) -> str:
    """
    Generate business insights from query results.
    
    Process:
    1. Create dedicated thread for insights
    2. Format results summary (query context + data sample)
    3. Send to insights agent
    4. Extract and return formatted insights
    """
```

#### 3. Pipeline Integration (`nl2sql_main.py`)
```python
def process_nl_query(query: str, execute: bool = True, thread_id: Optional[str] = None):
    # Step 1: Extract intent
    intent, thread_id = extract_intent(query, thread_id)
    
    # Step 2: Generate SQL
    sql, thread_id = generate_sql(intent, thread_id)
    
    # Step 3: Execute SQL
    results = execute_and_format(sql)
    
    # Step 4: Generate insights ⭐ NEW
    if results.get("success") and results.get("rows"):
        insights = generate_insights(results, query, sql)
        response["insights"] = insights
```

#### 4. Adaptive Card Display (`adaptive_cards.py`)
```python
def create_success_card(
    sql: str,
    results: Dict[str, Any],
    insights: Optional[str] = None,  # ⭐ NEW parameter
    ...
):
    # ... SQL and results sections ...
    
    # Insights Section
    if insights:
        insights_container = {
            "type": "Container",
            "spacing": "medium",
            "style": "emphasis",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "💡 Business Insights",
                    "weight": "bolder",
                    "size": "medium",
                    "color": "accent"
                },
                {
                    "type": "TextBlock",
                    "text": insights,
                    "wrap": True
                }
            ]
        }
        card["body"].append(insights_container)
```

#### 5. Teams Bot Integration (`teams_nl2sql_agent.py`)
```python
# Pass insights from pipeline to card builder
card = AdaptiveCardBuilder.create_success_card(
    sql=result.get("sql"),
    results=result.get("results"),
    insights=result.get("insights"),  # ⭐ NEW
    ...
)
```

## Agent Instructions

The insights agent receives detailed instructions to ensure high-quality output:

```
You are an expert data analyst providing business insights on query results.

INSTRUCTIONS:
1. Analyze the query results for:
   - Patterns and trends
   - Statistical significance
   - Anomalies or outliers
   - Business implications

2. Provide 3-5 concise insights (one sentence each)

3. Use emoji indicators:
   📊 Statistics/data overview
   📈 Growth/positive trends
   📉 Decline/negative trends
   ⚠️ Warnings/concerns
   ✅ Positive outcomes
   💡 Recommendations/opportunities
   🎯 Key takeaways
   🔍 Observations

4. Focus on business value, not technical details

5. Each insight should be:
   - Concise (one sentence)
   - Actionable or informative
   - Relevant to the query context

EXAMPLE:
Query: "Show top 5 customers by revenue"
Insights:
📊 Top 5 customers represent $2.5M in total revenue
📈 Customer #1 grew 45% over last quarter
⚠️ Customer #3 has payment delays (30+ days)
💡 Consider loyalty program for top tier
🎯 Revenue concentration in CA and NY
```

## Data Flow

```
User Query → Intent Agent → SQL Agent → Execute SQL → Results
                                              ↓
                                      Insights Agent
                                              ↓
                                    Business Insights
                                              ↓
                                      Adaptive Card
                                              ↓
                                      Teams User
```

## Example Scenarios

### Scenario 1: Customer Revenue Query
**User Query**: "Show me the top 10 customers by revenue"

**Generated Insights**:
- 📊 Top 10 customers generated $4.2M in revenue (38% of total)
- 📈 Average revenue per customer: $420K
- 🎯 Revenue heavily concentrated in top 3 customers ($2.1M)
- ⚠️ 2 top customers have declining quarterly trends
- 💡 Consider diversification strategy to reduce concentration risk

### Scenario 2: Product Sales Analysis
**User Query**: "What are total sales by product category?"

**Generated Insights**:
- 📊 5 product categories analyzed with $12.5M total sales
- 📈 Electronics category leads with 42% market share
- 📉 Office supplies down 15% year-over-year
- ✅ 3 categories exceeded quarterly targets
- 💡 Opportunity to invest in Electronics inventory

### Scenario 3: Geographic Distribution
**User Query**: "Show customer count by state"

**Generated Insights**:
- 📊 Customers distributed across 28 states
- 🎯 CA, TX, NY represent 55% of customer base
- 🔍 Midwest region shows low penetration (8%)
- 💡 Expansion opportunity in underserved markets
- 📈 Southern states showing 23% growth rate

## Error Handling

The insights feature is designed to be **non-blocking**:

```python
try:
    insights = generate_insights(results, query, sql)
    response["insights"] = insights
except Exception as e:
    print(f"Error generating insights: {str(e)}")
    # Don't fail the whole request if insights fail
    response["insights"] = None
```

**Behavior**:
- If insights generation fails, the card shows without insights
- SQL results and execution still succeed
- Error logged for debugging
- User experience not degraded

## Performance Considerations

### Token Usage
- **Insights Agent**: ~500-1000 tokens per request
  - Input: Query context + sample data (5 rows)
  - Output: 3-5 insights (~150-300 tokens)
- **Total Pipeline**: Intent + SQL + Insights
  - Typical: 2000-3000 tokens per query
  - With insights: +500-1000 tokens (~25-35% increase)

### Response Time
- **Insights Generation**: ~1-2 seconds
- **Total Pipeline**: 
  - Without insights: 3-5 seconds
  - With insights: 4-7 seconds
  - Increase: ~1-2 seconds (~25-40%)

### Cost Impact
- **Per Query Cost Increase**: ~25-35%
- **Example** (GPT-4o):
  - Without insights: $0.015 per query
  - With insights: $0.020 per query
  - Additional cost: $0.005 per query

## Testing Recommendations

### Test Cases

#### 1. Count/Aggregate Queries
```
Query: "How many customers do we have?"
Expected: Stats on total, distribution insights
```

#### 2. Top N Queries
```
Query: "Show top 5 products by sales"
Expected: Concentration analysis, trends, recommendations
```

#### 3. Filtered Queries
```
Query: "Show customers in California with revenue > $100K"
Expected: Segment characteristics, patterns, opportunities
```

#### 4. Time-based Queries
```
Query: "Sales by month for 2024"
Expected: Trends, seasonality, comparisons
```

#### 5. Join Queries
```
Query: "Customers with their total orders"
Expected: Relationship insights, correlation patterns
```

### Validation Checklist

- [ ] Insights appear in Adaptive Card
- [ ] 3-5 insights provided (not too few or too many)
- [ ] Emoji indicators appropriate for content
- [ ] Language is business-focused, not technical
- [ ] Insights are actionable or informative
- [ ] No redundancy with visible data
- [ ] Handles edge cases (0 rows, 1 row, etc.)
- [ ] Error handling works (no crashes if insights fail)
- [ ] Performance acceptable (<2s for insights)
- [ ] Token usage reasonable (<1000 tokens)

## Conversation Context

The insights agent uses a **dedicated thread** for each insight generation:

```python
# Create new thread for insights (not shared with intent/SQL threads)
thread = project_client.agents.threads.create()
```

**Why separate thread?**
- Insights don't need conversation history
- Each insight is independent analysis
- Prevents context pollution
- Cleaner agent specialization

**Intent/SQL threads** maintain conversation for follow-ups:
- "Show top customers" → "Tell me about row 3" ✓
- Thread shared between intent and SQL agents

## Configuration

### Enable/Disable Insights
Currently, insights are always generated if SQL execution succeeds. To make it optional:

```python
# In teams_nl2sql_agent.py or config file
INSIGHTS_ENABLED = True  # Set to False to disable

# In nl2sql_main.py process_nl_query()
if execute and INSIGHTS_ENABLED:
    if response["results"].get("success"):
        insights = generate_insights(...)
```

### Customize Insights Agent
Modify agent instructions in `_get_or_create_insights_agent()`:
- Adjust number of insights (3-5 default)
- Change emoji set
- Focus on specific business domains
- Add industry-specific terminology

## Future Enhancements

### Potential Improvements
1. **Context-Aware Insights**: Use conversation history for deeper analysis
2. **Comparative Insights**: Compare current results to historical queries
3. **Predictive Insights**: ML-based trend predictions
4. **Drill-Down Suggestions**: Recommend follow-up queries
5. **Visual Insights**: Generate chart recommendations
6. **Custom Insights Rules**: User-defined insight patterns
7. **Insights Caching**: Cache insights for identical queries
8. **Insights Feedback**: Allow users to rate insight quality

### Integration Opportunities
- **Power BI**: Export insights as annotations
- **Excel**: Include insights in data exports
- **Slack/Email**: Share insights in notifications
- **Dashboards**: Display insights alongside KPIs

## Troubleshooting

### Issue: No insights appearing
**Check**:
1. SQL execution succeeded?
2. Results contain data (rows > 0)?
3. Pipeline passing `insights` to card builder?
4. Adaptive Cards enabled?

### Issue: Generic/unhelpful insights
**Solution**:
- Enhance agent instructions with domain context
- Provide more sample data (increase from 5 rows)
- Add business rules to instructions

### Issue: Insights generation slow
**Solution**:
- Reduce sample data size
- Use smaller model for insights agent
- Cache insights for repeated queries
- Make insights optional/async

### Issue: High token usage
**Solution**:
- Limit sample data to 3 rows instead of 5
- Compress data format in prompt
- Use shorter column names
- Remove redundant context

## Related Documentation

- [CONVERSATION_MANAGEMENT.md](./CONVERSATION_MANAGEMENT.md) - Thread-based conversations
- [CHANGELOG.md](./CHANGELOG.md) - Version history
- [README.md](./README.md) - General setup and usage
- [DEPLOYMENT_GUIDE.md](../azure_deployment/DEPLOYMENT_GUIDE.md) - Azure deployment

## Version History

- **v0.0.21** (Current): Added data insights agent with emoji indicators
- **v0.0.20**: Conversation indicators in Adaptive Cards
- **v0.0.19**: Thread-based conversation management
- **v0.0.18**: Adaptive Cards implementation

---

**Last Updated**: 2024-01-XX  
**Author**: NL2SQL Development Team  
**Status**: ✅ Implemented and Ready for Testing
