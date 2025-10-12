# Adaptive Cards - Visual Examples

## 📸 Card Examples with JSON

### 1. Success Card Example

**Scenario:** User asks "How many customers do we have?"

**Visual Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ ✅  Query Results              │  5:45 PM               │
│     Found 1,120 result(s)      │  ●                     │
└─────────────────────────────────────────────────────────┘
│                                                          │
│ 📝 Generated SQL                                         │
│ ┌────────────────────────────────────────────────────┐  │
│ │ SELECT COUNT(DISTINCT CustomerId) AS CustomerCount│  │
│ │ FROM dim.DimCustomer                               │  │
│ │ ORDER BY CustomerCount;                            │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ 📊 Results                                               │
│ ┌────────────────────────────────────────────────────┐  │
│ │ Row 1                                              │  │
│ │ CustomerCount:  1120                               │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ⏱️ Execution Time:  0.15s                                │
│ 🎫 Tokens Used:     3645                                 │
│                                                          │
│ ┌──────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │ 🔄 Run   │ │ 📋 Copy      │ │ ✏️ Modify    │         │
│ │   Again  │ │   Results    │ │   Query      │         │
│ └──────────┘ └──────────────┘ └──────────────┘         │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Green "good" style header
- ✅ Timestamp in top-right
- ✅ Row count badge
- ✅ Code block for SQL
- ✅ Formatted result row
- ✅ Metadata footer (time + tokens)
- ✅ Three action buttons

---

### 2. Error Card Example

**Scenario:** User asks "Show me from invalid_table"

**Visual Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ ❌  Execution Error            │                        │
│     Query failed to execute    │  ●                     │
└─────────────────────────────────────────────────────────┘
│                                                          │
│ Error Details:                                           │
│ ┌────────────────────────────────────────────────────┐  │
│ │ 8 for SQL Server][SQL Server]Invalid object name  │  │
│ │ 'dbo.invalid_table'. (208) (SQLExecDirectW)        │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ Generated SQL:                                           │
│ ┌────────────────────────────────────────────────────┐  │
│ │ SELECT * FROM dbo.invalid_table                    │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ 💡 Try This:                                             │
│ • Check table and column names                           │
│ • Try rephrasing your question                           │
│ • Use simpler filters or conditions                      │
│                                                          │
│ ┌──────────────┐ ┌──────────────┐                       │
│ │ 🔄 Try Again │ │ 💬 Get Help  │                       │
│ └──────────────┘ └──────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Red "attention" style header
- ✅ Clear error message
- ✅ SQL that failed
- ✅ Helpful suggestions
- ✅ Action buttons for recovery

---

### 3. Welcome Card Example

**Scenario:** Bot added to new chat

**Visual Layout:**
```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│           👋 Welcome to NL2SQL Bot!                      │
│                                                          │
│        Ask database questions in natural language        │
│                                                          │
└─────────────────────────────────────────────────────────┘
│                                                          │
│ 🚀 Quick Start Examples:                                 │
│ • How many customers do we have?                         │
│ • Show me loans with balance over $10,000                │
│ • What's the average loan amount by state?               │
│ • List top 10 customers by balance                       │
│                                                          │
│ ✨ Features:                                              │
│ 🧠  AI-powered SQL generation                            │
│ ⚡  Real-time query execution                            │
│ 📊  Formatted results in cards                           │
│ 🔄  Interactive follow-ups                               │
│                                                          │
│ ┌────────────┐ ┌──────────────┐ ┌──────────────┐        │
│ │ 📋 Show   │ │ 🗂️ View       │ │ 📝 Sample    │        │
│ │   Commands│ │   Schema     │ │   Query      │        │
│ └────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Centered hero message
- ✅ Example queries
- ✅ Feature highlights with icons
- ✅ Quick action buttons

---

### 4. Help Card Example

**Scenario:** User types `/help`

**Visual Layout:**
```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│ 📚 NL2SQL Bot Help                                       │
│                                                          │
└─────────────────────────────────────────────────────────┘
│                                                          │
│ How It Works:                                            │
│ 1. 🧠 Understand your natural language question          │
│ 2. 💡 Generate SQL query using Azure AI                  │
│ 3. ⚡ Execute query against the database                 │
│ 4. 📊 Format and display results beautifully             │
│                                                          │
│ Example Questions:                                       │
│                                                          │
│ 📊  Count: How many customers do we have?                │
│                                                          │
│ 🔍  Filter: Show loans in California                     │
│                                                          │
│ 📈  Aggregate: Average loan amount by state              │
│                                                          │
│ 🏆  Top N: Top 10 customers by balance                   │
│                                                          │
│ Special Commands:                                        │
│ /help   Show this help message                           │
│ /about  About this bot                                   │
│ /schema View database schema                             │
│                                                          │
│ ┌────────────────┐                                       │
│ │ Try Example    │                                       │
│ └────────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Step-by-step workflow
- ✅ Categorized examples with icons
- ✅ Command reference table
- ✅ Call-to-action button

