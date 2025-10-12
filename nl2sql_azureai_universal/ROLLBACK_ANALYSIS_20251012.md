# Rollback Analysis - October 12, 2025

## Summary
Reverted from broken revision **v218fix** back to known-good **v215healthz** baseline.

---

## Timeline

| Revision | Date | Status | Description |
|----------|------|--------|-------------|
| v215healthz | Oct 11, 2025 | ✅ **Working** | Last stable revision; proper results display, clean SQL preview |
| v217healthz (0000024) | Oct 12, 2025 | ❌ Failed | Intermediate revision; unhealthy |
| v218fix | Oct 12, 2025 | ❌ **Broken** | Latest attempt; malformed SQL truncation footer, "No rows returned" |

---

## What Broke in v218fix

### 1. **Adaptive Card SQL Truncation Logic**
**Problem**: Added footer fact `("SQL", "(truncated for display)")` rendered as broken text in Teams instead of clean display.

**Evidence** (screenshot 2):
- Shows malformed `(truncated for display)` text in card
- SQL preview area displays incorrectly
- "No rows returned" instead of actual result table

**Root Cause**: 
- Footer fact syntax incompatible with Adaptive Cards JSON schema
- Should have used inline text annotation or separate TextBlock, not a fact pair

### 2. **Possible Read-Only SQL Guard Bug**
**Hypothesis**: New `is_read_only_sql()` function may have rejected valid SELECT statements.

**Code Added**:
```python
def is_read_only_sql(sql: str) -> bool:
    """Check if SQL is read-only (SELECT/WITH/SHOW)."""
    sql_upper = sql.strip().upper()
    return sql_upper.startswith(('SELECT', 'WITH', 'SHOW', 'EXPLAIN', 'DESCRIBE'))
```

**Potential Issue**: 
- Pattern too strict (missing CASE variations, comments before SELECT)
- Rejected legitimate queries → "No rows returned"

### 3. **Config.py Import Dependency**
**Problem**: Added `from config import Settings` but `config.py` wasn't in v215healthz Docker image.

**Impact**:
- Import error on container startup OR
- Wrong environment variable defaults → connection/execution failures

### 4. **Session TTL Cleanup**
**Lower Risk**: Added `_cleanup_stale_sessions()` logic with `last_activity` timestamps.

**Potential Issue**: Session cleanup may have prematurely deleted active threads.

---

## What Worked in v215healthz (Baseline)

✅ **No SQL truncation logic** → clean full SQL display  
✅ **No read-only guard** → all queries executed  
✅ **No config.py dependency** → direct `os.getenv()` calls  
✅ **Simple session management** → no TTL expiry interference  
✅ **Proper results display** → tables with data shown correctly  
✅ **Insights generation** → business recommendations rendered  

**Screenshot 1 Evidence**:
- "Query Results: Found 2 result(s)"
- Clean Generated SQL section (no truncation artifacts)
- Results table: 2 rows with CustomerKey, CompanyName, TotalSales, OrderCount
- Business Insights: detailed recommendations
- Elapsed Time: 32.84s, Tokens: 10243

---

## Reverted Changes

### Files Restored to v215healthz State
```bash
git checkout HEAD -- adaptive_cards.py nl2sql_main.py Dockerfile
rm -f config.py
```

### Removed Features
1. ❌ SQL truncation in Adaptive Cards
2. ❌ `config.py` centralized settings
3. ❌ Read-only SQL guard
4. ❌ Session TTL cleanup
5. ❌ TypedDict annotations
6. ❌ Dockerfile WORKDIR simplification

---

## Lessons Learned

