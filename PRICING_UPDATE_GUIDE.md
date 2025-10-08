# Azure OpenAI Pricing Update Guide - October 2025

## Overview
Your current pricing files are 2 months old (from August 2025). This guide helps you update them with the latest October 2025 pricing.

## Current Pricing Files Location
1. `/nl2sql_standalone_Langchain/azure_openai_pricing.json`
2. `/nl2sql_standalone_AzureAI/azure_openai_pricing.json`

## New Updated File Created
- `/azure_openai_pricing_updated_oct2025.json` (comprehensive, includes all current models)

## Key Pricing Changes (USD, Global Deployment, per 1K tokens)

### Models You're Using:

| Model | Old Input | New Input | Old Output | New Output | Change |
|-------|-----------|-----------|------------|------------|--------|
| **gpt-5** | $0.00125 | $0.00125 | $0.01 | $0.01 | ✅ No change |
| **gpt-4.1** | $0.00277 | $0.00277 | $0.01107 | $0.01107 | ✅ No change |

### New Features Added:
- ✨ **Cached Input Pricing** - New discount for repeated prompts:
  - `gpt-5`: $0.000625/1K (50% off input)
  - `gpt-4.1`: $0.001385/1K (50% off input)
  - `gpt-4o`: $0.00125/1K (50% off input)

### New Models Available (October 2025):

| Model | Input/1K | Output/1K | Cached Input/1K | Use Case |
|-------|----------|-----------|-----------------|----------|
| **GPT-5 series** | | | | Latest reasoning models |
| gpt-5 | $0.00125 | $0.01 | $0.000625 | Full reasoning |
| gpt-5-mini | $0.0003 | $0.0012 | $0.00015 | Fast reasoning |
| gpt-5-nano | $0.00015 | $0.0006 | $0.000075 | Ultra-fast |
| | | | | |
| **GPT-4.1 series** | | | | Latest general purpose |
| gpt-4.1 | $0.00277 | $0.01107 | $0.001385 | Full capability, 1M context |
| gpt-4.1-mini | $0.00055 | $0.0022 | $0.000275 | Balanced |
| gpt-4.1-nano | $0.00011 | $0.00044 | $0.000055 | Fastest, cheapest |
| | | | | |
| **o-series** | | | | Advanced reasoning |
| o3 | $0.015 | $0.06 | $0.0075 | Complex reasoning |
| o3-mini | $0.0011 | $0.0044 | $0.00055 | Efficient reasoning |
| o4-mini | $0.0011 | $0.0044 | $0.00055 | Latest efficient reasoning |
| | | | | |
| **GPT-4o series** | | | | Multimodal |
| gpt-4o | $0.0025 | $0.01 | $0.00125 | Text + vision |
| gpt-4o-mini | $0.00015 | $0.0006 | $0.000075 | Fast multimodal |

## How to Update Your Pricing Files

### Option 1: Replace Both Files (Recommended)
```bash
# Backup existing files
cp nl2sql_standalone_Langchain/azure_openai_pricing.json nl2sql_standalone_Langchain/azure_openai_pricing.json.backup
cp nl2sql_standalone_AzureAI/azure_openai_pricing.json nl2sql_standalone_AzureAI/azure_openai_pricing.json.backup

# Copy new pricing to both locations
cp azure_openai_pricing_updated_oct2025.json nl2sql_standalone_Langchain/azure_openai_pricing.json
cp azure_openai_pricing_updated_oct2025.json nl2sql_standalone_AzureAI/azure_openai_pricing.json
```

### Option 2: Update Only Your Models
If you only want to update models you're using (gpt-5, gpt-4.1), keep your current files but be aware of:
1. ✅ Your current prices are still accurate
2. ⚠️ You're missing cached input pricing (50% discount on repeated content)
3. ⚠️ You don't have pricing for newer models (o3, o4-mini, etc.)

## Cost Estimation Examples

### For Your Current Usage:

**Example: gpt-5 with 10K input tokens, 2K output tokens**
- Input cost: 10 × $0.00125 = $0.0125
- Output cost: 2 × $0.01 = $0.02
- **Total: $0.0325**

**Example: gpt-4.1 with 50K input tokens, 10K output tokens**
- Input cost: 50 × $0.00277 = $0.1385
- Output cost: 10 × $0.01107 = $0.1107
- **Total: $0.2492**

### With Prompt Caching (New Feature):

**Example: Same gpt-5 query with 8K cached, 2K new input, 2K output**
- Cached input: 8 × $0.000625 = $0.005
- New input: 2 × $0.00125 = $0.0025
- Output: 2 × $0.01 = $0.02
- **Total: $0.0275** (saves $0.005 or 15%)

## When to Use Cached Input
Cached input pricing applies when:
- Your prompts have large, repeated context (schema, instructions, examples)
- You make multiple queries with the same prefix
- Cache TTL: typically 5-10 minutes, max 1 hour

Perfect for your NL2SQL use case where:
- ✅ Database schema remains constant across queries
- ✅ System instructions are identical
- ✅ Multiple user questions use same context

## Model Recommendations for Your Use Case

Based on your NL2SQL application:

### Current Setup (Good):
- **gpt-5**: Excellent for complex queries, multi-table joins, reasoning
- **gpt-4.1**: Great balance of speed and capability

### Consider Trying:
1. **gpt-4.1-mini** ($0.00055 input): 80% cheaper than gpt-4.1, good for simpler queries
2. **gpt-5-mini** ($0.0003 input): Faster reasoning at lower cost
3. **gpt-4o-mini** ($0.00015 input): Cheapest option, great for intent extraction

### Suggested Strategy:
```
User Query → Intent Extraction (gpt-4o-mini - fast & cheap)
          → SQL Generation (gpt-4.1 or gpt-5 - accurate)
          → Result Formatting (gpt-4.1-mini - balanced)
```

## Pricing Sources & References

- **Official Pricing**: https://azure.microsoft.com/pricing/details/cognitive-services/openai-service/
- **Documentation**: https://learn.microsoft.com/azure/ai-services/openai/
- **Prompt Caching**: https://learn.microsoft.com/azure/ai-services/openai/how-to/prompt-caching
- **Calculator**: https://azure.microsoft.com/pricing/calculator/

## Update Checklist

- [ ] Backup existing pricing files
- [ ] Copy new pricing file to both implementations
- [ ] Test cost calculations in UI
- [ ] Verify pricing in run logs
- [ ] Consider enabling prompt caching for your schema
- [ ] Evaluate using cheaper models for simpler tasks

## Notes

1. Prices shown are for **Global Standard** deployment (most common)
2. **Data Zone** and **Regional** deployments have different pricing
3. **Provisioned Throughput (PTU)** has different pricing model
4. **Batch API** offers 50% discount on Global Standard pricing
5. All prices are subject to change - check official Azure pricing page

## Questions?

- Check your Azure portal for actual billing
- Use Azure Cost Management for detailed breakdowns
- Monitor token usage in your Streamlit UI's "Token usage & estimated cost" panel
- Review your RESULTS/*.txt logs for per-query costs

---

**Last Updated**: October 8, 2025
**Currency**: USD (CAD also included in JSON file)
**Deployment Type**: Global Standard (pay-as-you-go)
