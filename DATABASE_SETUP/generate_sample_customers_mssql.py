"""
Generate SQL INSERT statements for sample TERADATA-FI customers.
Creates realistic customer data for immediate database insertion via MSSQL MCP.
Target: 170 more customers to reach 250 total (currently at 80).
"""

import random

# Industry mapping from DimIndustry
INDUSTRIES = {
    'Manufacturing': {'SIC': '2000-3999', 'NAICS': '31-33'},
    'Healthcare': {'SIC': '8000-8099', 'NAICS': '62'},
    'Technology': {'SIC': '7370-7379', 'NAICS': '5112'},
    'Retail': {'SIC': '5200-5999', 'NAICS': '44-45'},
    'Real Estate': {'SIC': '6500-6599', 'NAICS': '5311'},
    'Professional Services': {'SIC': '8100-8999', 'NAICS': '5416'},
    'Construction': {'SIC': '1500-1799', 'NAICS': '2361'},
    'Transportation': {'SIC': '4000-4999', 'NAICS': '4841'},
    'Hospitality': {'SIC': '7000-7099', 'NAICS': '7211'},
    'Agriculture': {'SIC': '0100-0999', 'NAICS': '1111'}
}

# Risk rating distribution (mirrors actual commercial lending portfolios)
RISK_RATINGS = [
    ('AAA', 2), ('AA', 3), ('A', 15), ('BBB', 30), ('BB', 25),
    ('B', 15), ('CCC', 7), ('CC', 2), ('C', 1)
]

# Company suffixes
SUFFIXES = ['Corporation', 'Inc', 'LLC', 'Group', 'Industries', 'Enterprises', 
            'Holdings', 'Partners', 'Solutions', 'Services', 'Systems', 'Technologies']

# Company prefixes by industry
PREFIXES = {
    'Manufacturing': ['Precision', 'Advanced', 'Global', 'Industrial', 'Premier', 'Elite'],
    'Healthcare': ['Premier', 'Regional', 'Advanced', 'Integrated', 'Quality', 'Elite'],
    'Technology': ['Digital', 'Smart', 'Cloud', 'Cyber', 'Data', 'Tech'],
    'Retail': ['Metro', 'City', 'Premier', 'Quality', 'Value', 'Super'],
    'Real Estate': ['Metro', 'Urban', 'Prime', 'Capital', 'Investment', 'Premier'],
    'Professional Services': ['Strategic', 'Premier', 'Elite', 'Professional', 'Global', 'Expert'],
    'Construction': ['Premier', 'Modern', 'Quality', 'Professional', 'Advanced', 'Expert'],
    'Transportation': ['Express', 'Fast', 'Rapid', 'National', 'Interstate', 'Regional'],
    'Hospitality': ['Grand', 'Premier', 'Luxury', 'Boutique', 'Elite', 'Classic'],
    'Agriculture': ['Fresh', 'Green', 'Harvest', 'Prime', 'Valley', 'Country']
}

# Base names by industry
NAMES = {
    'Manufacturing': ['Manufacturing', 'Metalworks', 'Fabrication', 'Assembly', 'Production', 
                      'Components', 'Parts', 'Equipment', 'Tools', 'Machinery'],
    'Healthcare': ['Medical', 'Healthcare', 'Clinic', 'Hospital', 'Health Services', 
                   'Medical Center', 'Care Group', 'Health Systems', 'Medical Solutions'],
    'Technology': ['Software', 'Technologies', 'Systems', 'Solutions', 'Labs', 
                   'Analytics', 'Platform', 'Digital', 'Tech', 'Innovation'],
    'Retail': ['Stores', 'Retail', 'Shops', 'Market', 'Mart', 
               'Outlet', 'Commerce', 'Shopping', 'Goods', 'Trade'],
    'Real Estate': ['Properties', 'Realty', 'Real Estate', 'Development', 'Investments', 
                    'Holdings', 'Management', 'Ventures', 'Capital', 'Estates'],
    'Professional Services': ['Consulting', 'Advisors', 'Partners', 'Group', 'Associates', 
                              'Professionals', 'Experts', 'Counsel', 'Strategies', 'Solutions'],
    'Construction': ['Construction', 'Builders', 'Contractors', 'Building', 'Development', 
                     'Projects', 'Structures', 'Works', 'Construction Co', 'Build Group'],
    'Transportation': ['Logistics', 'Transport', 'Shipping', 'Freight', 'Delivery', 
                       'Transportation', 'Carriers', 'Fleet', 'Distribution', 'Express'],
    'Hospitality': ['Hotels', 'Resorts', 'Hospitality', 'Lodging', 'Inn', 
                    'Suites', 'Accommodations', 'Vacation', 'Stay', 'Retreat'],
    'Agriculture': ['Farms', 'Agriculture', 'Growers', 'Produce', 'Harvest', 
                    'Agribusiness', 'Farming', 'Ranch', 'Crops', 'Grains']
}

