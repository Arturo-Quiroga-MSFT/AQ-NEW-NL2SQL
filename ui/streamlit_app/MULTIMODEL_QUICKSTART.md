# Multi-Model NL2SQL Quick Start Guide

## 🎯 What is Multi-Model Optimization?

The Multi-Model NL2SQL app uses **different specialized AI models** for each stage of the pipeline, optimizing both **cost** and **performance**:

```
User Question
     ↓
🎯 Intent Extraction (gpt-4o-mini - fast & cheap)
     ↓
🧠 SQL Generation (gpt-4.1 or gpt-5-mini - accurate)
     ↓
⚡ SQL Execution (Azure SQL Database)
     ↓
📝 Result Formatting (gpt-4.1-mini - balanced)
     ↓
Natural Language Summary + Data
```

## 💰 Cost Savings

**Up to 80% cost reduction** compared to using a single premium model (like gpt-4.1) for all stages!

### Example Cost Breakdown

**Traditional Single-Model Approach (gpt-4.1 only):**
- Total tokens: 6,000 (3K input, 3K output)
- Cost: ~$0.017 per query
- Monthly (1K queries): ~$510

**Multi-Model Optimized Approach:**
- Intent (1K tokens @ gpt-4o-mini): ~$0.0006
- SQL (3K tokens @ gpt-4.1): ~$0.005
- Formatting (2K tokens @ gpt-4.1-mini): ~$0.0008
- **Total: ~$0.0064 per query** (62% cheaper!)
- **Monthly (1K queries): ~$192** (saves $318/month)

## 🚀 Running the Multi-Model App

### 1. Prerequisites

Ensure your `.env` file has:
```bash
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=https://your-endpoint.openai.azure.com/
AZURE_OPENAI_API_VERSION=2025-04-01-preview

AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DB=CONTOSO-FI
AZURE_SQL_USER=your_username
AZURE_SQL_PASSWORD=your_password
```

### 2. Start the App

```bash
# From repo root
streamlit run ui/streamlit_app/app_multimodel.py --server.port 8503

# Or from ui/streamlit_app directory
streamlit run app_multimodel.py
```

### 3. Using the App

1. **Select SQL Model**: In the sidebar, choose between:
   - `gpt-4.1`: Most accurate, best for complex queries
   - `gpt-5-mini`: Faster reasoning, lower cost

2. **Enter Your Question**: Type or use example buttons

3. **Run**: The app will:
   - 🎯 Extract intent using **gpt-4o-mini** (super fast, cheap)
   - 🧠 Generate SQL using your selected model
   - ⚡ Execute query against Azure SQL
   - 📝 Format results using **gpt-4.1-mini** (creates readable summary)

4. **View Cost Breakdown**: Expand the "Token usage & estimated cost by model" section to see:
   - Separate token counts for each stage
   - Individual costs for each model
   - Total cost comparison

## 🎨 Key Features

### ✨ Per-Stage Model Selection
- **Intent Extraction** always uses `gpt-4o-mini` (optimized for parsing)
- **SQL Generation** lets you choose `gpt-4.1` or `gpt-5-mini`
- **Result Formatting** always uses `gpt-4.1-mini` (balanced quality)

### 📊 Detailed Cost Tracking
- See token usage broken down by pipeline stage
- Compare costs across models
- Track cumulative costs over multiple queries

### 🤖 AI-Powered Result Summaries
- Natural language explanation of query results
- Key insights and patterns highlighted
- Professional, concise summaries

### 📁 Enhanced Run Logs
Saved to `RESULTS/nl2sql_multimodel_run_YYYYMMDD_HHMMSS.txt` with:
- Which model was used for each stage
- Token usage and costs per model
- AI-generated summary
- Complete query results

## 🧪 Comparing with Other Apps

Run all three apps simultaneously to compare:

```bash
# Terminal 1: Standard LangChain (port 8501)
streamlit run ui/streamlit_app/app.py

# Terminal 2: Azure AI Agent Service (port 8502)
streamlit run ui/streamlit_app/app_azureai.py --server.port 8502

# Terminal 3: Multi-Model Optimized (port 8503)
streamlit run ui/streamlit_app/app_multimodel.py --server.port 8503
```

