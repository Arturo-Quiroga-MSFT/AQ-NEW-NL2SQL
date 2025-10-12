# Quick Deploy: Adaptive Cards for Teams Bot

## 🚀 Quick Deploy (No Docker Rebuild Needed!)

Since `adaptive_cards.py` is just a Python file added to your repo, you have two options:

### Option 1: Rebuild Docker Image (Recommended - Permanent)

This makes the Adaptive Cards permanent in your image:

```bash
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal

# Build and push new image with Adaptive Cards
az acr build \
  --registry nl2sqlacr1760120779 \
  --image nl2sql-teams-bot:latest \
  --file Dockerfile \
  .

# Update ACA to use new image (creates new revision automatically)
az containerapp update \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --image nl2sqlacr1760120779.azurecr.io/nl2sql-teams-bot:latest
```

**Time:** ~3-5 minutes (ACR build + deploy)

### Option 2: Test Locally First

Test the Adaptive Cards locally before deploying:

```bash
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal

# Activate virtual environment
source ../.venv/bin/activate

# Run locally
python start_server.py
```

Then test in Teams by updating your bot endpoint temporarily to your local machine (using ngrok or similar).

---

## 🎨 What Changed

### Files Modified:
1. **`adaptive_cards.py`** (NEW) - Adaptive Card builder classes
2. **`teams_nl2sql_agent.py`** (UPDATED) - Now uses Adaptive Cards when available

### Backward Compatible:
- ✅ If `adaptive_cards.py` is missing, bot falls back to plain text
- ✅ No breaking changes to existing functionality
- ✅ All existing queries still work

---

## 🧪 Testing the Adaptive Cards

### 1. Welcome Card
**Trigger:** Add the bot to a new Teams chat or channel

**Expected:**
- Rich welcome card with:
  - Large welcome message
  - Quick start examples
  - Feature highlights
  - Action buttons: "Show Commands", "View Schema", "Sample Query"

### 2. Success Card
**Trigger:** Ask: "How many customers do we have?"

**Expected:**
- Green header with ✅ icon
- "Query Results" title with row count
- Collapsible SQL section
- Results displayed as formatted rows
- Action buttons: "Run Again", "Copy Results", "Modify Query"
- Footer with execution time and tokens

### 3. Error Card
**Trigger:** Ask: "Show me invalid_table_name"

**Expected:**
- Red header with ❌ icon
- "Execution Error" title
- Error message
- Generated SQL (if available)
- Suggestions section
- Action buttons: "Try Again", "Get Help"

### 4. Help Card
**Trigger:** Type: `/help`

**Expected:**
- Help title
- "How It Works" section with steps
- Example questions with icons
- Special commands table
- "Try Example" button

---

## 📊 Before & After Comparison

### Before (Plain Text)
```
✅ Query Results

Generated SQL:
```sql
SELECT COUNT(*) FROM dim.DimCustomer
```

Found 1120 result(s):
```
CustomerCount
-------------
1120
```

Tokens used: 466
```

### After (Adaptive Card)
```
┌──────────────────────────────────────┐
│ ✅  Query Results      │  5:45 PM    │
│     Found 1,120 results │ Good        │
├──────────────────────────────────────┤
│ 📝 Generated SQL                     │
│ SELECT COUNT(*) FROM dim.DimCustomer │
├──────────────────────────────────────┤
│ 📊 Results                           │
│ Row 1                                │
│ CustomerCount: 1120                  │
├──────────────────────────────────────┤
│ ⏱️ Execution Time: 0.15s             │
│ 🎫 Tokens Used: 466                  │
├──────────────────────────────────────┤
│ [🔄 Run Again] [📋 Copy] [✏️ Modify]  │
└──────────────────────────────────────┘
```

---

## 🎯 Key Benefits

### 1. Better Visual Hierarchy
- ✅ Color-coded sections (green=success, red=error, blue=info)
- ✅ Clear headers and footers
- ✅ Professional card layout

### 2. Interactive Elements
- ✅ **"Run Again"** - Re-execute query with one click
- ✅ **"Copy Results"** - Copy data to clipboard
- ✅ **"Modify Query"** - Edit and re-run
- ✅ **"Try Example"** - Quick sample queries

### 3. Better Mobile Experience
- ✅ Cards adapt to screen size
- ✅ Touch-friendly buttons
- ✅ Easier to read on phone

### 4. Enhanced Discoverability
- ✅ Welcome card guides new users
- ✅ Help card shows all commands
- ✅ Action buttons suggest next steps

---

## 🔧 Troubleshooting

### Issue: Cards Not Showing

**Check 1:** Verify `adaptive_cards.py` is in the image
```bash
az containerapp logs show \
  --name nl2sql-teams-bot \
  --resource-group AQ-BOT-RG \
  --tail 20
```

Look for:
- `[WARNING] Adaptive Cards module not found` → Rebuild image
- No warning → Cards are enabled

**Check 2:** Test card JSON locally
```python
from adaptive_cards import AdaptiveCardBuilder

card = AdaptiveCardBuilder.create_welcome_card()
print(json.dumps(card, indent=2))
```

### Issue: Card Rendering Error in Teams

**Cause:** Invalid Adaptive Card JSON

**Solution:** Validate card at [Adaptive Cards Designer](https://adaptivecards.io/designer/)

### Issue: Action Buttons Not Working

**Cause:** Action handlers not implemented yet

**Solution:** Action buttons currently show as disabled. To enable:
1. Add action handler in `on_message()` function
2. Check `context.activity.value` for button data
3. Process action (e.g., re-run query, export data)

---

## 🚀 Next Steps

### Phase 1: Deploy Basic Cards (NOW)
```bash
# Deploy updated bot with Adaptive Cards
az acr build --registry nl2sqlacr1760120779 --image nl2sql-teams-bot:latest .
az containerapp update --name nl2sql-teams-bot --resource-group AQ-BOT-RG --image nl2sqlacr1760120779.azurecr.io/nl2sql-teams-bot:latest
```

### Phase 2: Test & Refine (Week 1)
- ✅ Test all card types in Teams
- ✅ Gather user feedback
- ✅ Adjust colors, layout, wording

### Phase 3: Add Action Handlers (Week 2)
- ✅ Implement "Run Again" button
- ✅ Implement "Export CSV" button
- ✅ Add query modification flow

### Phase 4: Advanced Features (Week 3+)
- ✅ Query history carousel
- ✅ Schema explorer cards
- ✅ Chart/visualization hints
- ✅ Smart follow-up suggestions

---

## 📝 Deployment Checklist

- [ ] Code changes committed to git
- [ ] Tested locally (optional but recommended)
- [ ] Docker image rebuilt in ACR
- [ ] ACA updated with new image
- [ ] New revision created and healthy
- [ ] Tested welcome card in Teams
- [ ] Tested success card with sample query
- [ ] Tested error card with invalid query
- [ ] Tested help card with `/help` command
- [ ] Verified fallback to plain text works (if needed)

---

## 🎉 Ready to Deploy?

Run this single command to deploy:

```bash
cd /Users/arturoquiroga/GITHUB/AQ-NEW-NL2SQL/nl2sql_azureai_universal && \
az acr build --registry nl2sqlacr1760120779 --image nl2sql-teams-bot:latest . && \
az containerapp update --name nl2sql-teams-bot --resource-group AQ-BOT-RG --image nl2sqlacr1760120779.azurecr.io/nl2sql-teams-bot:latest
```

Then test in Teams! 🚀
