"""
TERADATA-FI Phase 2: Fact Table Data Generation
================================================

Generates realistic transactional data for all 7 fact tables:
1. FACT_LOAN_APPLICATION - Loan applications
2. FACT_LOAN_ORIGINATION - Originated loans
3. FACT_LOAN_BALANCE_DAILY - Daily balance snapshots
4. FACT_PAYMENT_TRANSACTION - Payment transactions
5. FACT_CUSTOMER_INTERACTION - Customer interactions
6. FACT_CUSTOMER_FINANCIALS - Quarterly financials
7. FACT_COVENANT_TEST - Covenant compliance tests

Approach:
- Generate applications first (base for everything)
- Convert approved apps to loans
- Generate balances from loans
- Generate payments for active loans
- Generate interactions throughout customer lifecycle
- Generate quarterly financials and covenant tests
"""

import pyodbc
import random
import datetime
import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Connection configuration
SERVER = os.getenv('AZURE_SQL_SERVER', 'aqsqlserver001.database.windows.net')
DATABASE = 'TERADATA-FI'
USERNAME = os.getenv('AZURE_SQL_USER')
PASSWORD = os.getenv('AZURE_SQL_PASSWORD')

CONNECTION_STRING = (
    f'DRIVER={{ODBC Driver 18 for SQL Server}};'
    f'SERVER={SERVER};'
    f'DATABASE={DATABASE};'
    f'UID={USERNAME};'
    f'PWD={PASSWORD};'
    f'Encrypt=yes;'
    f'TrustServerCertificate=no;'
    f'Connection Timeout=30;'
)

# Configuration
NUM_APPLICATIONS = 3000  # Target number of loan applications
APPROVAL_RATE = 0.75  # 75% approval rate
CONVERSION_RATE = 0.85  # 85% of approved apps convert to loans
BATCH_SIZE = 500

def get_connection():
    """Get database connection"""
    return pyodbc.connect(CONNECTION_STRING)

def weighted_choice(choices, weights):
    """Select from choices based on weights"""
    return random.choices(choices, weights=weights, k=1)[0]

def date_to_datekey(date):
    """Convert date to YYYYMMDD integer key"""
    return int(date.strftime('%Y%m%d'))

