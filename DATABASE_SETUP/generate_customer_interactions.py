"""
TERADATA-FI: Customer Interactions Generation
Generates customer service interactions across multiple channels
"""

import pyodbc
import os
import random
import datetime
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(env_path)

# Configuration
BATCH_SIZE = 500
SERVER = os.getenv('AZURE_SQL_SERVER', 'aqsqlserver001.database.windows.net')
DATABASE = 'TERADATA-FI'
USERNAME = os.getenv('AZURE_SQL_USER')
PASSWORD = os.getenv('AZURE_SQL_PASSWORD')

def weighted_choice(choices, weights):
    """Select a random choice based on weights"""
    total = sum(weights)
    normalized = [w/total for w in weights]
    return random.choices(choices, weights=normalized)[0]

def get_connection():
    """Establish database connection"""
    conn_str = (
        f'DRIVER={{ODBC Driver 18 for SQL Server}};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        f'UID={USERNAME};'
        f'PWD={PASSWORD};'
        f'Encrypt=yes;TrustServerCertificate=no'
    )
    return pyodbc.connect(conn_str)

def generate_interactions(conn):
    """Generate customer service interactions"""
    print(f"\nGenerating customer interactions...")
    cursor = conn.cursor()
    
    # Check existing interactions
    cursor.execute("SELECT COUNT(*) FROM fact.FACT_CUSTOMER_INTERACTION")
    existing_count = cursor.fetchone()[0]
    
    if existing_count > 0:
        print(f"  ✓ Already have {existing_count} customer interactions")
        print(f"  This script will ADD MORE interactions to existing data")
        user_input = input(f"  Continue? (y/n): ")
        if user_input.lower() != 'y':
            return existing_count
    
    # Get all customers
    cursor.execute("SELECT CustomerKey FROM dim.DimCustomer WHERE IsCurrent = 1")
    customers = [row[0] for row in cursor.fetchall()]
    
    # Get interaction types
    cursor.execute("SELECT InteractionTypeKey, TypeName FROM dim.DimInteractionType")
    interaction_types = list(cursor.fetchall())
    
    # Get interaction channels (note: column is ChannelKey not InteractionChannelKey)
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
    
    # Get customer applications for context
    cursor.execute("""
        SELECT CustomerKey, ApplicationKey 
        FROM fact.FACT_LOAN_APPLICATION
    """)
    customer_apps = {}
    for customer_key, app_key in cursor.fetchall():
        if customer_key not in customer_apps:
            customer_apps[customer_key] = []
        customer_apps[customer_key].append(app_key)
    
    print(f"  Generating interactions for {len(customers)} customers...")
    print(f"  {len(interaction_types)} interaction types available")
    print(f"  {len(channels)} channels available")
    
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
                'Sales Call': ['New Loan Inquiry', 'Rate Information Request', 'Product Comparison', 'Pre-qualification Discussion'],
                'Service Request': ['Payment Question', 'Statement Request', 'Account Update', 'Balance Inquiry', 'Payment Method Change'],
                'Collections Call': ['Past Due Balance', 'Payment Arrangement', 'Delinquency Notice', 'Payment Reminder'],
                'Compliance Check': ['Annual Review', 'KYC Update', 'Regulatory Compliance', 'Document Verification'],
                'Account Review': ['Credit Review', 'Loan Modification Request', 'Rate Review', 'Renewal Discussion']
            }
            subject = random.choice(subjects.get(type_name, ['General Inquiry']))
            
            # Notes
            notes = f'{type_name} via {channel_name} - {outcome}. {subject}'
            
            # Link to loan if customer has loans (70% of interactions)
            related_loan_key = None
            if customer_key in customer_loans and random.random() < 0.70:
                related_loan_key = random.choice(customer_loans[customer_key])
            
            # Link to application (30% of interactions without loan)
            related_app_key = None
            if related_loan_key is None and customer_key in customer_apps and random.random() < 0.30:
                related_app_key = random.choice(customer_apps[customer_key])
            
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
    print("TERADATA-FI: Customer Interactions Generation")
    print("=" * 70)
    print("\nThis script will generate customer service interactions:")
    print("  - 2-12 interactions per customer (avg ~7)")
    print("  - Across 5 channels: Phone, Email, Meeting, Portal, Chat")
    print("  - 5 interaction types: Sales, Service, Collections, Compliance, Review")
    print("  - Realistic outcomes and follow-up patterns")
    print("\nEstimated records: ~7,800 interactions for 1,120 customers")
    print("Estimated time: 1-2 minutes")
    print("-" * 70)
    
    try:
        print("\nConnecting to database...")
        conn = get_connection()
        print("✓ Connected successfully!")
        
        # Generate interactions
        interaction_count = generate_interactions(conn)
        
        print("\n" + "=" * 70)
        print("✓ Customer Interactions Complete!")
        print("=" * 70)
        print(f"  Total Interactions: {interaction_count:,}")
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