Then access:
- http://localhost:8501 - Standard LangChain
- http://localhost:8502 - Azure AI Agents
- http://localhost:8503 - Multi-Model Optimized

## 🎯 When to Use Multi-Model vs Single-Model

### Use Multi-Model (`app_multimodel.py`) When:
- ✅ You have high query volume (100+ queries/day)
- ✅ Cost optimization is important
- ✅ You want natural language result summaries
- ✅ You need detailed cost breakdowns
- ✅ You want flexibility to experiment with models

### Use Single-Model (`app.py`) When:
- ✅ You're prototyping and testing
- ✅ You want simplicity (one model config)
- ✅ Query volume is low
- ✅ You're already using a specific model for everything

### Use Azure AI Agents (`app_azureai.py`) When:
- ✅ You need production-grade reliability
- ✅ You want managed identity authentication
- ✅ You need persistent agents
- ✅ You're deploying on Azure infrastructure

## 📈 Model Selection Guide

### For Intent Extraction
**Fixed: gpt-4o-mini**
- Why: Intent extraction is simple parsing that doesn't require complex reasoning
- Cost: ~$0.0003 per query (input+output combined)

### For SQL Generation
**Choose gpt-4.1 when:**
- Complex multi-table joins required
- Advanced aggregations and CTEs needed
- Schema has many relationships
- Accuracy is critical
- Cost: ~$0.005-0.01 per query

**Choose gpt-5-mini when:**
- Simpler queries (1-2 tables)
- Speed is more important than perfection
- Very high query volume
- Budget constraints
- Cost: ~$0.001-0.002 per query

### For Result Formatting
**Fixed: gpt-4.1-mini**
- Why: Balanced model provides good summaries without premium cost
- Cost: ~$0.001-0.002 per query

## 🔍 Monitoring Costs

The app tracks and displays:
- **Per-model token usage**: Input and output tokens separately
- **Per-stage costs**: What each pipeline step costs
- **Total run cost**: Sum of all model costs
- **Cost savings**: Implied comparison to single-model approach

### Example Output:
```
🎯 Intent Extraction (gpt-4o-mini)
   Input tokens: 256
   Output tokens: 128
   Cost: $0.000384

🧠 SQL Generation (gpt-4.1)
   Input tokens: 2,048
   Output tokens: 512
   Cost: $0.011344

📝 Result Formatting (gpt-4.1-mini)
   Input tokens: 1,024
   Output tokens: 256
   Cost: $0.001126

Total: 4,224 tokens, $0.012854 USD
```

## 💡 Tips for Maximum Savings

1. **Use gpt-5-mini for SQL when possible**: Test if your queries work well with it
2. **Leverage prompt caching**: Repeated schema context gets 50% discount
3. **Batch similar queries**: Schema caching is more effective
4. **Monitor the logs**: Review which stages use the most tokens
5. **Adjust max_tokens**: Lower limits for simpler queries

## 🛠️ Troubleshooting

### "Import schema_reader could not be resolved"
- This is just a linting error, the app will run fine
- The imports are resolved at runtime via sys.path manipulation

### High costs for SQL generation
- Consider switching to gpt-5-mini
- Check if schema context is too large
- Simplify prompts if possible

### Poor quality summaries
- The gpt-4.1-mini model is balanced and should work well
- If needed, you can modify `FORMATTING_MODEL` to use gpt-4.1

## 📚 Additional Resources

- **Pricing Guide**: `/PRICING_UPDATE_GUIDE.md`
- **Model Pricing**: `/azure_openai_pricing_updated_oct2025.json`
- **Schema Documentation**: `/docs/CONTOSO-FI_SCHEMA_SUMMARY.md`
- **Example Questions**: `/docs/CONTOSO-FI_EXAMPLE_QUESTIONS.txt`
- **UI Comparison**: `/ui/streamlit_app/README.md`

## 🤝 Contributing

To add more models or modify the multi-model strategy:
1. Update the model constants at the top of `app_multimodel.py`
2. Ensure pricing is in `azure_openai_pricing_updated_oct2025.json`
3. Test thoroughly with various query types
4. Update this guide with your changes

---

**Questions?** Check the main README or create an issue in the repository.

**Cost concerns?** The multi-model approach typically saves 60-80% compared to using premium models for everything!