def generate_applications(conn):
    """Generate loan applications"""
    print(f"\nGenerating loan applications...")
    cursor = conn.cursor()
    
    # Check for existing applications
    cursor.execute("SELECT COUNT(*) FROM fact.FACT_LOAN_APPLICATION")
    existing_count = cursor.fetchone()[0]
    
    if existing_count >= NUM_APPLICATIONS:
        print(f"  ✓ Already have {existing_count} applications (target: {NUM_APPLICATIONS})")
        return existing_count
    
    remaining = NUM_APPLICATIONS - existing_count
    print(f"  Found {existing_count} existing applications")
    print(f"  Generating {remaining} additional applications...")
    
    # Get dimension data
    cursor.execute("SELECT CustomerKey FROM dim.DimCustomer WHERE IsCurrent = 1")
    customer_keys = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT ProductKey FROM dim.DimLoanProduct")
    product_keys = [row[0] for row in cursor.fetchall()]
    
    cursor.execute("SELECT StatusKey, StatusName FROM dim.DimApplicationStatus")
    statuses = {name: key for key, name in cursor.fetchall()}
    
    cursor.execute("SELECT DateKey, [Date] FROM dim.DimDate WHERE [Year] >= 2023 AND [Year] <= 2024 ORDER BY DateKey")
    date_keys = [(row[0], row[1]) for row in cursor.fetchall()]
    
    # Application statuses with weights
    status_weights = {
        'Approved': 0.60,
        'Declined': 0.20,
        'Withdrawn by Applicant': 0.10,
        'Under Review': 0.08,
        'Submitted': 0.02
    }
    
    # Term lengths in months
    term_options = [12, 24, 36, 48, 60, 84, 120, 180, 240]
    term_weights = [0.05, 0.10, 0.20, 0.20, 0.25, 0.10, 0.05, 0.03, 0.02]
    
    batch = []
    inserted = 0
    
    for i in range(existing_count, NUM_APPLICATIONS):
        app_id = f'APP{i+1:06d}'
        customer_key = random.choice(customer_keys)
        
        # Application date (spread across 2023-2024)
        app_date_key, app_date = random.choice(date_keys)
        
        product_key = random.choice(product_keys)
        
        # Requested amount based on customer segment (get from customer)
        cursor.execute("SELECT CustomerSegment, AnnualRevenue FROM dim.DimCustomer WHERE CustomerKey = ?", customer_key)
        segment, revenue = cursor.fetchone()
        
        if segment == 'Small Business':
            requested_amount = random.randint(50000, 500000)
        elif segment == 'Middle Market':
            requested_amount = random.randint(500000, 5000000)
        else:  # Large Corporate
            requested_amount = random.randint(5000000, 50000000)
        
        requested_term = weighted_choice(term_options, term_weights)
        
        # Determine approval status
        status_name = weighted_choice(list(status_weights.keys()), list(status_weights.values()))
        status_key = statuses[status_name]
        
        is_approved = 1 if status_name == 'Approved' else 0
        
        # For approved applications
        approved_amount = None
        approved_term = None
        decision_date_key = None
        decision_code = None
        decision_reason = None
        review_duration = None
        is_converted = 0
        
        if status_name in ['Approved', 'Declined']:
            # Decision made 3-21 days after application
            review_duration = random.randint(3, 21)
            decision_date = app_date + timedelta(days=review_duration)
            
            # Find closest date key
            cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", decision_date)
            result = cursor.fetchone()
            decision_date_key = result[0] if result else None
            
            if status_name == 'Approved':
                # Approved: may adjust amount/term
                approved_amount = requested_amount if random.random() < 0.70 else int(requested_amount * random.uniform(0.80, 0.95))
                approved_term = requested_term if random.random() < 0.80 else weighted_choice(term_options, term_weights)
                decision_code = 'APPROVED'
                decision_reason = 'Meets credit criteria'
                
                # 85% conversion rate for approved apps
                is_converted = 1 if random.random() < CONVERSION_RATE else 0
            else:
                decision_code = weighted_choice(['DTI_HIGH', 'CREDIT_LOW', 'COLLATERAL', 'CASH_FLOW'], [0.35, 0.30, 0.20, 0.15])
                reasons = {
                    'DTI_HIGH': 'Debt-to-income ratio exceeds policy limits',
                    'CREDIT_LOW': 'Credit score below minimum threshold',
                    'COLLATERAL': 'Insufficient collateral value',
                    'CASH_FLOW': 'Insufficient cash flow to service debt'
                }
                decision_reason = reasons[decision_code]
        
        # Credit metrics
        credit_score = random.randint(580, 850) if is_approved else random.randint(520, 700)
        debt_to_income = round(random.uniform(0.15, 0.65), 2)
        internal_risk_score = random.randint(300, 900)
        
        now = datetime.datetime.now()
        
        batch.append((
            app_id, customer_key, app_date_key, decision_date_key, product_key, None,  # PurposeKey
            status_key, requested_amount, approved_amount, requested_term, approved_term,
            credit_score, debt_to_income, revenue, internal_risk_score,
            decision_code, decision_reason, review_duration, None,  # OriginatedLoanKey
            is_approved, is_converted, now, now
        ))
        
        if len(batch) >= BATCH_SIZE:
            cursor.executemany("""
                INSERT INTO fact.FACT_LOAN_APPLICATION (
                    ApplicationId, CustomerKey, ApplicationDateKey, DecisionDateKey, ProductKey, PurposeKey,
                    ApplicationStatusKey, RequestedAmount, ApprovedAmount, RequestedTerm, ApprovedTerm,
                    CreditScoreAtApplication, DebtToIncomeRatio, AnnualRevenue, InternalRiskScore,
                    DecisionCode, DecisionReason, ReviewDuration_Days, OriginatedLoanKey,
                    IsApproved, IsConverted, CreatedDate, ModifiedDate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            inserted += len(batch)
            print(f"  Inserted {inserted} applications...")
            batch = []
    
    if batch:
        cursor.executemany("""
            INSERT INTO fact.FACT_LOAN_APPLICATION (
                ApplicationId, CustomerKey, ApplicationDateKey, DecisionDateKey, ProductKey, PurposeKey,
                ApplicationStatusKey, RequestedAmount, ApprovedAmount, RequestedTerm, ApprovedTerm,
                CreditScoreAtApplication, DebtToIncomeRatio, AnnualRevenue, InternalRiskScore,
                DecisionCode, DecisionReason, ReviewDuration_Days, OriginatedLoanKey,
                IsApproved, IsConverted, CreatedDate, ModifiedDate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        inserted += len(batch)
    
    total = existing_count + inserted
    print(f"  ✓ Generated {inserted} new applications (total: {total})")
    return total

def generate_loans(conn):
    """Generate originated loans from approved/converted applications"""
    print(f"\nGenerating originated loans...")
    cursor = conn.cursor()
    
    # Get approved and converted applications
    cursor.execute("""
        SELECT 
            ApplicationKey, ApplicationId, CustomerKey, ProductKey, PurposeKey,
            ApprovedAmount, ApprovedTerm, DecisionDateKey
        FROM fact.FACT_LOAN_APPLICATION
        WHERE IsApproved = 1 AND IsConverted = 1
    """)
    applications = cursor.fetchall()
    
    print(f"  Found {len(applications)} approved applications to convert to loans")
    
    # Get delinquency status keys - use hardcoded value for "Current" status
    # StatusKey 1 = Current (0 days delinquent)
    current_status_key = 1
    
    batch = []
    inserted = 0
    loan_keys_map = {}  # Map ApplicationKey to LoanKey for updating
    
    for i, app in enumerate(applications):
        (app_key, app_id, customer_key, product_key, purpose_key, 
         approved_amount, term_months, decision_date_key) = app
        
        loan_id = f'LOAN{i+1:06d}'
        
        # Origination date: 7-30 days after decision
        cursor.execute("SELECT [Date] FROM dim.DimDate WHERE DateKey = ?", decision_date_key)
        decision_date = cursor.fetchone()[0]
        orig_date = decision_date + timedelta(days=random.randint(7, 30))
        
        cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", orig_date)
        result = cursor.fetchone()
        orig_date_key = result[0] if result else decision_date_key
        
        # Maturity date
        cursor.execute("SELECT [Date] FROM dim.DimDate WHERE DateKey = ?", orig_date_key)
        orig_date = cursor.fetchone()[0]
        maturity_date = orig_date + timedelta(days=term_months * 30)
        
        cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", maturity_date)
        result = cursor.fetchone()
        maturity_date_key = result[0] if result else orig_date_key
        
        # First payment date: 30 days after origination
        first_payment_date = orig_date + timedelta(days=30)
        cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", first_payment_date)
        result = cursor.fetchone()
        first_payment_date_key = result[0] if result else orig_date_key
        
        # Loan amounts - convert Decimal to float for calculations
        original_amount = float(approved_amount)
        funded_amount = float(original_amount)  # Assume full funding
        
        # Calculate months since origination
        today = datetime.date(2024, 12, 31)  # Use end of 2024 as "today"
        months_elapsed = max(0, (today.year - orig_date.year) * 12 + (today.month - orig_date.month))
        months_elapsed = min(months_elapsed, term_months)  # Cap at term
        
        # Payment schedule
        payments_scheduled = months_elapsed
        payments_made = payments_scheduled - random.randint(0, max(0, int(payments_scheduled * 0.05)))  # 95%+ on-time
        missed_payments = payments_scheduled - payments_made
        late_payments = random.randint(0, min(2, payments_made))  # Small number of late payments
        
        # Calculate balances
        monthly_payment = (original_amount * (0.06/12)) / (1 - (1 + 0.06/12)**-term_months) if term_months > 0 else 0
        principal_paid = (monthly_payment * payments_made * 0.75)  # ~75% goes to principal over life
        interest_paid = (monthly_payment * payments_made * 0.25)  # ~25% goes to interest
        current_balance = max(0, funded_amount - principal_paid)
        
        remaining_term_months = max(0, term_months - months_elapsed)
        
        # Interest rate
        base_rates = {'Fixed': (4.5, 12.0), 'Variable': (3.5, 10.0)}
        rate_type = 'Fixed' if random.random() < 0.60 else 'Variable'
        interest_rate = round(random.uniform(*base_rates[rate_type]), 2)
        
        reference_rate = 'SOFR' if rate_type == 'Variable' else None
        margin = round(random.uniform(1.5, 4.5), 2) if rate_type == 'Variable' else None
        apr = round(interest_rate + random.uniform(0.1, 0.5), 2)
        
        # Fees
        origination_fee = original_amount * random.uniform(0.005, 0.02)
        processing_fee = random.uniform(500, 2500)
        other_fees = random.uniform(0, 1000)
        total_fees = origination_fee + processing_fee + other_fees
        
        # Collateral and LTV
        collateral_value = original_amount * random.uniform(1.10, 1.50) if random.random() < 0.70 else None
        ltv = round((original_amount / collateral_value * 100), 2) if collateral_value else None
        
        # Delinquency
        days_delinquent = 0
        delinquency_status_key = current_status_key
        if missed_payments > 0:
            days_delinquent = random.randint(1, min(90, missed_payments * 30))
            # Update delinquency status based on days - use hardcoded keys
            # 1=Current, 2=1-29, 3=30-59, 4=60-89, 5=90+, 6=Charged Off
            if days_delinquent >= 90:
                delinquency_status_key = 5  # 90+ Days
            elif days_delinquent >= 60:
                delinquency_status_key = 4  # 60-89 Days
            elif days_delinquent >= 30:
                delinquency_status_key = 3  # 30-59 Days
            else:
                delinquency_status_key = 2  # 1-29 Days
        
        # Performance metrics
        npv = original_amount * random.uniform(0.05, 0.15)
        irr = round(random.uniform(8.0, 18.0), 2)
        roe = round(random.uniform(12.0, 25.0), 2)
        yield_pct = round(random.uniform(interest_rate - 1, interest_rate + 2), 2)
        
        # Status flags
        is_active = 1 if current_balance > 0 and days_delinquent < 120 else 0
        is_paid_off = 1 if current_balance == 0 and payments_made >= payments_scheduled else 0
        is_charged_off = 1 if days_delinquent >= 120 else 0
        is_restructured = 1 if days_delinquent > 60 and random.random() < 0.20 else 0
        has_personal_guarantee = 1 if random.random() < 0.40 else 0
        
        now = datetime.datetime.now()
        
        batch.append((
            loan_id, customer_key, orig_date_key, maturity_date_key, first_payment_date_key,
            product_key, purpose_key, delinquency_status_key,
            original_amount, funded_amount, current_balance, principal_paid, interest_paid,
            term_months, remaining_term_months, interest_rate, rate_type, reference_rate, margin, apr,
            origination_fee, processing_fee, other_fees, total_fees,
            collateral_value, ltv, days_delinquent,
            payments_made, payments_scheduled, missed_payments, late_payments,
            npv, irr, roe, yield_pct,
            is_active, is_paid_off, is_charged_off, is_restructured, has_personal_guarantee,
            now, now
        ))
        
        if len(batch) >= BATCH_SIZE:
            cursor.executemany("""
                INSERT INTO fact.FACT_LOAN_ORIGINATION (
                    LoanId, CustomerKey, OriginationDateKey, MaturityDateKey, FirstPaymentDateKey,
                    ProductKey, PurposeKey, DelinquencyStatusKey,
                    OriginalAmount, FundedAmount, CurrentBalance, PrincipalPaid, InterestPaid,
                    TermMonths, RemainingTermMonths, InterestRate, RateType, ReferenceRate, Margin, APR,
                    OriginationFee, ProcessingFee, OtherFees, TotalFeesCollected,
                    CollateralValue, LTV, DaysDelinquent,
                    PaymentsMade, PaymentsScheduled, MissedPayments, LatePayments,
                    NPV, IRR, ROE, Yield,
                    IsActive, IsPaidOff, IsChargedOff, IsRestructured, HasPersonalGuarantee,
                    CreatedDate, ModifiedDate
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            conn.commit()
            inserted += len(batch)
            print(f"  Inserted {inserted} loans...")
            batch = []
    
    if batch:
        cursor.executemany("""
            INSERT INTO fact.FACT_LOAN_ORIGINATION (
                LoanId, CustomerKey, OriginationDateKey, MaturityDateKey, FirstPaymentDateKey,
                ProductKey, PurposeKey, DelinquencyStatusKey,
                OriginalAmount, FundedAmount, CurrentBalance, PrincipalPaid, InterestPaid,
                TermMonths, RemainingTermMonths, InterestRate, RateType, ReferenceRate, Margin, APR,
                OriginationFee, ProcessingFee, OtherFees, TotalFeesCollected,
                CollateralValue, LTV, DaysDelinquent,
                PaymentsMade, PaymentsScheduled, MissedPayments, LatePayments,
                NPV, IRR, ROE, Yield,
                IsActive, IsPaidOff, IsChargedOff, IsRestructured, HasPersonalGuarantee,
                CreatedDate, ModifiedDate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        inserted += len(batch)
    
    print(f"  ✓ Generated {inserted} originated loans")
    
    # Update applications with loan keys
    print(f"  Updating application records with loan keys...")
    cursor.execute("""
        UPDATE a
        SET a.OriginatedLoanKey = l.LoanKey
        FROM fact.FACT_LOAN_APPLICATION a
        JOIN fact.FACT_LOAN_ORIGINATION l ON a.CustomerKey = l.CustomerKey 
            AND a.ApprovedAmount = l.OriginalAmount
        WHERE a.IsConverted = 1 AND a.OriginatedLoanKey IS NULL
    """)
    conn.commit()
    print(f"  ✓ Updated application linkages")
    
    return inserted

def main():
    """Main execution"""
    print("=" * 70)
    print("TERADATA-FI Phase 2: Fact Table Data Generation")
    print("=" * 70)
    print(f"\nThis script will generate:")
    print(f"  1. {NUM_APPLICATIONS:,} loan applications")
    print(f"  2. ~{int(NUM_APPLICATIONS * APPROVAL_RATE * CONVERSION_RATE):,} originated loans (from approved applications)")
    print(f"  3. Additional fact tables (interactions, balances, etc.) in future phases")
    print(f"\nEstimated time: 5-10 minutes")
    print("-" * 70)
    
    try:
        print("\nConnecting to database...")
        conn = get_connection()
        print("✓ Connected successfully!")
        
        # Generate applications
        app_count = generate_applications(conn)
        
        # Generate loans from approved applications
        loan_count = generate_loans(conn)
        
        # Get final counts
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM fact.FACT_LOAN_APPLICATION")
        total_apps = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fact.FACT_LOAN_APPLICATION WHERE IsApproved = 1")
        approved_apps = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fact.FACT_LOAN_ORIGINATION")
        total_loans = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fact.FACT_LOAN_ORIGINATION WHERE IsActive = 1")
        active_loans = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(CurrentBalance) FROM fact.FACT_LOAN_ORIGINATION WHERE IsActive = 1")
        total_balance = cursor.fetchone()[0] or 0
        
        print("\n" + "=" * 70)
        print("✓ Phase 2 Data Generation Complete!")
        print("=" * 70)
        print(f"\nFinal Data Summary:")
        print(f"  • Total Applications: {total_apps:,}")
        print(f"  • Approved Applications: {approved_apps:,} ({approved_apps/total_apps*100:.1f}%)")
        print(f"  • Total Loans: {total_loans:,}")
        print(f"  • Active Loans: {active_loans:,}")
        print(f"  • Total Active Balance: ${total_balance:,.2f}")
        print(f"\n📊 Ready for advanced analytics and NL2SQL demos!")
        print(f"\nNext Steps:")
        print(f"  1. Generate daily balance snapshots (FACT_LOAN_BALANCE_DAILY)")
        print(f"  2. Generate payment transactions (FACT_PAYMENT_TRANSACTION)")
        print(f"  3. Generate customer interactions (FACT_CUSTOMER_INTERACTION)")
        print(f"  4. Generate quarterly financials (FACT_CUSTOMER_FINANCIALS)")
        print(f"  5. Generate covenant tests (FACT_COVENANT_TEST)")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
