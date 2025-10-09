"""
TERADATA-FI Data Generation Script - INCREMENTAL VERSION
Only generates missing data (DimDate completion + DimCustomer records)

This version skips data that was already seeded via MSSQL MCP:
- DimIndustry (10 records exist)
- DimLoanProduct (8 records exist)  
- Reference dimensions (risk ratings, statuses, etc.)

Generates:
- DimDate: Additional ~1,361 dates (already have 100)
- DimCustomer: 5,000 new customers (already have 120)

Author: NL2SQL Demo System
Date: 2025-10-09
Version: 1.1 (Incremental)
"""

import pyodbc
import random
import datetime
from datetime import timedelta
from faker import Faker
from decimal import Decimal

# Initialize
fake = Faker('en_US')
Faker.seed(42)
random.seed(42)

# Connection string - Using SQL Authentication from .env
CONNECTION_STRING = """
    DRIVER={ODBC Driver 18 for SQL Server};
    SERVER=aqsqlserver001.database.windows.net;
    DATABASE=TERADATA-FI;
    UID=arturoqu;
    PWD=Porkinos.72848677;
    Encrypt=yes;DATA
    TrustServerCertificate=no;
    Connection Timeout=30;
"""

# Data generation parameters
START_DATE = datetime.date(2022, 1, 1)
END_DATE = datetime.date(2025, 12, 31)
NUM_NEW_CUSTOMERS = 1000  # Generate 1,000 customers for faster demo (can scale up later)

def get_connection():
    """Establish database connection"""
    return pyodbc.connect(CONNECTION_STRING)

def date_to_datekey(dt):
    """Convert date to integer key (YYYYMMDD)"""
    return int(dt.strftime('%Y%m%d'))

def weighted_choice(choices, weights):
    """Select item from choices based on weights"""
    return random.choices(choices, weights=weights, k=1)[0]