def generate_company_name(industry):
    """Generate realistic company name for given industry"""
    prefix = random.choice(PREFIXES[industry])
    base = random.choice(NAMES[industry])
    suffix = random.choice(SUFFIXES)
    return f"{prefix} {base} {suffix}"

def generate_customer_segment(annual_revenue):
    """Determine customer segment based on annual revenue"""
    if annual_revenue < 5000000:
        return 'Small Business'
    elif annual_revenue < 50000000:
        return 'Middle Market'
    else:
        return 'Large Corporate'

def generate_customer_tier(segment, is_vip):
    """Determine customer tier"""
    if is_vip:
        return 'Platinum'
    elif segment == 'Large Corporate':
        return random.choice(['Platinum', 'Gold', 'Gold'])
    elif segment == 'Middle Market':
        return random.choice(['Gold', 'Silver', 'Silver'])
    else:
        return random.choice(['Silver', 'Bronze', 'Bronze'])

def generate_employees(segment):
    """Generate realistic employee count based on segment"""
    if segment == 'Small Business':
        return random.randint(5, 99)
    elif segment == 'Middle Market':
        return random.randint(100, 999)
    else:
        return random.randint(1000, 10000)

def generate_annual_revenue(segment):
    """Generate realistic annual revenue based on segment"""
    if segment == 'Small Business':
        return random.randint(500000, 4999999)
    elif segment == 'Middle Market':
        return random.randint(5000000, 49999999)
    else:
        return random.randint(50000000, 500000000)

def generate_risk_rating():
    """Generate risk rating based on distribution"""
    total_weight = sum(weight for _, weight in RISK_RATINGS)
    r = random.randint(1, total_weight)
    cumulative = 0
    for rating, weight in RISK_RATINGS:
        cumulative += weight
        if r <= cumulative:
            return rating
    return 'BBB'

def generate_tax_id():
    """Generate fake 9-digit tax ID"""
    return ''.join([str(random.randint(0, 9)) for _ in range(9)])

