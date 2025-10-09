"""
TERADATA-FI Phase 2B: Additional Fact Table Data Generation
=============================================================

Generates transactional data for:
1. FACT_PAYMENT_TRANSACTION - Monthly payment records
2. FACT_LOAN_BALANCE_DAILY - Monthly balance snapshots
3. FACT_CUSTOMER_INTERACTION - Customer service interactions

This enriches the dataset with time-series data for advanced analytics.
"""

import pyodbc
import random
import datetime
import os
from datetime import timedelta
from dateutil.relativedelta import relativedelta
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

def generate_payments(conn):
    """Generate payment transactions for all active loans"""
    print(f"\nGenerating payment transactions...")
    cursor = conn.cursor()
    
    # Check existing payments
    cursor.execute("SELECT COUNT(*) FROM fact.FACT_PAYMENT_TRANSACTION")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"  ✓ Already have {existing_count} payment transactions")
        return existing_count
    
    # Get payment method and type keys
    cursor.execute("SELECT PaymentMethodKey, MethodName FROM dim.DimPaymentMethod")
    payment_methods = {name: key for key, name in cursor.fetchall()}
    
    cursor.execute("SELECT PaymentTypeKey, TypeName FROM dim.DimPaymentType")
    payment_types = {name: key for key, name in cursor.fetchall()}
    
    # Get all active loans with payment schedule info
    cursor.execute("""
        SELECT 
            l.LoanKey, l.LoanId, l.CustomerKey, l.OriginationDateKey, 
            l.FirstPaymentDateKey, l.TermMonths, l.CurrentBalance, l.OriginalAmount,
            l.InterestRate, l.PaymentsMade, l.PaymentsScheduled, l.MissedPayments,
            d.Date as OriginationDate, fp.Date as FirstPaymentDate
        FROM fact.FACT_LOAN_ORIGINATION l
        JOIN dim.DimDate d ON l.OriginationDateKey = d.DateKey
        JOIN dim.DimDate fp ON l.FirstPaymentDateKey = fp.DateKey
        WHERE l.IsActive = 1
        ORDER BY l.LoanKey
    """)
    
    loans = cursor.fetchall()
    print(f"  Found {len(loans)} active loans requiring payment history")
    
    # Payment method distribution
    method_weights = {
        'ACH Transfer': 0.70,
        'Wire Transfer': 0.15,
        'Check': 0.10,
        'Debit Card': 0.05
    }
    
    # Payment type distribution  
    type_weights = {
        'Scheduled Payment': 0.85,
        'Prepayment': 0.08,
        'Late Payment': 0.05,
        'Loan Payoff': 0.02
    }
    
    batch = []
    total_inserted = 0
    payment_id_counter = 1
    
    for loan in loans:
        (loan_key, loan_id, customer_key, orig_date_key, first_payment_date_key,
         term_months, current_balance, original_amount, interest_rate,
         payments_made, payments_scheduled, missed_payments,
         orig_date, first_payment_date) = loan
        
        # Convert to float for calculations
        original_amount = float(original_amount)
        current_balance = float(current_balance)
        
        # Calculate monthly payment (simple amortization)
        monthly_rate = float(interest_rate) / 100 / 12
        if monthly_rate > 0 and term_months > 0:
            monthly_payment = (original_amount * monthly_rate) / (1 - (1 + monthly_rate) ** -term_months)
        else:
            monthly_payment = original_amount / term_months if term_months > 0 else 0
        
        # Generate payment for each scheduled payment
        current_date = first_payment_date
        remaining_principal = original_amount
        
        for payment_num in range(1, payments_scheduled + 1):
            payment_id = f'PAY{payment_id_counter:08d}'
            payment_id_counter += 1
            
            # Determine if payment was made or missed
            is_missed = payment_num > payments_made
            
            if not is_missed:
                # Payment was made
                payment_date = current_date
                
                # Small chance of late payment (3-5 days late)
                if random.random() < 0.03:  # 3% late payment rate
                    payment_date = current_date + timedelta(days=random.randint(3, 15))
                
                # Find closest date key for actual payment date
                cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", payment_date)
                result = cursor.fetchone()
                payment_date_key = result[0] if result else first_payment_date_key
                
                # Find closest date key for scheduled payment date
                cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", current_date)
                result = cursor.fetchone()
                scheduled_date_key = result[0] if result else first_payment_date_key
                
                # Calculate days late
                days_late = max(0, (payment_date - current_date).days)
                is_late_payment = 1 if days_late > 0 else 0
                is_early_payment = 0  # Could add logic for early payments if needed
                
                # Calculate principal and interest portions
                interest_portion = remaining_principal * monthly_rate
                principal_portion = monthly_payment - interest_portion
                
                # Ensure we don't pay more principal than remaining
                if principal_portion > remaining_principal:
                    principal_portion = remaining_principal
                    
                actual_payment = principal_portion + interest_portion
                remaining_principal -= principal_portion
                
                # Payment method and type
                payment_method = weighted_choice(list(method_weights.keys()), list(method_weights.values()))
                payment_method_key = payment_methods[payment_method]
                
                payment_type = weighted_choice(list(type_weights.keys()), list(type_weights.values()))
                payment_type_key = payment_types[payment_type]
                
                # Fees (mostly 0, occasional late fee for payments more than 5 days late)
                late_fee = random.uniform(25, 75) if days_late > 5 else 0
                processing_fee = 0
                other_fees = 0
                total_fees = late_fee + processing_fee + other_fees
                
                # Determine if prepayment
                is_prepayment = 1 if payment_type == 'Prepayment' else 0
                
                # Total payment amount
                total_payment_amount = actual_payment + total_fees
                
                # Penalty amount (late fees)
                penalty_amount = late_fee if days_late > 5 else 0
                
                # Scheduled amount (the regular monthly payment)
                scheduled_amount = monthly_payment
                
                # Status flags
                is_reversed = 0
                
                now = datetime.datetime.now()
                
                batch.append((
                    payment_id, loan_key, payment_date_key, scheduled_date_key,
                    payment_method_key, payment_type_key,
                    total_payment_amount, principal_portion, interest_portion,
                    total_fees, penalty_amount, scheduled_amount,
                    payment_num, days_late,
                    is_early_payment, is_late_payment, is_prepayment, is_reversed,
                    now, now
                ))
                
                if len(batch) >= BATCH_SIZE:
                    cursor.executemany("""
                        INSERT INTO fact.FACT_PAYMENT_TRANSACTION (
                            PaymentId, LoanKey, PaymentDateKey, ScheduledDateKey,
                            PaymentMethodKey, PaymentTypeKey,
                            TotalPaymentAmount, PrincipalAmount, InterestAmount,
                            FeesAmount, PenaltyAmount, ScheduledAmount,
                            PaymentNumber, DaysLate,
                            IsEarlyPayment, IsLatePayment, IsPrepayment, IsReversed,
                            CreatedDate, ModifiedDate
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    conn.commit()
                    total_inserted += len(batch)
                    print(f"  Inserted {total_inserted} payments...")
                    batch = []
            
            # Move to next month
            current_date = current_date + relativedelta(months=1)
    
    # Insert remaining batch
    if batch:
        cursor.executemany("""
            INSERT INTO fact.FACT_PAYMENT_TRANSACTION (
                PaymentId, LoanKey, PaymentDateKey, ScheduledDateKey,
                PaymentMethodKey, PaymentTypeKey,
                TotalPaymentAmount, PrincipalAmount, InterestAmount,
                FeesAmount, PenaltyAmount, ScheduledAmount,
                PaymentNumber, DaysLate,
                IsEarlyPayment, IsLatePayment, IsPrepayment, IsReversed,
                CreatedDate, ModifiedDate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        total_inserted += len(batch)
    
    print(f"  ✓ Generated {total_inserted} payment transactions")
    return total_inserted

def generate_balances(conn):
    """Generate monthly balance snapshots"""
    print(f"\nGenerating loan balance snapshots...")
    cursor = conn.cursor()
    
    # Check existing balances
    cursor.execute("SELECT COUNT(*) FROM fact.FACT_LOAN_BALANCE_DAILY")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"  ✓ Already have {existing_count} balance snapshots")
        return existing_count
    
    # Get all loans
    cursor.execute("""
        SELECT 
            l.LoanKey, l.CustomerKey, l.OriginationDateKey, 
            l.OriginalAmount, l.CurrentBalance, l.InterestRate, l.TermMonths,
            d.Date as OriginationDate
        FROM fact.FACT_LOAN_ORIGINATION l
        JOIN dim.DimDate d ON l.OriginationDateKey = d.DateKey
        ORDER BY l.LoanKey
    """)
    
    loans = cursor.fetchall()
    print(f"  Found {len(loans)} loans")
    print(f"  Generating monthly balance snapshots from origination to present...")
    
    batch = []
    total_inserted = 0
    
    end_date = datetime.date(2024, 12, 31)  # Snapshot through end of 2024
    
    for loan in loans:
        (loan_key, customer_key, orig_date_key, original_amount, 
         current_balance, interest_rate, term_months, orig_date) = loan
        
        # Convert to float
        original_amount = float(original_amount)
        current_balance = float(current_balance)
        monthly_rate = float(interest_rate) / 100 / 12
        
        # Calculate monthly payment
        if monthly_rate > 0 and term_months > 0:
            monthly_payment = (original_amount * monthly_rate) / (1 - (1 + monthly_rate) ** -term_months)
        else:
            monthly_payment = original_amount / term_months if term_months > 0 else 0
        
        # Generate snapshots for each month
        snapshot_date = orig_date
        remaining_principal = original_amount
        month_count = 0
        
        while snapshot_date <= end_date and month_count < term_months:
            # Find date key
            cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", snapshot_date)
            result = cursor.fetchone()
            snapshot_date_key = result[0] if result else orig_date_key
            
            # Calculate interest for the month
            interest_accrued = remaining_principal * monthly_rate
            
            # Principal payment
            principal_payment = monthly_payment - interest_accrued
            if principal_payment > remaining_principal:
                principal_payment = remaining_principal
            
            # Update balance
            beginning_balance = remaining_principal
            remaining_principal = max(0, remaining_principal - principal_payment)
            ending_balance = remaining_principal
            
            # Days in month
            days_in_period = 30
            
            # Delinquency (matches loan table)
            days_past_due = 0
            
            now = datetime.datetime.now()
            
            batch.append((
                loan_key, customer_key, snapshot_date_key,
                beginning_balance, ending_balance,
                principal_payment, interest_accrued,
                monthly_payment, days_in_period, days_past_due,
                now, now
            ))
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany("""
                    INSERT INTO fact.FACT_LOAN_BALANCE_DAILY (
                        LoanKey, CustomerKey, BalanceDateKey,
                        BeginningBalance, EndingBalance,
                        PrincipalPaid, InterestAccrued,
                        ScheduledPayment, DaysInPeriod, DaysPastDue,
                        CreatedDate, ModifiedDate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                total_inserted += len(batch)
                print(f"  Inserted {total_inserted} balance snapshots...")
                batch = []
            
            # Move to next month
            snapshot_date = snapshot_date + relativedelta(months=1)
            month_count += 1
    
    # Insert remaining batch
    if batch:
        cursor.executemany("""
            INSERT INTO fact.FACT_LOAN_BALANCE_DAILY (
                LoanKey, CustomerKey, BalanceDateKey,
                BeginningBalance, EndingBalance,
                PrincipalPaid, InterestAccrued,
                ScheduledPayment, DaysInPeriod, DaysPastDue,
                CreatedDate, ModifiedDate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        total_inserted += len(batch)
    
    print(f"  ✓ Generated {total_inserted} balance snapshots")
    return total_inserted

def generate_interactions(conn):
    """Generate customer service interactions"""
    print(f"\nGenerating customer interactions...")
    cursor = conn.cursor()
    
    # Check existing interactions
    cursor.execute("SELECT COUNT(*) FROM fact.FACT_CUSTOMER_INTERACTION")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"  ✓ Already have {existing_count} interactions")
        return existing_count
    
    # Get interaction types
    cursor.execute("SELECT InteractionTypeKey, TypeName FROM dim.DimInteractionType")
    interaction_types = [(key, name) for key, name in cursor.fetchall()]
    
    # Get all customers
    cursor.execute("SELECT CustomerKey FROM dim.DimCustomer WHERE IsCurrent = 1")
    customers = [row[0] for row in cursor.fetchall()]
    
    print(f"  Generating interactions for {len(customers)} customers...")
    
    # Interaction patterns: 2-12 interactions per customer over 2 years
    batch = []
    total_inserted = 0
    interaction_id_counter = 1
    
    start_date = datetime.date(2023, 1, 1)
    end_date = datetime.date(2024, 12, 31)
    
    for customer_key in customers:
        # Random number of interactions per customer
        num_interactions = random.randint(2, 12)
        
        for _ in range(num_interactions):
            interaction_id = f'INT{interaction_id_counter:08d}'
            interaction_id_counter += 1
            
            # Random date
            days_diff = (end_date - start_date).days
            interaction_date = start_date + timedelta(days=random.randint(0, days_diff))
            
            # Find date key
            cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", interaction_date)
            result = cursor.fetchone()
            interaction_date_key = result[0] if result else 20230101
            
            # Interaction type
            type_key, type_name = random.choice(interaction_types)
            
            # Duration (minutes) - adjusted for actual interaction types
            if type_name in ['Sales Call', 'Service Request', 'Collections Call']:
                duration = random.randint(5, 45)
            elif type_name in ['Compliance Check', 'Account Review']:
                duration = random.randint(30, 120)
            else:
                duration = random.randint(2, 10)
            
            # Outcome
            outcomes = ['Resolved', 'Follow-up Required', 'Escalated', 'Information Provided']
            outcome = weighted_choice(outcomes, [0.60, 0.25, 0.10, 0.05])
            
            # Notes
            notes = f'{type_name} interaction - {outcome}'
            
            # Flags
            is_inbound = 1 if random.random() < 0.70 else 0
            is_resolved = 1 if outcome == 'Resolved' else 0
            requires_followup = 1 if outcome == 'Follow-up Required' else 0
            
            now = datetime.datetime.now()
            
            batch.append((
                interaction_id, customer_key, interaction_date_key, type_key,
                duration, outcome, notes,
                is_inbound, is_resolved, requires_followup,
                now, now
            ))
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany("""
                    INSERT INTO fact.FACT_CUSTOMER_INTERACTION (
                        InteractionId, CustomerKey, InteractionDateKey, InteractionTypeKey,
                        DurationMinutes, Outcome, Notes,
                        IsInbound, IsResolved, RequiresFollowup,
                        CreatedDate, ModifiedDate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                total_inserted += len(batch)
                print(f"  Inserted {total_inserted} interactions...")
                batch = []
    
    # Insert remaining batch
    if batch:
        cursor.executemany("""
            INSERT INTO fact.FACT_CUSTOMER_INTERACTION (
                InteractionId, CustomerKey, InteractionDateKey, InteractionTypeKey,
                DurationMinutes, Outcome, Notes,
                IsInbound, IsResolved, RequiresFollowup,
                CreatedDate, ModifiedDate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        total_inserted += len(batch)
    
    print(f"  ✓ Generated {total_inserted} customer interactions")
    return total_inserted

def main():
    """Main execution"""
    print("=" * 70)
    print("TERADATA-FI Phase 2B: Additional Fact Table Data Generation")
    print("=" * 70)
    print(f"\nThis script will generate:")
    print(f"  1. Payment transactions for all active loans")
    print(f"  2. Monthly balance snapshots showing loan progression")
    print(f"  3. Customer service interactions (calls, emails, meetings)")
    print(f"\nEstimated time: 5-10 minutes")
    print("-" * 70)
    
    try:
        print("\nConnecting to database...")
        conn = get_connection()
        print("✓ Connected successfully!")
        
        # Generate payments
        payment_count = generate_payments(conn)
        
        # Generate balances
        balance_count = generate_balances(conn)
        
        # Generate interactions
        interaction_count = generate_interactions(conn)
        
        # Get final counts
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM fact.FACT_PAYMENT_TRANSACTION")
        total_payments = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(PaymentAmount) FROM fact.FACT_PAYMENT_TRANSACTION WHERE IsSuccessful = 1")
        total_payment_volume = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM fact.FACT_LOAN_BALANCE_DAILY")
        total_balances = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM fact.FACT_CUSTOMER_INTERACTION")
        total_interactions = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT CustomerKey) FROM fact.FACT_CUSTOMER_INTERACTION")
        customers_with_interactions = cursor.fetchone()[0]
        
        print("\n" + "=" * 70)
        print("✓ Phase 2B Data Generation Complete!")
        print("=" * 70)
        print(f"\nFinal Data Summary:")
        print(f"  • Payment Transactions: {total_payments:,}")
        print(f"  • Total Payment Volume: ${total_payment_volume:,.2f}")
        print(f"  • Balance Snapshots: {total_balances:,}")
        print(f"  • Customer Interactions: {total_interactions:,}")
        print(f"  • Customers with Interactions: {customers_with_interactions:,}")
        print(f"\n📊 Complete transactional dataset ready for advanced analytics!")
        print(f"\nNext Steps:")
        print(f"  1. Run validation queries to verify data quality")
        print(f"  2. Test complex multi-table analytical queries")
        print(f"  3. Configure NL2SQL app to connect to TERADATA-FI")
        print(f"  4. Generate comprehensive demo question bank")
        
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