---

### 5. Large Result Set Example

**Scenario:** User asks "List all customers"

**Visual Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ ✅  Query Results              │  5:47 PM               │
│     Found 1,120 result(s)      │  ●                     │
└─────────────────────────────────────────────────────────┘
│                                                          │
│ 📝 Generated SQL                                         │
│ ┌────────────────────────────────────────────────────┐  │
│ │ SELECT CustomerId, FirstName, LastName, Email      │  │
│ │ FROM dim.DimCustomer                               │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ 📊 Results                                               │
│ ┌────────────────────────────────────────────────────┐  │
│ │ Row 1                                              │  │
│ │ CustomerId:  1001                                  │  │
│ │ FirstName:   John                                  │  │
│ │ LastName:    Doe                                   │  │
│ │ Email:       john.doe@email.com                    │  │
│ ├────────────────────────────────────────────────────┤  │
│ │ Row 2                                              │  │
│ │ CustomerId:  1002                                  │  │
│ │ FirstName:   Jane                                  │  │
│ │ LastName:    Smith                                 │  │
│ │ Email:       jane.smith@email.com                  │  │
│ ├────────────────────────────────────────────────────┤  │
│ │ ... (8 more rows) ...                              │  │
│ └────────────────────────────────────────────────────┘  │
│                                                          │
│ ⚠️ Showing first 10 of 1,120 results.                    │
│    1,110 more rows available.                            │
│                                                          │
│ ⏱️ Execution Time:  1.23s                                │
│ 🎫 Tokens Used:     5240                                 │
│                                                          │
│ ┌──────────┐ ┌──────────────┐ ┌──────────────┐         │
│ │ 📥 Export│ │ 📋 Copy      │ │ 🔍 Show More │         │
│ │   All    │ │   Results    │ │              │         │
│ └──────────┘ └──────────────┘ └──────────────┘         │
└─────────────────────────────────────────────────────────┘
```

**Features:**
- ✅ Shows first 10 rows
- ✅ Each row as separate container with facts
- ✅ Warning message about additional rows
- ✅ "Export All" and "Show More" buttons

---

## 🎨 Color Coding Reference

### Container Styles

| Style | Color | Use Case |
|-------|-------|----------|
| `good` | Green | Success, positive results |
| `attention` | Red | Errors, failures, warnings |
| `emphasis` | Light gray | Important sections, headers |
| `accent` | Blue | Information, highlights |
| `default` | White | Normal content |

### Text Colors

| Color | Use Case |
|-------|----------|
| `good` | Success messages, positive metrics |
| `attention` | Error messages, warnings |
| `accent` | Highlights, important info |
| `default` | Normal text |
| `subtle` | Secondary information, timestamps |

### Font Weights

| Weight | Use Case |
|--------|----------|
| `bolder` | Headers, titles, labels |
| `default` | Normal content |
| `lighter` | Secondary text, hints |

---

## 📱 Responsive Design

### Desktop View (Wide Screen)
- Multi-column layouts for facts
- Side-by-side action buttons
- Full-width SQL code blocks

### Mobile View (Narrow Screen)
- Single column layout
- Stacked action buttons
- Word-wrapped text
- Collapsible sections

---

## 🎯 Design Patterns Used

### 1. Progressive Disclosure
- SQL query collapsed by default (can expand)
- Large result sets show first 10 rows
- "Show More" reveals additional data

### 2. Visual Hierarchy
```
Primary:   Query Results (large, bold)
Secondary: SQL query, metadata (medium)
Tertiary:  Timestamps, token usage (small, subtle)
```

### 3. Scannable Layout
- Icons for quick identification (✅, ❌, 📊)
- Color coding for status (green=good, red=error)
- Clear sections with spacing

### 4. Call-to-Action
- Action buttons at bottom
- Primary action (Run Again) leftmost
- Destructive actions (if any) rightmost

---

## 🔧 Customization Options

### Adjust Max Rows Displayed
In `adaptive_cards.py`, change:
```python
def _create_results_table(rows, total_count, max_rows=10):
    # Change max_rows to 20, 50, etc.