def generate_dim_date_complete(conn):
    """Generate complete date dimension (skips existing dates)"""
    print("Generating complete DimDate dimension...")
    cursor = conn.cursor()
    
    # Get existing dates
    cursor.execute("SELECT DateKey FROM dim.DimDate")
    existing_keys = set(row[0] for row in cursor.fetchall())
    print(f"  Found {len(existing_keys)} existing date records")
    
    current = START_DATE
    batch = []
    inserted = 0
    
    while current <= END_DATE:
        date_key = date_to_datekey(current)
        
        # Skip if already exists
        if date_key in existing_keys:
            current += timedelta(days=1)
            continue
        
        year = current.year
        quarter = (current.month - 1) // 3 + 1
        month = current.month
        month_name = current.strftime('%B')
        week = current.isocalendar()[1]
        day_of_year = current.timetuple().tm_yday
        day_of_month = current.day
        day_of_week = current.isoweekday()
        day_name = current.strftime('%A')
        
        is_weekend = 1 if day_of_week in [6, 7] else 0
        is_quarter_end = 1 if month in [3, 6, 9, 12] and current.day >= 28 else 0
        is_year_end = 1 if month == 12 and current.day >= 28 else 0
        is_month_end = 1 if (current + timedelta(days=1)).month != month else 0
        
        # Fiscal year: Oct 1 - Sep 30
        fiscal_year = year if month >= 10 else year - 1
        fiscal_month = month - 9 if month >= 10 else month + 3
        fiscal_quarter = (fiscal_month - 1) // 3 + 1
        
        # Prior dates
        prior_day = current - timedelta(days=1)
        prior_week = current - timedelta(weeks=1)
        prior_month = current - timedelta(days=30)
        prior_quarter = current - timedelta(days=90)
        prior_year = current.replace(year=year-1) if year > START_DATE.year else current
        
        batch.append((
            date_key, current, year, quarter, month, month_name, week, day_of_year,
            day_of_month, day_of_week, day_name, is_weekend, 0, None,
            is_quarter_end, is_year_end, is_month_end,
            fiscal_year, fiscal_quarter, fiscal_month,
            prior_day, prior_week, prior_month, prior_quarter, prior_year
        ))
        
        if len(batch) >= 1000:
            cursor.executemany("""
                INSERT INTO dim.DimDate (
                    DateKey, [Date], [Year], Quarter, [Month], MonthName, [Week], DayOfYear,
                    DayOfMonth, DayOfWeek, DayName, IsWeekend, IsHoliday, HolidayName,
                    IsQuarterEnd, IsYearEnd, IsMonthEnd,
                    FiscalYear, FiscalQuarter, FiscalMonth,
                    PriorDay, PriorWeek, PriorMonth, PriorQuarter, PriorYear
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            inserted += len(batch)
            print(f"  Inserted {inserted} dates so far...")
            batch = []
        
        current += timedelta(days=1)
    
    if batch:
        cursor.executemany("""
            INSERT INTO dim.DimDate (
                DateKey, [Date], [Year], Quarter, [Month], MonthName, [Week], DayOfYear,
                DayOfMonth, DayOfWeek, DayName, IsWeekend, IsHoliday, HolidayName,
                IsQuarterEnd, IsYearEnd, IsMonthEnd,
                FiscalYear, FiscalQuarter, FiscalMonth,
                PriorDay, PriorWeek, PriorMonth, PriorQuarter, PriorYear
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        inserted += len(batch)
    
    print(f"  ✓ Inserted {inserted} new date records (total: {len(existing_keys) + inserted})")

def generate_dim_customer_bulk(conn, num_customers=NUM_NEW_CUSTOMERS):
    """Generate customer dimension records"""
    print(f"\nGenerating {num_customers} new DimCustomer records...")
    cursor = conn.cursor()
    
    # Get existing customer count to start IDs correctly
    cursor.execute("SELECT MAX(CAST(SUBSTRING(CustomerId, 5, 10) AS INT)) FROM dim.DimCustomer")
    max_id = cursor.fetchone()[0]
    start_id = (max_id or 0) + 1
    print(f"  Starting from CUST{start_id:05d}")
    
    # Get industry keys
    cursor.execute("SELECT IndustryKey, IndustryName FROM dim.DimIndustry")
    industries = {name: key for key, name in cursor.fetchall()}
    
    # Industry distribution (weighted to match real portfolios)
    # Use ACTUAL industry names from database
    industry_weights = {
        'Manufacturing': 0.22,
        'Healthcare Services': 0.18,
        'Software & IT Services': 0.15,
        'Retail Trade': 0.12,
        'Real Estate Development': 0.10,
        'Consulting & Legal': 0.08,
        'Freight & Logistics': 0.07,
        'Commercial Construction': 0.05,
        'Hotels & Restaurants': 0.02,
        'Wholesale Distribution': 0.01
    }
    
    entity_types = ['LLC', 'Corporation', 'Partnership', 'Corporation']
    segments = ['Small Business', 'Middle Market', 'Large Corporate']
    segment_weights = [0.60, 0.30, 0.10]
    tiers = ['Bronze', 'Silver', 'Gold', 'Platinum']
    tier_weights = [0.50, 0.30, 0.15, 0.05]
    risk_ratings = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC', 'CC', 'C']
    risk_weights = [0.02, 0.05, 0.15, 0.30, 0.25, 0.15, 0.05, 0.02, 0.01]
    
    batch = []
    for i in range(num_customers):
        customer_id = f'CUST{start_id + i:05d}'
        company_name = fake.company()
        tax_id = f"{random.randint(10,99)}-{random.randint(1000000,9999999)}"
        legal_entity = random.choice(entity_types)
        year_founded = random.randint(1985, 2020)
        
        # Segment drives revenue/employees
        segment = weighted_choice(segments, segment_weights)
        if segment == 'Small Business':
            employee_count = random.randint(5, 99)
            annual_revenue = random.randint(500000, 4999999)
            total_loans = random.randint(1, 3)
            total_volume = random.randint(500000, 4500000)
        elif segment == 'Middle Market':
            employee_count = random.randint(100, 999)
            annual_revenue = random.randint(5000000, 49999999)
            total_loans = random.randint(3, 10)
            total_volume = random.randint(5000000, 35000000)
        else:  # Large Corporate
            employee_count = random.randint(1000, 10000)
            annual_revenue = random.randint(50000000, 500000000)
            total_loans = random.randint(10, 25)
            total_volume = random.randint(35000000, 150000000)
        
        # Select industry (weighted)
        industry_name = weighted_choice(list(industry_weights.keys()), list(industry_weights.values()))
        primary_industry_id = industries[industry_name]
        
        # Get SIC/NAICS from industry (simplified - match actual DB industry names)
        sic_map = {
            'Manufacturing': '3300', 'Healthcare Services': '8000', 'Software & IT Services': '7370',
            'Retail Trade': '5300', 'Real Estate Development': '6500', 'Consulting & Legal': '8700',
            'Freight & Logistics': '4200', 'Commercial Construction': '1500', 'Hotels & Restaurants': '7000',
            'Wholesale Distribution': '5100'
        }
        naics_map = {
            'Manufacturing': '31-33', 'Healthcare Services': '62', 'Software & IT Services': '5112',
            'Retail Trade': '44-45', 'Real Estate Development': '5311', 'Consulting & Legal': '5416',
            'Freight & Logistics': '4841', 'Commercial Construction': '2361', 'Hotels & Restaurants': '7211',
            'Wholesale Distribution': '4240'
        }
        primary_sic = sic_map[industry_name]
        primary_naics = naics_map[industry_name]
        
        # Risk rating
        risk_rating = weighted_choice(risk_ratings, risk_weights)
        
        # Tier (VIP customers get Platinum)
        is_vip = 1 if random.random() < 0.10 else 0
        tier = 'Platinum' if is_vip else weighted_choice(tiers, tier_weights)
        
        # High risk industries - using actual DB names
        is_high_risk = 1 if industry_name in ['Commercial Construction', 'Hotels & Restaurants', 'Real Estate Development'] or risk_rating in ['CCC', 'CC', 'C'] else 0
        
        lifetime_revenue = int(total_volume * 0.05)  # 5% margin
        default_count = 0
        
        effective_date = datetime.date(2024, 1, 1)
        
        batch.append((
            customer_id, company_name, tax_id, legal_entity, year_founded, employee_count, annual_revenue,
            primary_industry_id, primary_sic, primary_naics,
            risk_rating, risk_rating, risk_rating, risk_rating,  # All ratings same for simplicity
            None, segment, tier,
            total_loans, total_volume, lifetime_revenue, default_count,
            1, is_high_risk, is_vip,
            effective_date, None, 1,
            datetime.datetime.now(), datetime.datetime.now()
        ))
        
        if len(batch) >= 500:
            cursor.executemany("""
                INSERT INTO dim.DimCustomer (
                    CustomerId, CompanyName, TaxId, LegalEntityType, YearFounded, EmployeeCount, AnnualRevenue,
                    PrimaryIndustryId, PrimarySICCode, PrimaryNAICSCode,
                    CreditRating_SP, CreditRating_Moody, CreditRating_Fitch, InternalRiskRating,
                    RelationshipManagerId, CustomerSegment, CustomerTier,
                    TotalLoansCount, TotalLoanVolume, LifetimeRevenue, DefaultCount,
                    IsActive, IsHighRisk, IsVIP,
                    EffectiveDate, EndDate, IsCurrent,
                    CreatedDate, ModifiedDate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            print(f"  Inserted {len(batch)} customers (total: {i+1})...")
            batch = []
    
    if batch:
        cursor.executemany("""
            INSERT INTO dim.DimCustomer (
                CustomerId, CompanyName, TaxId, LegalEntityType, YearFounded, EmployeeCount, AnnualRevenue,
                PrimaryIndustryId, PrimarySICCode, PrimaryNAICSCode,
                CreditRating_SP, CreditRating_Moody, CreditRating_Fitch, InternalRiskRating,
                RelationshipManagerId, CustomerSegment, CustomerTier,
                TotalLoansCount, TotalLoanVolume, LifetimeRevenue, DefaultCount,
                IsActive, IsHighRisk, IsVIP,
                EffectiveDate, EndDate, IsCurrent,
                CreatedDate, ModifiedDate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
    
    print(f"  ✓ Generated {num_customers} new customer records")

def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("TERADATA-FI Incremental Data Generation")
    print("="*70 + "\n")
    
    print("This script will:")
    print("  1. Complete DimDate dimension (2022-2025) - ~1,361 dates")
    print("  2. Generate 1,000 new customer records")
    print("  3. Skip existing reference data (already seeded via MSSQL MCP)")
    print("\nEstimated time: 3-5 minutes")
    print("\n" + "-"*70 + "\n")
    
    try:
        print("Connecting to database...")
        conn = get_connection()
        print("✓ Connected successfully!\n")
        
        # Generate missing data
        generate_dim_date_complete(conn)
        generate_dim_customer_bulk(conn)
        
        # Final summary
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM dim.DimDate")
        date_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM dim.DimCustomer")
        customer_count = cursor.fetchone()[0]
        
        print("\n" + "="*70)
        print("✓ Data Generation Complete!")
        print("="*70)
        print(f"\nFinal Data Summary:")
        print(f"  • DimDate records: {date_count:,}")
        print(f"  • DimCustomer records: {customer_count:,}")
        print(f"  • DimIndustry records: 10 (pre-existing)")
        print(f"  • DimLoanProduct records: 8 (pre-existing)")
        print(f"  • DimRiskRating records: 10 (pre-existing)")
        print(f"  • Reference dimensions: ~60 records (pre-existing)")
        
        print(f"\n📊 Ready for demos with {customer_count:,} customers across 10 industries!")
        print(f"\nNext Steps:")
        print(f"  1. Test customer segmentation queries")
        print(f"  2. Test industry analysis queries")
        print(f"  3. Generate fact table data (Phase 2)")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
