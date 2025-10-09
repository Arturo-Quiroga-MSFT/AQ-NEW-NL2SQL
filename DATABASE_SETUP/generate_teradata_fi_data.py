"""
TERADATA-FI Data Generation Script
Phase 1: Core Dimensions & Facts Seeding

This script generates realistic commercial lending data for demo purposes.
Covers: 3 years historical data (2022-2025), 5,000 customers, 50,000 applications, 12,000 loans

Author: NL2SQL Demo System
Date: 2025-10-09
Version: 1.0
"""

import pyodbc
import random
import datetime
from datetime import timedelta
from faker import Faker
from decimal import Decimal
import json

# Initialize
fake = Faker('en_US')
Faker.seed(42)  # Reproducible data
random.seed(42)

# ========================================
# Configuration
# ========================================

# Connection string - Using Azure AD authentication
# Note: Make sure you're logged in with 'az login' before running this script
CONNECTION_STRING = """
    DRIVER={ODBC Driver 18 for SQL Server};
    SERVER=aqsqlserver001.database.windows.net;
    DATABASE=TERADATA-FI;
    Authentication=ActiveDirectoryInteractive;
    Encrypt=yes;
    TrustServerCertificate=no;
    Connection Timeout=30;
"""

# Data generation parameters
START_DATE = datetime.date(2022, 1, 1)
END_DATE = datetime.date(2025, 12, 31)
NUM_CUSTOMERS = 5000
NUM_APPLICATIONS = 50000
NUM_LOANS = 12000
NUM_EMPLOYEES = 150
NUM_BRANCHES = 25

# ========================================
# Helper Functions
# ========================================

def get_connection():
    """Establish database connection"""
    return pyodbc.connect(CONNECTION_STRING)

def date_to_datekey(dt):
    """Convert date to integer key (YYYYMMDD)"""
    return int(dt.strftime('%Y%m%d'))

def random_date(start, end):
    """Generate random date between start and end"""
    delta = end - start
    random_days = random.randint(0, delta.days)
    return start + timedelta(days=random_days)

def weighted_choice(choices, weights):
    """Select item from choices based on weights"""
    return random.choices(choices, weights=weights, k=1)[0]

# ========================================
# Dimension Generation Functions
# ========================================

