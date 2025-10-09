# NL2SQL Multi-Model V2 - Hardcoded Questions Update

## Overview

Created a new version of the multi-model Streamlit app (`app_multimodel_v2.py`) with **hardcoded example questions** instead of loading from an external file.

## Changes Made

### 1. **New Streamlit App: `app_multimodel_v2.py`**
   - **Location**: `/ui/streamlit_app/app_multimodel_v2.py`
   - **Key Change**: Questions are now hardcoded in the `EXAMPLE_QUESTIONS` list
   - **Removed**: File-loading logic from `_load_examples()` function
   - **Benefits**:
     - No dependency on external `CONTOSO-FI_EXAMPLE_QUESTIONS.txt` file
     - Questions always available, regardless of file system issues
     - Easier to maintain and version control

### 2. **New Dockerfile: `Dockerfile.multimodel_v2`**
   - **Location**: `/azure_deployment/Dockerfile.multimodel_v2`
   - **Key Change**: CMD runs `app_multimodel_v2.py` instead of `app_multimodel.py`
   - **Purpose**: Deploy the new version with hardcoded questions

### 3. **Hardcoded Questions** (Curated from Question Bank)

The following 12 questions are now hardcoded:

#### **EASY (3 questions)**
1. Show the 10 most recent loans by OriginationDate.
2. Show the 10 upcoming loan maturities (soonest MaturityDate first) with principal amount and status.
3. List 20 companies with their industry and credit rating.

#### **MEDIUM (4 questions)**
4. For each company with loans, compute total principal amount; show the top 20 companies by total principal.
5. Average interest rate by industry and region (join Loan → Company → Country → Region).
6. Count of loans by status per country (join Loan → Company → Country).
7. Total collateral value per loan with the associated company name; show the top 20 by total collateral value.

#### **COMPLICATED (3 questions)**
8. For each loan, compute month-over-month change in EndingPrincipal from PaymentSchedule; show 20 loans with the largest absolute change (include positive/negative flags).
9. Covenant compliance rate by industry: percentage of covenant tests with Status = 'Pass' (all-time), grouped by industry and calendar quarter.
10. Weighted average interest rate by region and currency (weighted by PrincipalAmount).

#### **STRESS - Advanced SQL (2 questions)**
11. As-of-balance: for each region, using the latest available DueDate per loan from PaymentSchedule, sum EndingPrincipal by company and show the top 3 companies per region with each company's share of the region total.
12. Delinquency buckets by month and region: using PaymentEvent, bucket DaysDelinquent into 0–29, 30–59, 60–89, and 90+ and show, for the 6 most recent months in the data, each bucket's percentage of total per region.

## Deployment Instructions

### Option A: Build and Deploy V2 (Recommended)

```bash
# 1. Build new V2 image
az acr build --registry acrnl2sqlddo6f5dplg5v4 \
  --image nl2sql-multimodel:V4 \
  -f azure_deployment/Dockerfile.multimodel_v2 .

# 2. Update Container App with V4
az containerapp update \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --image acrnl2sqlddo6f5dplg5v4.azurecr.io/nl2sql-multimodel:V4
```

### Option B: Keep Original Dockerfile, Just Update Questions

If you prefer to keep the original Dockerfile and just want to update the questions in `app_multimodel.py`:

```bash
# 1. Update the original app_multimodel.py with hardcoded questions
# 2. Rebuild with existing Dockerfile
az acr build --registry acrnl2sqlddo6f5dplg5v4 \
  --image nl2sql-multimodel:V4 \
  -f azure_deployment/Dockerfile.multimodel .

# 3. Update Container App
az containerapp update \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --image acrnl2sqlddo6f5dplg5v4.azurecr.io/nl2sql-multimodel:V4
```

## File Structure

```
AQ-NEW-NL2SQL/
├── ui/
│   └── streamlit_app/
│       ├── app_multimodel.py       # Original (loads from file)
│       └── app_multimodel_v2.py    # NEW (hardcoded questions)
│
└── azure_deployment/
    ├── Dockerfile.multimodel        # Original
    └── Dockerfile.multimodel_v2     # NEW (uses app_multimodel_v2.py)
```

## Benefits of V2 Approach

1. **Reliability**: Questions always available, no file I/O errors
2. **Simplicity**: No need to manage external question files
3. **Version Control**: Questions versioned with the code
4. **Performance**: Slightly faster startup (no file reading)
5. **Deployment**: Easier to deploy, fewer dependencies

## Future Updates

To update questions in the future:

1. Edit `app_multimodel_v2.py` and modify the `EXAMPLE_QUESTIONS` list
2. Rebuild the Docker image with a new version tag
3. Deploy the new version to Azure Container Apps

## Verification

After deployment, verify:
1. Visit the app URL
2. Check that the 12 hardcoded questions appear as buttons
3. Test a few questions to ensure they work correctly
4. Check that the UI indicates "Multi-Model Optimized V2"

## Rollback

If needed, rollback to V3 (previous version):

```bash
az containerapp update \
  --name nl2sql-app-dev \
  --resource-group rg-nl2sql-app \
  --image acrnl2sqlddo6f5dplg5v4.azurecr.io/nl2sql-multimodel:V3
```

---

**Created**: October 9, 2025  
**Version**: V2 (Hardcoded Questions)  
**Author**: AI Assistant