```

### Change Color Scheme
Modify container styles:
```python
header = {
    "type": "Container",
    "style": "good",  # Change to: emphasis, accent, attention
    ...
}
```

### Add Custom Actions
Add more buttons:
```python
actions.append({
    "type": "Action.Submit",
    "title": "📊 View Chart",
    "data": {"action": "chart", "sql": sql}
})
```

### Modify Text Sizes
```python
{
    "type": "TextBlock",
    "text": "Title",
    "size": "extraLarge"  # Options: small, medium, large, extraLarge
}
```

---

## 💡 Advanced Card Features (Future)

### 1. Carousel for Query History
```
[← Previous] Query 1 | Query 2 | Query 3 [Next →]
```

### 2. Input Forms for Filters
```
┌─────────────────────────┐
│ 📅 Date Range Filter     │
│ From: [2024-01-01]      │
│ To:   [2024-12-31]      │
│ [Apply Filter]          │
└─────────────────────────┘
```

### 3. Expandable/Collapsible Sections
```
📝 Generated SQL [▼]
  ┌─────────────────────┐
  │ SELECT * FROM ...   │
  └─────────────────────┘

📝 Generated SQL [▶]  (collapsed)
```

### 4. Data Visualization Hints
```
📊 This data can be visualized!
[View as Bar Chart] [View as Pie Chart]
```

---

## 📚 Resources

- **Adaptive Cards Schema:** https://adaptivecards.io/explorer/
- **Teams Card Reference:** https://docs.microsoft.com/en-us/microsoftteams/platform/task-modules-and-cards/cards/cards-reference
- **Card Designer Tool:** https://adaptivecards.io/designer/ (Build cards visually!)
- **Sample Cards:** https://github.com/microsoft/AdaptiveCards/tree/main/samples

---

## ✅ Testing Checklist

- [ ] Welcome card displays correctly
- [ ] Success card shows results properly
- [ ] Error card displays error message
- [ ] Help card is readable
- [ ] Cards render on desktop
- [ ] Cards render on mobile
- [ ] Action buttons are clickable
- [ ] SQL code block is formatted
- [ ] Result rows are easy to read
- [ ] Metadata footer is visible
- [ ] Colors match expectations
- [ ] Icons display correctly

---

## 🎉 Summary

**Before Adaptive Cards:**
- Plain text responses
- Hard to scan results
- No interactivity
- Poor mobile experience

**After Adaptive Cards:**
- ✅ Rich visual design with colors and structure
- ✅ Interactive buttons for quick actions
- ✅ Better readability and scanability
- ✅ Professional appearance
- ✅ Mobile-friendly responsive layout
- ✅ Guided user experience with suggestions

**Deploy now and see the difference!** 🚀
