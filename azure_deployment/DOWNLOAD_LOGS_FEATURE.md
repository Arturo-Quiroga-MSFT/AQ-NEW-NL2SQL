# Download Log Files Feature - V2 Update

## Overview

Added download buttons to the NL2SQL Multi-Model V2 app to allow users to download run logs directly from the UI.

## Changes Made

### Location
`/ui/streamlit_app/app_multimodel_v2.py`

### New Features

After each query run, users will see a **"📥 Download Run Logs"** section with three download buttons:

#### 1. **📄 Download .txt** 
- Complete run log in plain text format
- Includes all details: query, intent, reasoning, SQL, results, token usage
- Best for: Reading in text editors, archiving, searching

#### 2. **📝 Download .md**
- Run log in Markdown format with enhanced formatting
- Includes timing breakdown tables, formatted SQL, result tables
- Best for: Viewing in Markdown viewers, GitHub, documentation

#### 3. **📊 Download .json**
- Structured summary in JSON format
- Includes: timestamp, models used, token usage, cost, result count
- Best for: Programmatic analysis, data processing, dashboards

## Benefits

### Before (Container-only storage):
- ❌ Logs saved inside container (ephemeral)
- ❌ Lost when container restarts
- ❌ Difficult to access
- ❌ Required Azure Blob Storage setup

### After (Download buttons):
- ✅ Download logs directly from UI
- ✅ Available immediately after each run
- ✅ No Azure Blob Storage required
- ✅ Three formats (text, markdown, JSON)
- ✅ Works offline/locally

## User Experience

### Before:
1. Run query
2. See message: "✅ Run log saved: `nl2sql_multimodel_v2_run_20251009_143147.txt`"
3. **Cannot access the file** (inside container)

### After:
1. Run query
2. See message with download buttons
3. **Click button to download** any format
4. Files available on local computer immediately

## Download Section Layout

```
### 📥 Download Run Logs
[📄 Download .txt] [📝 Download .md] [📊 Download .json]
💾 Logs saved locally: `nl2sql_multimodel_v2_run_20251009_143147.txt` 
    and `nl2sql_multimodel_v2_run_20251009_143147.md`
```

## JSON Summary Structure

```json
{
  "timestamp": "2025-10-09T14:31:47.815810",
  "implementation": "Multi-Model Optimized V2",
  "models": {
    "intent": "gpt-4o-mini",
    "sql": "gpt-5-mini",
    "formatting": "gpt-4.1-mini"
  },
  "query": "List 20 companies with their industry and credit rating.",
  "elapsed_time_seconds": 25.51,
  "token_usage": {
    "intent": {"prompt": 1306, "completion": 64, "total": 1370},
    "sql": {"prompt": 2709, "completion": 1174, "total": 3883},
    "formatting": {"prompt": 724, "completion": 269, "total": 993},
    "total": 6246
  },
  "cost": {
    "total_usd": 0.003446,
    "currency": "USD"
  },
  "result_count": 15
}
```

## Use Cases

### For Data Scientists/Analysts:
- Download JSON for batch analysis of query performance
- Track token usage and costs over time
- Compare different models' effectiveness

### For Developers:
- Download text logs for debugging
- Share markdown logs in documentation
- Archive query history

### For Managers:
- Monitor AI costs via JSON summaries
- Review query patterns
- Audit system usage

## Deployment

### Build and Deploy V5:

```bash
# 1. Build new image with download feature
az acr build --registry acrnl2sqlddo6f5dplg5v4 \
  --image nl2sql-multimodel:V5 \
  -f azure_deployment/Dockerfile.multimodel_v2 .

# 2. Deploy to Container Apps
az containerapp update \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --image acrnl2sqlddo6f5dplg5v4.azurecr.io/nl2sql-multimodel:V5
```

## Backwards Compatibility

- ✅ Azure Blob Storage upload still works (if configured)
- ✅ Local file saving still works
- ✅ No breaking changes
- ✅ Download buttons are additive feature

## Testing

After deployment, test by:
1. Running a query
2. Verifying three download buttons appear
3. Clicking each button to download files
4. Opening downloaded files to verify content

Expected filenames:
- `nl2sql_multimodel_v2_run_20251009_143147.txt`
- `nl2sql_multimodel_v2_run_20251009_143147.md`
- `nl2sql_multimodel_v2_run_20251009_143147.json`

## Alternative: Azure Blob Storage

If you prefer centralized storage, you can still enable Azure Blob Storage by setting environment variables:

```bash
az containerapp update \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --set-env-vars \
    "AZURE_STORAGE_CONNECTION_STRING=<connection-string>" \
    "AZURE_STORAGE_CONTAINER_NAME=nl2sql-logs"
```

This works **in addition to** the download buttons (not instead of).

## Technical Details

### File Locations (Inside Container):
- `/app/RESULTS/nl2sql_multimodel_v2_run_*.txt`
- `/app/RESULTS/nl2sql_multimodel_v2_run_*.md`

### Download Mechanism:
- Uses Streamlit's `st.download_button()`
- Reads files from disk into memory
- Serves via browser download
- No additional backend required

### Performance:
- Minimal impact (file reading is fast)
- Files are small (~10-50 KB typically)
- Download buttons only shown after successful run

---

**Version**: V5 (Download Feature)  
**Date**: October 9, 2025  
**Status**: Ready for deployment
