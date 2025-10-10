"""
TERADATA-FI Phase 2B: Balance Snapshots and Customer Interactions
Generates monthly balance snapshots and customer interactions for demo queries
"""

import pyodbc
import os
import random
import datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BATCH_SIZE = 500

def weighted_choice(choices, weights):
    """Select a random choice based on weights"""
    total = sum(weights)
    normalized = [w/total for w in weights]
    return random.choices(choices, weights=normalized)[0]

def get_connection():
    """Establish database connection"""
    server = os.getenv('AZURE_SQL_SERVER', 'aqsqlserver001.database.windows.net')
    database = 'TERADATA-FI'  # Hardcoded database name
    username = os.getenv('AZURE_SQL_USER')
    password = os.getenv('AZURE_SQL_PASSWORD')
    
    conn_str = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};Encrypt=yes;TrustServerCertificate=no'
    return pyodbc.connect(conn_str)

def generate_balances(conn):
    """Generate monthly balance snapshots showing loan progression"""
    print(f"\nGenerating loan balance snapshots...")
    cursor = conn.cursor()
    
    # Check existing balances
    cursor.execute("SELECT COUNT(*) FROM fact.FACT_LOAN_BALANCE_DAILY")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"  ✓ Already have {existing_count} balance snapshots")
        user_input = input(f"  Continue adding more balance snapshots? (y/n): ")
        if user_input.lower() != 'y':
            return existing_count
    
    # Get all loans with their details
    cursor.execute("""
        SELECT 
            l.LoanKey, l.OriginationDateKey, l.FirstPaymentDateKey,
            l.TermMonths, l.CurrentBalance, l.OriginalAmount, l.InterestRate,
            l.PaymentsMade, l.PaymentsScheduled,
            d.Date as OriginationDate, 
            fp.Date as FirstPaymentDate
        FROM fact.FACT_LOAN_ORIGINATION l
        JOIN dim.DimDate d ON l.OriginationDateKey = d.DateKey
        JOIN dim.DimDate fp ON l.FirstPaymentDateKey = fp.DateKey
        WHERE l.IsActive = 1
        ORDER BY l.LoanKey
    """)
    
    loans = cursor.fetchall()
    print(f"  Found {len(loans)} active loans")
    print(f"  Generating monthly balance snapshots from origination through 2024...")
    
    # Get delinquency statuses
    cursor.execute("SELECT DelinquencyStatusKey, StatusName FROM dim.DimDelinquencyStatus")
    delinquency_statuses = {name: key for key, name in cursor.fetchall()}
    
    batch = []
    total_inserted = 0
    
    end_date = datetime.date(2024, 12, 31)
    
    for loan in loans:
        (loan_key, orig_date_key, first_payment_date_key, term_months, 
         current_balance, original_amount, interest_rate, 
         payments_made, payments_scheduled,
         orig_date, first_payment_date) = loan
        
        # Convert to float for calculations
        original_amount = float(original_amount)
        current_balance = float(current_balance)
        monthly_rate = float(interest_rate) / 100 / 12
        
        # Calculate monthly payment (amortization formula)
        if monthly_rate > 0 and term_months > 0:
            monthly_payment = (original_amount * monthly_rate) / (1 - (1 + monthly_rate) ** -term_months)
        else:
            monthly_payment = original_amount / term_months if term_months > 0 else 0
        
        # Generate monthly snapshots from first payment date
        snapshot_date = first_payment_date
        remaining_principal = original_amount
        month_num = 0
        
        while snapshot_date <= end_date and month_num < payments_scheduled:
            # Find date key for snapshot
            cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", snapshot_date)
            result = cursor.fetchone()
            snapshot_date_key = result[0] if result else first_payment_date_key
            
            # Calculate interest accrued in this month
            interest_accrued = remaining_principal * monthly_rate
            
            # Principal payment (if payment was made)
            if month_num < payments_made:
                principal_payment = monthly_payment - interest_accrued
                if principal_payment > remaining_principal:
                    principal_payment = remaining_principal
                remaining_principal = max(0, remaining_principal - principal_payment)
            else:
                # No payment made yet
                principal_payment = 0
            
            # Calculate delinquency
            days_delinquent = 0
            if month_num >= payments_made and month_num < payments_scheduled:
                # Payment was due but not made
                days_late = (datetime.date.today() - snapshot_date).days
                days_delinquent = max(0, days_late)
            
            # Determine delinquency status
            if days_delinquent == 0:
                delinq_status = delinquency_statuses['Current']
            elif days_delinquent <= 30:
                delinq_status = delinquency_statuses['1-30 Days Past Due']
            elif days_delinquent <= 60:
                delinq_status = delinquency_statuses['31-60 Days Past Due']
            elif days_delinquent <= 90:
                delinq_status = delinquency_statuses['61-90 Days Past Due']
            else:
                delinq_status = delinquency_statuses['Non-Performing Loan (90+ DPD)']
            
            # Delinquent amount
            delinquent_amount = monthly_payment if days_delinquent > 0 else 0
            
            # Allowance (credit loss reserve based on balance and delinquency)
            if days_delinquent == 0:
                allowance_rate = 0.01  # 1% for current loans
            elif days_delinquent <= 30:
                allowance_rate = 0.03  # 3% for 1-30 DPD
            elif days_delinquent <= 60:
                allowance_rate = 0.10  # 10% for 31-60 DPD
            elif days_delinquent <= 90:
                allowance_rate = 0.25  # 25% for 61-90 DPD
            else:
                allowance_rate = 0.50  # 50% for NPL
            
            allowance = remaining_principal * allowance_rate
            
            now = datetime.datetime.now()
            
            batch.append((
                loan_key, snapshot_date_key, delinq_status,
                remaining_principal,  # PrincipalBalance
                0,  # InterestBalance (unpaid interest)
                0,  # FeesBalance
                remaining_principal,  # TotalBalance
                interest_accrued,  # AccruedInterest for the month
                days_delinquent,
                delinquent_amount,
                allowance,
                now
            ))
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany("""
                    INSERT INTO fact.FACT_LOAN_BALANCE_DAILY (
                        LoanKey, SnapshotDateKey, DelinquencyStatusKey,
                        PrincipalBalance, InterestBalance, FeesBalance, TotalBalance,
                        AccruedInterest, DaysDelinquent, DelinquentAmount, Allowance,
                        CreatedDate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                total_inserted += len(batch)
                print(f"  Inserted {total_inserted} balance snapshots...")
                batch = []
            
            # Move to next month
            month_num += 1
            snapshot_date = snapshot_date + relativedelta(months=1)
    
    # Insert remaining batch
    if batch:
        cursor.executemany("""
            INSERT INTO fact.FACT_LOAN_BALANCE_DAILY (
                LoanKey, SnapshotDateKey, DelinquencyStatusKey,
                PrincipalBalance, InterestBalance, FeesBalance, TotalBalance,
                AccruedInterest, DaysDelinquent, DelinquentAmount, Allowance,
                CreatedDate
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
        print(f"  ✓ Already have {existing_count} customer interactions")
        user_input = input(f"  Continue adding more interactions? (y/n): ")
        if user_input.lower() != 'y':
            return existing_count
    
    # Get all customers
    cursor.execute("SELECT CustomerKey FROM dim.DimCustomer WHERE IsCurrent = 1")
    customers = [row[0] for row in cursor.fetchall()]
    
    # Get interaction types
    cursor.execute("SELECT InteractionTypeKey, TypeName FROM dim.DimInteractionType")
    interaction_types = list(cursor.fetchall())
    
    # Get interaction channels
    cursor.execute("SELECT ChannelKey, ChannelName FROM dim.DimInteractionChannel")
    channels = list(cursor.fetchall())
    
    # Get customer loans for context
    cursor.execute("""
        SELECT CustomerKey, LoanKey 
        FROM fact.FACT_LOAN_ORIGINATION 
        WHERE IsActive = 1
    """)
    customer_loans = {}
    for customer_key, loan_key in cursor.fetchall():
        if customer_key not in customer_loans:
            customer_loans[customer_key] = []
        customer_loans[customer_key].append(loan_key)
    
    print(f"  Generating interactions for {len(customers)} customers...")
    
    batch = []
    total_inserted = 0
    interaction_id_counter = existing_count + 1
    
    start_date = datetime.date(2023, 1, 1)
    end_date = datetime.date(2024, 12, 31)
    
    for customer_key in customers:
        # Random number of interactions per customer (2-12 over 2 years)
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
            
            # Interaction type and channel
            type_key, type_name = random.choice(interaction_types)
            channel_key, channel_name = random.choice(channels)
            
            # Duration based on type and channel
            if type_name in ['Sales Call', 'Service Request', 'Collections Call']:
                duration = random.randint(5, 45)
            elif type_name in ['Compliance Check', 'Account Review']:
                duration = random.randint(30, 120)
            else:
                duration = random.randint(2, 10)
            
            # Outcome distribution
            outcomes = ['Resolved', 'Follow-up Required', 'Escalated', 'Information Provided']
            outcome_weights = [0.60, 0.25, 0.10, 0.05]
            outcome = weighted_choice(outcomes, outcome_weights)
            
            # Subject line based on interaction type
            subjects = {
                'Sales Call': ['New Loan Inquiry', 'Rate Information Request', 'Product Comparison'],
                'Service Request': ['Payment Question', 'Statement Request', 'Account Update'],
                'Collections Call': ['Past Due Balance', 'Payment Arrangement', 'Delinquency Notice'],
                'Compliance Check': ['Annual Review', 'KYC Update', 'Regulatory Compliance'],
                'Account Review': ['Credit Review', 'Loan Modification Request', 'Rate Review']
            }
            subject = random.choice(subjects.get(type_name, ['General Inquiry']))
            
            # Notes
            notes = f'{type_name} via {channel_name} - {outcome}'
            
            # Link to loan if customer has loans (70% of interactions)
            related_loan_key = None
            if customer_key in customer_loans and random.random() < 0.70:
                related_loan_key = random.choice(customer_loans[customer_key])
            
            # Related application (NULL for now, could link to applications)
            related_app_key = None
            
            # Follow-up required
            requires_followup = 1 if outcome == 'Follow-up Required' else 0
            followup_date_key = None
            if requires_followup:
                followup_date = interaction_date + timedelta(days=random.randint(3, 14))
                cursor.execute("SELECT TOP 1 DateKey FROM dim.DimDate WHERE [Date] >= ? ORDER BY [Date]", followup_date)
                result = cursor.fetchone()
                followup_date_key = result[0] if result else None
            
            now = datetime.datetime.now()
            
            batch.append((
                interaction_id, customer_key, interaction_date_key,
                type_key, channel_key,
                subject, notes, duration, outcome,
                related_loan_key, related_app_key,
                requires_followup, followup_date_key,
                now, now
            ))
            
            if len(batch) >= BATCH_SIZE:
                cursor.executemany("""
                    INSERT INTO fact.FACT_CUSTOMER_INTERACTION (
                        InteractionId, CustomerKey, InteractionDateKey,
                        InteractionTypeKey, InteractionChannelKey,
                        Subject, Notes, Duration_Minutes, Outcome,
                        RelatedLoanKey, RelatedApplicationKey,
                        RequiresFollowUp, FollowUpDateKey,
                        CreatedDate, ModifiedDate
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, batch)
                conn.commit()
                total_inserted += len(batch)
                print(f"  Inserted {total_inserted} interactions...")
                batch = []
    
    # Insert remaining batch
    if batch:
        cursor.executemany("""
            INSERT INTO fact.FACT_CUSTOMER_INTERACTION (
                InteractionId, CustomerKey, InteractionDateKey,
                InteractionTypeKey, InteractionChannelKey,
                Subject, Notes, Duration_Minutes, Outcome,
                RelatedLoanKey, RelatedApplicationKey,
                RequiresFollowUp, FollowUpDateKey,
                CreatedDate, ModifiedDate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, batch)
        conn.commit()
        total_inserted += len(batch)
    
    print(f"  ✓ Generated {total_inserted} customer interactions")
    return total_inserted

def main():
    print("=" * 70)
    print("TERADATA-FI Phase 2B: Balance Snapshots & Customer Interactions")
    print("=" * 70)
    print("\nThis script will generate:")
    print("  1. Monthly balance snapshots for all active loans")
    print("  2. Customer service interactions across multiple channels")
    print("\nEstimated time: 3-5 minutes")
    print("-" * 70)
    
    try:
        print("\nConnecting to database...")
        conn = get_connection()
        print("✓ Connected successfully!")
        
        # Generate data
        balance_count = generate_balances(conn)
        interaction_count = generate_interactions(conn)
        
        print("\n" + "=" * 70)
        print("✓ Phase 2B Complete!")
        print("=" * 70)
        print(f"  Balance Snapshots: {balance_count:,}")
        print(f"  Customer Interactions: {interaction_count:,}")
        print("\nData is ready for NL2SQL demo queries!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        print("\n  Traceback:")
        print("  " + str(traceback.format_exc()))
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