def generate_dim_date(conn):
    """Generate complete date dimension from START_DATE to END_DATE"""
    print("Generating DimDate...")
    cursor = conn.cursor()
    
    current = START_DATE
    batch = []
    
    while current <= END_DATE:
        date_key = date_to_datekey(current)
        year = current.year
        quarter = (current.month - 1) // 3 + 1
        month = current.month
        month_name = current.strftime('%B')
        week = current.isocalendar()[1]
        day_of_year = current.timetuple().tm_yday
        day_of_month = current.day
        day_of_week = current.isoweekday()  # 1=Monday, 7=Sunday
        day_name = current.strftime('%A')
        
        is_weekend = 1 if day_of_week in [6, 7] else 0
        is_quarter_end = 1 if month in [3, 6, 9, 12] and day_of_month >= 28 else 0
        is_year_end = 1 if month == 12 and day_of_month >= 28 else 0
        is_month_end = 1 if (current + timedelta(days=1)).month != month else 0
        
        # Fiscal year: Oct 1 - Sep 30
        fiscal_year = year if month >= 10 else year - 1
        fiscal_month = month - 9 if month >= 10 else month + 3
        fiscal_quarter = (fiscal_month - 1) // 3 + 1
        
        # Prior dates
        prior_day = current - timedelta(days=1)
        prior_week = current - timedelta(weeks=1)
        prior_month_approx = current - timedelta(days=30)
        prior_quarter_approx = current - timedelta(days=90)
        prior_year = current.replace(year=year-1) if year > START_DATE.year else None
        
        batch.append((
            date_key, current, year, quarter, month, month_name, week, day_of_year,
            day_of_month, day_of_week, day_name, is_weekend, 0, None,  # Holiday fields
            is_quarter_end, is_year_end, is_month_end,
            fiscal_year, fiscal_quarter, fiscal_month,
            prior_day, prior_week, prior_month_approx, prior_quarter_approx, prior_year
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
    
    print(f"  ✓ Generated {(END_DATE - START_DATE).days + 1} date records")

def generate_dim_industry(conn):
    """Generate industry dimension"""
    print("Generating DimIndustry...")
    cursor = conn.cursor()
    
    industries = [
        ('IND001', 'Manufacturing', 'Industrial', 'Manufacturing', '3300', '336000', 'Medium', 0.0350, 0.6500, 1, 0),
        ('IND002', 'Healthcare', 'Healthcare', 'Healthcare Services', '8000', '621000', 'Low', 0.0120, 0.8200, 1, 0),
        ('IND003', 'Technology', 'Technology', 'Software & IT Services', '7370', '541500', 'Medium', 0.0280, 0.7500, 0, 1),
        ('IND004', 'Retail', 'Retail', 'Retail Trade', '5300', '445000', 'High', 0.0480, 0.5800, 0, 1),
        ('IND005', 'Construction', 'Construction', 'Commercial Construction', '1500', '236000', 'High', 0.0520, 0.5500, 0, 1),
        ('IND006', 'Real Estate', 'Real Estate', 'Real Estate Development', '6500', '531000', 'Medium', 0.0380, 0.6800, 1, 1),
        ('IND007', 'Transportation', 'Transportation', 'Freight & Logistics', '4200', '484000', 'Medium', 0.0320, 0.6200, 0, 0),
        ('IND008', 'Hospitality', 'Services', 'Hotels & Restaurants', '7000', '721000', 'High', 0.0550, 0.5200, 0, 1),
        ('IND009', 'Professional Services', 'Services', 'Consulting & Legal', '8700', '541100', 'Low', 0.0180, 0.7800, 0, 0),
        ('IND010', 'Wholesale', 'Wholesale', 'Wholesale Distribution', '5100', '424000', 'Medium', 0.0350, 0.6500, 0, 0),
    ]
    
    cursor.executemany("""
        INSERT INTO dim.DimIndustry (
            IndustryId, IndustrySector, IndustryGroup, IndustryName, SICCode, NAICSCode,
            RiskProfile, DefaultRate_Historical, RecoveryRate_Historical,
            IsRegulated, IsVolatile
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, industries)
    conn.commit()
    
    print(f"  ✓ Generated {len(industries)} industry records")

def generate_dim_loan_product(conn):
    """Generate loan product dimension"""
    print("Generating DimLoanProduct...")
    cursor = conn.cursor()
    
    products = [
        ('PROD001', 'Term Loan - 5 Year', 'Commercial', 'Standard Term Loan', 100000, 5000000, 60, 60, 'Fixed', None, 500, 1, 0, 1, 2.0, 1),
        ('PROD002', 'Term Loan - 7 Year', 'Commercial', 'Standard Term Loan', 250000, 10000000, 84, 84, 'Fixed', None, 550, 1, 1, 1, 1.5, 1),
        ('PROD003', 'Revolving Line of Credit', 'Commercial', 'Working Capital Line', 50000, 2000000, 12, 36, 'Variable', 'SOFR', 250, 0, 0, 1, 0.0, 1),
        ('PROD004', 'SBA 7(a) Loan', 'SBA', 'Small Business Admin Guarantee', 50000, 5000000, 120, 300, 'Variable', 'Prime', 275, 1, 1, 1, 0.0, 1),
        ('PROD005', 'Commercial Real Estate', 'Real Estate', 'Property Acquisition/Refinance', 500000, 25000000, 120, 360, 'Fixed', None, 200, 1, 0, 1, 3.0, 1),
        ('PROD006', 'Equipment Financing', 'Equipment', 'Equipment Purchase', 25000, 1000000, 24, 84, 'Fixed', None, 400, 1, 0, 1, 0.0, 1),
        ('PROD007', 'Bridge Loan', 'Commercial', 'Short-term Financing', 100000, 5000000, 6, 24, 'Variable', 'SOFR', 600, 1, 0, 1, 5.0, 1),
        ('PROD008', 'Construction Loan', 'Real Estate', 'New Construction', 1000000, 50000000, 12, 36, 'Variable', 'SOFR', 350, 1, 1, 1, 2.0, 1),
    ]
    
    cursor.executemany("""
        INSERT INTO dim.DimLoanProduct (
            ProductId, ProductName, ProductCategory, ProductType,
            MinAmount, MaxAmount, MinTerm, MaxTerm, BaseRateType, ReferenceRateType,
            MarginBps, RequiresCollateral, RequiresPersonalGuarantee,
            AllowsPrepayment, PrepaymentPenaltyPercent, IsActive
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, products)
    conn.commit()
    
    print(f"  ✓ Generated {len(products)} product records")

def generate_reference_dimensions(conn):
    """Generate small reference dimensions"""
    print("Generating reference dimensions...")
    cursor = conn.cursor()
    
    # DimRiskRating
    risk_ratings = [
        ('AAA', 'Prime - Exceptional', 'Investment Grade', 10, 0.0010, 0.2500, 0.0025),
        ('AA', 'Prime - Excellent', 'Investment Grade', 9, 0.0025, 0.2500, 0.0050),
        ('A', 'Prime - Good', 'Investment Grade', 8, 0.0050, 0.3000, 0.0100),
        ('BBB', 'Investment Grade', 'Investment Grade', 7, 0.0100, 0.3500, 0.0150),
        ('BB', 'Sub-Investment Grade', 'Sub-Investment Grade', 6, 0.0250, 0.4000, 0.0300),
        ('B', 'Speculative', 'Sub-Investment Grade', 5, 0.0500, 0.5000, 0.0600),
        ('CCC', 'High Risk', 'Sub-Investment Grade', 4, 0.1000, 0.6000, 0.1200),
        ('CC', 'Very High Risk', 'Sub-Investment Grade', 3, 0.2000, 0.7000, 0.2500),
        ('C', 'Extremely High Risk', 'Sub-Investment Grade', 2, 0.3500, 0.8000, 0.4000),
        ('D', 'Default', 'Default', 1, 1.0000, 0.9000, 1.0000),
    ]
    cursor.executemany("""
        INSERT INTO dim.DimRiskRating (RiskRatingCode, RiskRatingName, RiskCategory, NumericScore,
                                        PD_Probability, LGD_Probability, RequiredProvision_Percent)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, risk_ratings)
    
    # DimDelinquencyStatus
    delinquency_statuses = [
        ('CURRENT', 'Current', 0, 0, 1, 0, 0),
        ('DPD30', '1-30 Days Past Due', 1, 30, 1, 0, 0),
        ('DPD60', '31-60 Days Past Due', 31, 60, 1, 0, 0),
        ('DPD90', '61-90 Days Past Due', 61, 90, 1, 0, 0),
        ('NPL', 'Non-Performing Loan (90+ DPD)', 91, 999999, 0, 1, 1),
        ('CHARGEOFF', 'Charged Off', 180, 999999, 0, 1, 0),
    ]
    cursor.executemany("""
        INSERT INTO dim.DimDelinquencyStatus (StatusCode, StatusName, MinDaysDelinquent, MaxDaysDelinquent,
                                               IsPerforming, IsNonPerforming, RequiresRestructuring)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, delinquency_statuses)
    
    # DimApplicationStatus
    app_statuses = [
        ('SUBMITTED', 'Submitted', 'Pending', 1, 0, 1),
        ('UNDERREVIEW', 'Under Review', 'Pending', 1, 0, 2),
        ('APPROVED', 'Approved', 'Approved', 1, 1, 3),
        ('DECLINED', 'Declined', 'Declined', 0, 1, 4),
        ('WITHDRAWN', 'Withdrawn by Applicant', 'Withdrawn', 0, 1, 5),
        ('EXPIRED', 'Expired', 'Expired', 0, 1, 6),
    ]
    cursor.executemany("""
        INSERT INTO dim.DimApplicationStatus (StatusCode, StatusName, StatusCategory, IsActive, IsTerminal, SortOrder)
        VALUES (?, ?, ?, ?, ?, ?)
    """, app_statuses)
    
    # DimPaymentMethod
    payment_methods = [
        ('ACH', 'ACH Transfer', 'Electronic bank-to-bank transfer', 0.00, 1, 1),
        ('WIRE', 'Wire Transfer', 'Same-day wire transfer', 15.00, 0, 1),
        ('CHECK', 'Check', 'Paper check', 0.00, 5, 0),
        ('DEBIT', 'Debit Card', 'Debit card payment', 2.50, 0, 1),
    ]
    cursor.executemany("""
        INSERT INTO dim.DimPaymentMethod (MethodCode, MethodName, MethodDescription, ProcessingFee, ProcessingDays, IsElectronic)
        VALUES (?, ?, ?, ?, ?, ?)
    """, payment_methods)
    
    # DimPaymentType
    payment_types = [
        ('SCHEDULED', 'Scheduled Payment', 'Regular scheduled payment'),
        ('PREPAYMENT', 'Prepayment', 'Early/extra payment'),
        ('LATE', 'Late Payment', 'Payment after due date'),
        ('PAYOFF', 'Loan Payoff', 'Final payment closing loan'),
    ]
    cursor.executemany("""
        INSERT INTO dim.DimPaymentType (TypeCode, TypeName, TypeDescription)
        VALUES (?, ?, ?)
    """, payment_types)
    
    conn.commit()
    print("  ✓ Generated reference dimension records")

def generate_dim_customer(conn, num_customers=NUM_CUSTOMERS):
    """Generate customer dimension with SCD Type 2"""
    print(f"Generating DimCustomer ({num_customers} records)...")
    cursor = conn.cursor()
    
    # Get industry keys
    cursor.execute("SELECT IndustryKey, IndustryId FROM dim.DimIndustry")
    industries = cursor.fetchall()
    
    entity_types = ['LLC', 'Corp', 'Partnership', 'Sole Proprietorship']
    segments = ['Small Business', 'Middle Market', 'Corporate']
    tiers = ['Bronze', 'Silver', 'Gold', 'Platinum']
    risk_ratings = ['AAA', 'AA', 'A', 'BBB', 'BB', 'B', 'CCC']
    
    batch = []
    for i in range(1, num_customers + 1):
        customer_id = f'CUST{i:06d}'
        company_name = fake.company()
        tax_id = fake.bothify(text='##-#######')
        legal_entity = weighted_choice(entity_types, [0.5, 0.3, 0.15, 0.05])
        year_founded = random.randint(1980, 2020)
        employee_count = weighted_choice([25, 75, 200, 500, 1200], [0.4, 0.3, 0.15, 0.10, 0.05])
        annual_revenue = employee_count * random.randint(80000, 150000)
        
        primary_industry = random.choice(industries)[1]
        segment = weighted_choice(segments, [0.6, 0.3, 0.1])
        tier = weighted_choice(tiers, [0.5, 0.3, 0.15, 0.05])
        risk_rating = weighted_choice(risk_ratings, [0.05, 0.15, 0.25, 0.30, 0.15, 0.08, 0.02])
        
        is_high_risk = 1 if risk_rating in ['B', 'CCC'] else 0
        is_vip = 1 if tier == 'Platinum' else 0
        
        effective_date = START_DATE
        
        batch.append((
            customer_id, company_name, tax_id, legal_entity, year_founded, employee_count, annual_revenue,
            None, None, None,  # Industry/Address FKs (populate later)
            None, None, None, risk_rating,  # Credit ratings
            None, segment, tier,  # Relationship manager, segment, tier
            0, 0, 0, 0,  # Portfolio metrics (updated later)
            1, is_high_risk, is_vip,  # Flags
            effective_date, None, 1  # SCD Type 2
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
                    EffectiveDate, EndDate, IsCurrent
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
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
                EffectiveDate, EndDate, IsCurrent
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
    
    print(f"  ✓ Generated {num_customers} customer records")

# ========================================
# Main Execution
# ========================================

def main():
    """Main execution function"""
    print("\n" + "="*60)
    print("TERADATA-FI Data Generation - Phase 1")
    print("="*60 + "\n")
    
    try:
        conn = get_connection()
        print("✓ Connected to database\n")
        
        # Generate dimensions first (required for FK relationships)
        generate_dim_date(conn)
        generate_dim_industry(conn)
        generate_dim_loan_product(conn)
        generate_reference_dimensions(conn)
        generate_dim_customer(conn)
        
        print("\n" + "="*60)
        print("Phase 1 Data Generation Complete!")
        print("="*60)
        print(f"\nNext Steps:")
        print(f"1. Generate remaining dimensions (DimEmployee, DimBranch, etc.)")
        print(f"2. Generate fact table data (Applications, Originations, etc.)")
        print(f"3. Run data validation queries")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