def generate_batch_sql(start_id, batch_size, start_date_offset):
    """Generate SQL INSERT statements for a batch of customers"""
    
    sql_lines = []
    sql_lines.append("-- Auto-generated customer batch")
    
    # Get industry keys
    sql_lines.append("DECLARE @ManufKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Manufacturing');")
    sql_lines.append("DECLARE @HealthKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Healthcare');")
    sql_lines.append("DECLARE @TechKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Technology');")
    sql_lines.append("DECLARE @RetailKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Retail');")
    sql_lines.append("DECLARE @RealEstateKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Real Estate');")
    sql_lines.append("DECLARE @ProfServKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Professional Services');")
    sql_lines.append("DECLARE @ConstructionKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Construction');")
    sql_lines.append("DECLARE @TransportKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Transportation');")
    sql_lines.append("DECLARE @HospitalityKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Hospitality');")
    sql_lines.append("DECLARE @AgricultureKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Agriculture');")
    sql_lines.append("")
    
    sql_lines.append("INSERT INTO dim.DimCustomer (")
    sql_lines.append("    CustomerId, CompanyName, TaxId, LegalEntityType, YearFounded, EmployeeCount, AnnualRevenue,")
    sql_lines.append("    PrimaryIndustryId, PrimarySICCode, PrimaryNAICSCode, CreditRating_SP, InternalRiskRating,")
    sql_lines.append("    CustomerSegment, CustomerTier, TotalLoansCount, TotalLoanVolume, LifetimeRevenue, DefaultCount,")
    sql_lines.append("    IsActive, IsHighRisk, IsVIP, EffectiveDate, EndDate, IsCurrent, CreatedDate, ModifiedDate")
    sql_lines.append(")")
    sql_lines.append("VALUES")
    
    values = []
    for i in range(batch_size):
        cust_id = start_id + i
        industry = random.choice(list(INDUSTRIES.keys()))
        
        # Generate company details
        company_name = generate_company_name(industry)
        tax_id = generate_tax_id()
        legal_entity = random.choice(['Corporation', 'LLC', 'Corporation', 'LLC'])
        year_founded = random.randint(2005, 2020)
        
        # Determine segment first (to drive other attributes)
        segment_choice = random.randint(1, 100)
        if segment_choice <= 60:
            segment = 'Small Business'
        elif segment_choice <= 85:
            segment = 'Middle Market'
        else:
            segment = 'Large Corporate'
        
        # Generate metrics based on segment
        annual_revenue = generate_annual_revenue(segment)
        employees = generate_employees(segment)
        
        risk_rating = generate_risk_rating()
        
        # VIP status (top 10% of customers)
        is_vip = 1 if random.randint(1, 100) <= 10 else 0
        tier = generate_customer_tier(segment, is_vip)
        
        # High risk industries
        high_risk_industries = ['Construction', 'Hospitality', 'Agriculture']
        is_high_risk = 1 if industry in high_risk_industries or risk_rating in ['CCC', 'CC', 'C'] else 0
        
        # Loan portfolio metrics (realistic based on segment)
        if segment == 'Small Business':
            total_loans = random.randint(1, 3)
            total_volume = random.randint(500000, 5000000)
        elif segment == 'Middle Market':
            total_loans = random.randint(3, 8)
            total_volume = random.randint(5000000, 35000000)
        else:
            total_loans = random.randint(8, 18)
            total_volume = random.randint(35000000, 100000000)
        
        lifetime_revenue = int(total_volume * 0.05)  # 5% revenue margin
        default_count = 0  # All current customers in good standing
        
        # Industry key mapping
        industry_key_map = {
            'Manufacturing': '@ManufKey',
            'Healthcare': '@HealthKey',
            'Technology': '@TechKey',
            'Retail': '@RetailKey',
            'Real Estate': '@RealEstateKey',
            'Professional Services': '@ProfServKey',
            'Construction': '@ConstructionKey',
            'Transportation': '@TransportKey',
            'Hospitality': '@HospitalityKey',
            'Agriculture': '@AgricultureKey'
        }
        
        # SIC/NAICS codes
        sic_code = INDUSTRIES[industry]['SIC'].split('-')[0]
        naics_code = INDUSTRIES[industry]['NAICS']
        
        # Effective date (stagger across January 2024)
        day = min(28, start_date_offset + (i % 10))
        effective_date = f'2024-01-{day:02d}'
        
        # Build SQL value row
        value_row = f"('CUST{cust_id:05d}','{company_name}','{tax_id}','{legal_entity}',{year_founded},{employees},{annual_revenue},"
        value_row += f"{industry_key_map[industry]},'{sic_code}','{naics_code}','{risk_rating}','{risk_rating}',"
        value_row += f"'{segment}','{tier}',{total_loans},{total_volume},{lifetime_revenue},{default_count},"
        value_row += f"1,{is_high_risk},{is_vip},'{effective_date}',NULL,1,GETDATE(),GETDATE())"
        
        values.append(value_row)
    
    # Join all values with commas
    sql_lines.append(',\n'.join(values) + ';')
    sql_lines.append("")
    sql_lines.append(f"SELECT 'Batch completed: {start_id} to {start_id + batch_size - 1}' AS Status, COUNT(*) AS TotalCustomers FROM dim.DimCustomer;")
    
    return '\n'.join(sql_lines)

# Generate batches
print("=" * 80)
print("TERADATA-FI Sample Customer Generation")
print("=" * 80)
print()

# Generate 5 batches of 34 customers each = 170 customers (80 + 170 = 250 total)
for batch_num in range(1, 6):
    start_id = 80 + ((batch_num - 1) * 34) + 1
    batch_size = 34 if batch_num < 5 else 33  # Last batch has 33 to reach exactly 250
    start_date_offset = batch_num
    
    print(f"-- ============================================================================")
    print(f"-- Batch {batch_num}: Customers {start_id}-{start_id + batch_size - 1}")
    print(f"-- ============================================================================")
    print()
    print(generate_batch_sql(start_id, batch_size, start_date_offset))
    print()