### 1. **Test Adaptive Cards JSON Before Deploy**
- Adaptive Cards have strict schema requirements
- Footer facts must match exact structure
- Always validate with [Adaptive Cards Designer](https://adaptivecards.io/designer/) before pushing

### 2. **Incremental Feature Deployment**
- **DON'T**: Bundle 5+ features in one image (truncation + guard + config + TTL + types)
- **DO**: One feature per revision with rollback plan
- Example safe path:
  1. Add config.py → test → deploy
  2. Add SQL guard → test → deploy
  3. Add truncation (validated JSON) → test → deploy

### 3. **Container Image Validation**
- Verify all new imports (`config.py`) are in Docker COPY manifest
- Check `start_server.py` can import all modules before build
- Run local Docker build + test before ACR push

### 4. **Log Debugging Info**
- Add startup log line: "Image tag: v2.1.8-fix, config loaded: true"
- Log feature toggles: "Read-only guard: enabled, session TTL: 3600s"
- Helps correlate revision failures to specific features

### 5. **Keep Working Baseline Safe**
- Tag stable commits: `git tag v215healthz-stable 9433047`
- Maintain separate branch for experiments
- Always test against Teams/ACA staging slot first

---

## Next Steps (Safe Incremental Path)

### Phase 1: Restore Stability ✅
- [x] Revert to v215healthz code baseline
- [ ] Rebuild image with tag `v2.1.9-baseline-restore`
- [ ] Deploy to ACA and confirm Teams functionality matches screenshot 1

### Phase 2: Add ONE Feature (Read-Only Guard) - **OPTIONAL**
Only proceed if user wants this; otherwise stay at baseline.

**Implementation**:
1. Add ONLY read-only guard to `nl2sql_main.py`
2. Improve regex to handle edge cases:
   ```python
   # Strip comments and whitespace before checking
   sql_clean = re.sub(r'--.*$', '', sql, flags=re.MULTILINE).strip()
   ```
3. Add unit tests: test_read_only_guard.py
4. Build → tag `v2.1.10-readonly-guard`
5. Deploy → test 5 queries in Teams → monitor logs
6. If breaks: instant rollback to v2.1.9

### Phase 3: Add Truncation (If Needed) - **HOLD**
**Only if SQL statements commonly exceed Teams card limits (32KB)**

Better approach than footer fact:
```python
# In adaptive_cards.py create_success_card:
if len(sql) > 500:
    sql_display = sql[:500] + "\n\n... (query continues, showing first 500 chars)"
else:
    sql_display = sql
```

No footer artifacts—just inline ellipsis.

---

## Root Cause: Why "No rows returned"?

**Most Likely**: Read-only guard false-rejected query OR config import failed → execution error swallowed.

**Smoking Gun**: Screenshot 2 shows "No rows returned" but also displays SQL that *should* have run (it's a valid SELECT TOP 50...).

**Hypothesis**:
1. `is_read_only_sql()` matched correctly
2. Execution happened
3. **BUT**: Some other error (connection timeout, permissions, schema mismatch) caused empty result
4. Insight agent still ran (using cached context?) but had no data
5. Result: malformed card display + empty table

**Fix for Future**: Log execution errors explicitly before returning empty results.

---

## Action Items

- [ ] User confirms v215healthz is active and working in Teams
- [ ] Rebuild baseline image from reverted code: `v2.1.9-baseline-restore`
- [ ] Deploy v2.1.9 to ACA, deactivate v218fix permanently
- [ ] Git commit revert: `git commit -m "Revert quick-wins to v215healthz baseline"`
- [ ] Create feature branch for future experiments: `git checkout -b feature/incremental-improvements`
- [ ] Add unit tests before next feature attempt

---

## Files Modified (Reverted)

```
M  nl2sql_azureai_universal/adaptive_cards.py     (reverted)
M  nl2sql_azureai_universal/nl2sql_main.py        (reverted)
M  nl2sql_azureai_universal/Dockerfile            (reverted)
D  nl2sql_azureai_universal/config.py             (deleted)
```

**Baseline Commit**: `9433047` (Oct 10, 2025)
**Known-Good Image**: Built from this commit → deployed as v215healthz

---

## Testing Checklist (Before Future Deploys)

### Local Docker Test
```bash
cd nl2sql_azureai_universal
docker build -t nl2sql-local:test .
docker run -p 3978:3978 --env-file .env nl2sql-local:test

# In another terminal:
curl http://localhost:3978/healthz
# Expect: {"status":"ok"} or similar

# Check logs for import errors:
docker logs <container_id>
```

### Adaptive Card JSON Validation
1. Export card JSON from `adaptive_cards.py`
2. Paste into https://adaptivecards.io/designer/
3. Verify rendering (no broken text artifacts)
4. Test all interactive elements (buttons, inputs)

### Teams Bot Test (Staging)
1. Deploy to separate test slot: `nl2sql-teams-bot-staging`
2. Test 5 queries:
   - Simple SELECT
   - Complex JOIN
   - Invalid query (expect error card)
   - Long query (test truncation if enabled)
   - Forbidden statement (if guard enabled)
3. Verify insights, results table, elapsed time all render correctly
4. Check no regressions in conversation memory

### ACA Health Check
```bash
# After deploy, wait 60s for health probe
az containerapp revision show \
  -g AQ-BOT-RG \
  -n nl2sql-teams-bot \
  --revision <NEW_REV> \
  --query "properties.healthState"

# Expect: "Healthy"
# If "Unhealthy": immediately deactivate and rollback
```

---

## Conclusion

**v218fix broke due to untested Adaptive Card schema changes and bundled feature complexity.**

**Safe path forward**: Stay at v215healthz baseline until incremental features are individually validated with:
1. Local Docker test
2. Unit tests
3. Adaptive Card designer validation
4. Staging slot deployment
5. 24-hour bake time before production traffic

**Current State**: Code reverted to v215healthz baseline, ready for clean rebuild.
