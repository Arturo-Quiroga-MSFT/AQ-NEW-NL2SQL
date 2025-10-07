# NL2SQL Demo Guide

## 📓 Demo Notebook Overview

**File:** `NL2SQL_Demo_Walkthrough.ipynb`

This interactive Jupyter notebook provides a step-by-step demonstration of the NL2SQL pipeline capabilities, perfect for presenting to partners, stakeholders, or team members.

## 🎯 What's Included

### 15 Interactive Cells Covering:

1. **Introduction** - Overview of the pipeline and technologies
2. **Dependencies** - Import all required libraries
3. **Azure OpenAI Setup** - Configure connection and detect model type
4. **LLM Initialization** - Create the language model instance
5. **Token Tracking** - Set up usage and cost monitoring
6. **Pricing Configuration** - Load pricing data
7. **Sample Queries** - Pre-defined example questions
8. **Intent Extraction** - AI-powered intent understanding
9. **Demo: Intent** - Live demonstration of intent extraction
10. **Schema Reader** - Database schema understanding
11. **SQL Generation** - AI-powered query generation
12. **SQL Sanitization** - Clean and validate SQL
13. **Full Pipeline Demo** - Complete end-to-end workflow
14. **Interactive Testing** - Try your own queries
15. **Database Execution** - Optional real execution (with safety warnings)

## 🚀 Quick Start

### Prerequisites
```bash
# Make sure you're in the standalone directory
cd nl2sql_standalone

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux
# or
.venv\Scripts\activate  # Windows

# Install Jupyter if not already installed
pip install jupyter notebook
```

### Launch the Notebook
```bash
jupyter notebook NL2SQL_Demo_Walkthrough.ipynb
```

Or use VS Code:
1. Open `NL2SQL_Demo_Walkthrough.ipynb` in VS Code
2. Select Python kernel (your .venv)
3. Run cells sequentially with Shift+Enter

## 📋 Demo Flow

### Recommended Presentation Order:

1. **Start with Overview** (Cell 1)
   - Explain the problem: business users need data but don't know SQL
   - Show the 5-step pipeline architecture

2. **Show Configuration** (Cells 2-6)
   - Highlight Azure OpenAI integration
   - Mention model flexibility (GPT-4, GPT-5, o-series)
   - Explain token tracking for cost control

3. **Demonstrate Intent Extraction** (Cells 7-9)
   - Use sample query: "How many customers do I have?"
   - Show how AI understands intent and entities
   - Highlight JSON structure for programmatic use

4. **Show SQL Generation** (Cells 10-12)
   - Display schema awareness
   - Show generated T-SQL query
   - Explain sanitization process

5. **Run Full Pipeline** (Cell 13)
   - Execute complete workflow
   - Show timing and token usage
   - Highlight cost tracking

6. **Interactive Demo** (Cell 14)
   - Let audience suggest queries
   - Show real-time processing
   - Demonstrate flexibility

7. **Wrap Up** (Cell 16)
   - Summarize key benefits
   - Discuss integration possibilities
   - Q&A

## 💡 Demo Tips

### For Technical Audiences:
- Focus on architecture and model selection
- Discuss prompt engineering techniques
- Show token optimization strategies
- Explain error handling and validation

### For Business Audiences:
- Emphasize ease of use (natural language)
- Highlight time savings
- Show cost transparency
- Demonstrate accuracy with real examples

### For Executive Audiences:
- Quick overview (5 minutes)
- Focus on ROI and business value
- Show one impressive end-to-end example
- Discuss scalability and integration

## 🎨 Customization Tips

### Add Your Own Examples:
```python
# In Cell 6, add domain-specific queries:
SAMPLE_QUERIES = [
    "Your industry-specific question 1",
    "Your industry-specific question 2",
    # etc.
]
```

### Adjust for Your Schema:
- Update schema_reader.py to match your database
- Modify sample queries to reflect your data model
- Update documentation to reference your tables

### Branding:
- Add company logo in first markdown cell
- Customize colors and formatting
- Add additional visualizations

## 🔒 Safety Notes

### Demo vs Production:
- The notebook is designed for **demonstration only**
- Cell 15 includes execution against real database (disabled by default)
- Always review generated SQL before execution
- Use read-only database credentials for demos

### Best Practices:
1. Test all queries before live demo
2. Have backup examples ready
3. Monitor token usage during demo
4. Keep `.env` credentials secure
5. Clear output before sharing notebook

## 📊 Sample Output

When running the demo, you'll see:

```
═══════════════════════════════════════════════════════════
🚀 COMPLETE NL2SQL PIPELINE
═══════════════════════════════════════════════════════════

📝 NATURAL LANGUAGE QUERY
──────────────────────────────────────────────────────────
How many customers do I have?

🧠 STEP 1: EXTRACT INTENT & ENTITIES
──────────────────────────────────────────────────────────
{
  "intent": "aggregate_count",
  "entity": "customers",
  ...
}

⚡ STEP 3: GENERATE SQL QUERY
──────────────────────────────────────────────────────────
SELECT COUNT(*) AS customer_count
FROM dbo.Company

📈 PIPELINE SUMMARY
═══════════════════════════════════════════════════════════
⏱️ Total time: 3.45 seconds
📊 Total tokens: 1,234 (prompt: 890, completion: 344)
💰 Estimated cost: $0.003421 USD
═══════════════════════════════════════════════════════════
```

## 🆘 Troubleshooting

### "Module not found" errors:
```bash
pip install -r requirements.txt
```

### Jupyter kernel issues:
```bash
python -m ipykernel install --user --name=nl2sql
```

### Azure OpenAI connection errors:
- Check `.env` file exists and has valid credentials
- Verify network connectivity
- Check API quotas in Azure portal

### Schema reader errors:
- Ensure SQL credentials are correct
- Check database connectivity
- Verify ODBC driver is installed

## 📞 Support

For questions or issues:
1. Check README.md for setup instructions
2. Review .env.example for configuration template
3. Consult Azure OpenAI documentation
4. Contact: [Your Contact Information]

---

**Last Updated:** October 7, 2025
**Version:** 1.0
**Compatible with:** Python 3.11+, Jupyter Notebook, VS Code
