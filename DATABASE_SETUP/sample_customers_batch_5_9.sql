================================================================================
TERADATA-FI Sample Customer Generation
================================================================================

-- ============================================================================
-- Batch 1: Customers 81-114
-- ============================================================================

-- Auto-generated customer batch
DECLARE @ManufKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Manufacturing');
DECLARE @HealthKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Healthcare');
DECLARE @TechKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Technology');
DECLARE @RetailKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Retail');
DECLARE @RealEstateKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Real Estate');
DECLARE @ProfServKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Professional Services');
DECLARE @ConstructionKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Construction');
DECLARE @TransportKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Transportation');
DECLARE @HospitalityKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Hospitality');
DECLARE @AgricultureKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Agriculture');

INSERT INTO dim.DimCustomer (
    CustomerId, CompanyName, TaxId, LegalEntityType, YearFounded, EmployeeCount, AnnualRevenue,
    PrimaryIndustryId, PrimarySICCode, PrimaryNAICSCode, CreditRating_SP, InternalRiskRating,
    CustomerSegment, CustomerTier, TotalLoansCount, TotalLoanVolume, LifetimeRevenue, DefaultCount,
    IsActive, IsHighRisk, IsVIP, EffectiveDate, EndDate, IsCurrent, CreatedDate, ModifiedDate
)
VALUES
('CUST00081','Premier Experts Corporation','959875832','Corporation',2015,25,4320358,@ProfServKey,'8100','5416','A','A','Small Business','Bronze',3,4449888,222494,0,1,0,0,'2024-01-01',NULL,1,GETDATE(),GETDATE()),
('CUST00082','Investment Estates Inc','998753288','LLC',2012,2839,124710804,@RealEstateKey,'6500','5311','CCC','CCC','Large Corporate','Gold',10,62656158,3132807,0,1,1,0,'2024-01-02',NULL,1,GETDATE(),GETDATE()),
('CUST00083','Elite Parts Industries','025068235','LLC',2018,92,3655116,@ManufKey,'2000','31-33','BBB','BBB','Small Business','Bronze',3,1775919,88795,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00084','Precision Components Corporation','414236851','LLC',2020,43,2176637,@ManufKey,'2000','31-33','BB','BB','Small Business','Bronze',1,2057753,102887,0,1,0,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00085','Global Solutions Systems','778162589','LLC',2015,61,938501,@ProfServKey,'8100','5416','BB','BB','Small Business','Silver',1,1061591,53079,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00086','Rapid Express Group','073457974','Corporation',2015,420,34826101,@TransportKey,'4000','4841','BBB','BBB','Middle Market','Silver',7,8201687,410084,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00087','City Shops Inc','216023435','Corporation',2008,902,32895802,@RetailKey,'5200','44-45','BB','BB','Middle Market','Silver',8,8757144,437857,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00088','Premier Lodging Services','926477062','LLC',2018,31,2309528,@HospitalityKey,'7000','7211','A','A','Small Business','Bronze',2,4466268,223313,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00089','Global Production Partners','955121191','LLC',2019,928,26549138,@ManufKey,'2000','31-33','AAA','AAA','Middle Market','Gold',4,31392545,1569627,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00090','Cyber Digital Services','358029708','Corporation',2009,17,4536136,@TechKey,'7370','5112','BB','BB','Small Business','Bronze',3,4201978,210098,0,1,0,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00091','Premier Lodging Systems','192923498','Corporation',2017,36,533402,@HospitalityKey,'7000','7211','AA','AA','Small Business','Bronze',2,1636506,81825,0,1,1,0,'2024-01-01',NULL,1,GETDATE(),GETDATE()),
('CUST00092','Boutique Resorts Partners','138896395','LLC',2012,2304,403089519,@HospitalityKey,'7000','7211','BBB','BBB','Large Corporate','Gold',15,59249983,2962499,0,1,1,0,'2024-01-02',NULL,1,GETDATE(),GETDATE()),
('CUST00093','Country Agribusiness Group','086030135','Corporation',2009,9829,191432859,@AgricultureKey,'0100','1111','B','B','Large Corporate','Gold',10,98008021,4900401,0,1,1,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00094','Quality Hospital Industries','008736788','Corporation',2007,56,2785360,@HealthKey,'8000','62','A','A','Small Business','Bronze',2,2528906,126445,0,1,0,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00095','Advanced Health Systems Services','134527391','LLC',2012,413,42998372,@HealthKey,'8000','62','BBB','BBB','Middle Market','Silver',3,5809215,290460,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00096','Elite Medical Center Corporation','020888727','LLC',2006,55,2789706,@HealthKey,'8000','62','BBB','BBB','Small Business','Bronze',1,1527780,76389,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00097','Strategic Solutions Solutions','808912614','LLC',2006,594,31148174,@ProfServKey,'8100','5416','AA','AA','Middle Market','Gold',3,14663016,733150,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00098','Boutique Vacation Holdings','813517171','Corporation',2016,530,26450880,@HospitalityKey,'7000','7211','BBB','BBB','Middle Market','Silver',6,32251020,1612551,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00099','Professional Projects Enterprises','747145698','Corporation',2006,95,519807,@ConstructionKey,'1500','2361','BBB','BBB','Small Business','Silver',1,1141534,57076,0,1,1,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00100','Strategic Strategies Enterprises','363244163','Corporation',2018,40,2895834,@ProfServKey,'8100','5416','BBB','BBB','Small Business','Silver',3,3024894,151244,0,1,0,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00101','Digital Digital Solutions','006937915','Corporation',2011,25,4528418,@TechKey,'7370','5112','B','B','Small Business','Silver',1,1576347,78817,0,1,0,0,'2024-01-01',NULL,1,GETDATE(),GETDATE()),
('CUST00102','Boutique Vacation Holdings','316385251','LLC',2018,6,3703905,@HospitalityKey,'7000','7211','BB','BB','Small Business','Silver',3,3726954,186347,0,1,1,0,'2024-01-02',NULL,1,GETDATE(),GETDATE()),
('CUST00103','Smart Analytics Partners','194068535','Corporation',2016,9272,345249788,@TechKey,'7370','5112','B','B','Large Corporate','Gold',9,62377802,3118890,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00104','Harvest Agribusiness Group','205093622','LLC',2011,23,2099625,@AgricultureKey,'0100','1111','BBB','BBB','Small Business','Bronze',3,1827668,91383,0,1,1,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00105','Fast Carriers Industries','593105407','LLC',2012,5304,111265801,@TransportKey,'4000','4841','B','B','Large Corporate','Platinum',8,71649137,3582456,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00106','Expert Builders Enterprises','996103261','Corporation',2014,2588,324924877,@ConstructionKey,'1500','2361','A','A','Large Corporate','Platinum',8,66619314,3330965,0,1,1,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00107','Boutique Lodging Partners','915114342','LLC',2009,65,2842607,@HospitalityKey,'7000','7211','B','B','Small Business','Platinum',3,1708192,85409,0,1,1,1,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00108','Quality Builders Corporation','181112134','Corporation',2006,95,2591541,@ConstructionKey,'1500','2361','BB','BB','Small Business','Bronze',3,2912308,145615,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00109','Global Production Solutions','317990595','LLC',2010,5011,336313278,@ManufKey,'2000','31-33','B','B','Large Corporate','Gold',13,62249448,3112472,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00110','Rapid Logistics Partners','943208576','LLC',2011,7,1782554,@TransportKey,'4000','4841','BB','BB','Small Business','Bronze',1,2951375,147568,0,1,0,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00111','Advanced Healthcare Enterprises','925238488','Corporation',2009,93,3935866,@HealthKey,'8000','62','BBB','BBB','Small Business','Bronze',1,4299697,214984,0,1,0,0,'2024-01-01',NULL,1,GETDATE(),GETDATE()),
('CUST00112','Rapid Distribution LLC','323771050','Corporation',2008,654,7496366,@TransportKey,'4000','4841','BB','BB','Middle Market','Platinum',3,6838448,341922,0,1,0,1,'2024-01-02',NULL,1,GETDATE(),GETDATE()),
('CUST00113','Fast Logistics Industries','606465969','LLC',2009,39,3250096,@TransportKey,'4000','4841','BBB','BBB','Small Business','Bronze',1,4359558,217977,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00114','Harvest Ranch Enterprises','381037317','Corporation',2010,437,13670064,@AgricultureKey,'0100','1111','BB','BB','Middle Market','Silver',8,13014325,650716,0,1,1,0,'2024-01-04',NULL,1,GETDATE(),GETDATE());

SELECT 'Batch completed: 81 to 114' AS Status, COUNT(*) AS TotalCustomers FROM dim.DimCustomer;

-- ============================================================================
-- Batch 2: Customers 115-148
-- ============================================================================

-- Auto-generated customer batch
DECLARE @ManufKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Manufacturing');
DECLARE @HealthKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Healthcare');
DECLARE @TechKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Technology');
DECLARE @RetailKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Retail');
DECLARE @RealEstateKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Real Estate');
DECLARE @ProfServKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Professional Services');
DECLARE @ConstructionKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Construction');
DECLARE @TransportKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Transportation');
DECLARE @HospitalityKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Hospitality');
DECLARE @AgricultureKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Agriculture');

INSERT INTO dim.DimCustomer (
    CustomerId, CompanyName, TaxId, LegalEntityType, YearFounded, EmployeeCount, AnnualRevenue,
    PrimaryIndustryId, PrimarySICCode, PrimaryNAICSCode, CreditRating_SP, InternalRiskRating,
    CustomerSegment, CustomerTier, TotalLoansCount, TotalLoanVolume, LifetimeRevenue, DefaultCount,
    IsActive, IsHighRisk, IsVIP, EffectiveDate, EndDate, IsCurrent, CreatedDate, ModifiedDate
)
VALUES
('CUST00115','Expert Solutions LLC','385216921','Corporation',2018,99,2272614,@ProfServKey,'8100','5416','BB','BB','Small Business','Bronze',2,2059997,102999,0,1,0,0,'2024-01-02',NULL,1,GETDATE(),GETDATE()),
('CUST00116','Elite Medical Center Services','809312875','LLC',2017,62,4564444,@HealthKey,'8000','62','B','B','Small Business','Silver',1,4298446,214922,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00117','Quality Hospital Enterprises','759162273','LLC',2020,73,3063124,@HealthKey,'8000','62','CCC','CCC','Small Business','Bronze',3,4986806,249340,0,1,1,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00118','Super Mart Partners','806342664','Corporation',2016,294,8454350,@RetailKey,'5200','44-45','BB','BB','Middle Market','Gold',5,28489069,1424453,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00119','Industrial Fabrication Systems','306776473','Corporation',2015,338,39993949,@ManufKey,'2000','31-33','BBB','BBB','Middle Market','Gold',4,7419987,370999,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00120','Professional Group Holdings','837156388','Corporation',2010,71,4352211,@ProfServKey,'8100','5416','CCC','CCC','Small Business','Bronze',3,3552248,177612,0,1,1,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00121','Integrated Medical Solutions Industries','815959243','LLC',2015,73,1585851,@HealthKey,'8000','62','BBB','BBB','Small Business','Bronze',2,754560,37728,0,1,0,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00122','Boutique Lodging Technologies','187325551','Corporation',2011,16,2987219,@HospitalityKey,'7000','7211','A','A','Small Business','Bronze',1,1071962,53598,0,1,1,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00123','Advanced Manufacturing Inc','816929542','LLC',2015,33,1500593,@ManufKey,'2000','31-33','BB','BB','Small Business','Silver',2,537885,26894,0,1,0,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00124','Premier Healthcare Inc','861780688','LLC',2005,90,642116,@HealthKey,'8000','62','BBB','BBB','Small Business','Bronze',2,1400976,70048,0,1,0,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00125','Premier Partners Corporation','843126647','LLC',2012,8,3252540,@ProfServKey,'8100','5416','BB','BB','Small Business','Silver',3,1349315,67465,0,1,0,0,'2024-01-02',NULL,1,GETDATE(),GETDATE()),
('CUST00126','Premier Building Industries','212481893','LLC',2009,4588,95904594,@ConstructionKey,'1500','2361','BBB','BBB','Large Corporate','Gold',17,90315378,4515768,0,1,1,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00127','Smart Analytics Services','817400024','LLC',2010,63,1880389,@TechKey,'7370','5112','B','B','Small Business','Platinum',2,4974443,248722,0,1,0,1,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00128','National Transport Systems','155402857','Corporation',2015,29,3617594,@TransportKey,'4000','4841','BBB','BBB','Small Business','Silver',1,2095159,104757,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00129','Premier Goods Partners','426387812','LLC',2013,433,36813250,@RetailKey,'5200','44-45','B','B','Middle Market','Silver',6,25798626,1289931,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00130','Prime Agriculture Corporation','812201655','LLC',2006,70,2166914,@AgricultureKey,'0100','1111','BB','BB','Small Business','Bronze',1,4711737,235586,0,1,1,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00131','Country Harvest Enterprises','006060466','LLC',2018,380,42187949,@AgricultureKey,'0100','1111','BBB','BBB','Middle Market','Silver',6,11715003,585750,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00132','Interstate Fleet Group','940618563','Corporation',2014,949,23776110,@TransportKey,'4000','4841','B','B','Middle Market','Gold',8,30221483,1511074,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00133','Integrated Clinic Group','806714389','Corporation',2018,43,2513196,@HealthKey,'8000','62','BBB','BBB','Small Business','Silver',2,3200522,160026,0,1,0,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00134','Premier Suites Technologies','146082564','LLC',2014,7083,68218680,@HospitalityKey,'7000','7211','B','B','Large Corporate','Gold',10,54150259,2707512,0,1,1,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00135','Premier Tools LLC','504294917','Corporation',2013,98,2093698,@ManufKey,'2000','31-33','BBB','BBB','Small Business','Bronze',3,2364157,118207,0,1,0,0,'2024-01-02',NULL,1,GETDATE(),GETDATE()),
('CUST00136','Global Components LLC','751327742','Corporation',2005,8676,81768681,@ManufKey,'2000','31-33','A','A','Large Corporate','Platinum',17,97478010,4873900,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00137','Advanced Structures Systems','209002407','LLC',2015,95,3943931,@ConstructionKey,'1500','2361','BBB','BBB','Small Business','Silver',2,1428128,71406,0,1,1,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00138','Premier Commerce Solutions','777141354','LLC',2018,496,27032114,@RetailKey,'5200','44-45','BBB','BBB','Middle Market','Platinum',5,8489105,424455,0,1,0,1,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00139','City Mart Holdings','655317309','Corporation',2005,4327,101080275,@RetailKey,'5200','44-45','BBB','BBB','Large Corporate','Gold',18,63225918,3161295,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00140','Tech Solutions Industries','457527225','Corporation',2006,40,3030715,@TechKey,'7370','5112','A','A','Small Business','Bronze',2,876018,43800,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00141','Prime Produce Solutions','444471962','Corporation',2006,94,3391889,@AgricultureKey,'0100','1111','B','B','Small Business','Bronze',2,871603,43580,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00142','Prime Development Technologies','047867874','LLC',2018,46,798346,@RealEstateKey,'6500','5311','B','B','Small Business','Silver',3,865470,43273,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00143','Premier Medical Center Inc','338157173','LLC',2007,29,4424526,@HealthKey,'8000','62','BB','BB','Small Business','Bronze',2,759204,37960,0,1,0,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00144','Premier Medical Center Solutions','072643435','LLC',2013,53,2039759,@HealthKey,'8000','62','A','A','Small Business','Silver',2,3468121,173406,0,1,0,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00145','Premier Hotels Corporation','055576169','Corporation',2014,79,3861792,@HospitalityKey,'7000','7211','BB','BB','Small Business','Silver',2,3800955,190047,0,1,1,0,'2024-01-02',NULL,1,GETDATE(),GETDATE()),
('CUST00146','Quality Health Services Group','489983595','LLC',2014,56,1359627,@HealthKey,'8000','62','BB','BB','Small Business','Bronze',1,2652216,132610,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00147','Advanced Health Systems Systems','629296602','LLC',2016,530,48845970,@HealthKey,'8000','62','CC','CC','Middle Market','Gold',8,17231183,861559,0,1,1,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00148','Tech Systems Holdings','549180889','LLC',2017,79,3557955,@TechKey,'7370','5112','B','B','Small Business','Bronze',3,3532133,176606,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE());

SELECT 'Batch completed: 115 to 148' AS Status, COUNT(*) AS TotalCustomers FROM dim.DimCustomer;

-- ============================================================================
-- Batch 3: Customers 149-182
-- ============================================================================

-- Auto-generated customer batch
DECLARE @ManufKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Manufacturing');
DECLARE @HealthKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Healthcare');
DECLARE @TechKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Technology');
DECLARE @RetailKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Retail');
DECLARE @RealEstateKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Real Estate');
DECLARE @ProfServKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Professional Services');
DECLARE @ConstructionKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Construction');
DECLARE @TransportKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Transportation');
DECLARE @HospitalityKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Hospitality');
DECLARE @AgricultureKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Agriculture');

INSERT INTO dim.DimCustomer (
    CustomerId, CompanyName, TaxId, LegalEntityType, YearFounded, EmployeeCount, AnnualRevenue,
    PrimaryIndustryId, PrimarySICCode, PrimaryNAICSCode, CreditRating_SP, InternalRiskRating,
    CustomerSegment, CustomerTier, TotalLoansCount, TotalLoanVolume, LifetimeRevenue, DefaultCount,
    IsActive, IsHighRisk, IsVIP, EffectiveDate, EndDate, IsCurrent, CreatedDate, ModifiedDate
)
VALUES
('CUST00149','Rapid Logistics LLC','646914219','LLC',2013,18,1853768,@TransportKey,'4000','4841','BBB','BBB','Small Business','Bronze',1,1309585,65479,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00150','Quality Clinic Services','920549810','LLC',2006,24,506342,@HealthKey,'8000','62','BB','BB','Small Business','Silver',2,3346385,167319,0,1,0,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00151','Valley Agriculture Enterprises','789146949','LLC',2020,834,49381757,@AgricultureKey,'0100','1111','BBB','BBB','Middle Market','Gold',4,6956032,347801,0,1,1,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00152','Country Agriculture Services','674724226','LLC',2013,882,37157718,@AgricultureKey,'0100','1111','BBB','BBB','Middle Market','Silver',3,9844165,492208,0,1,1,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00153','Premier Medical Solutions LLC','480090912','Corporation',2012,710,20175358,@HealthKey,'8000','62','B','B','Middle Market','Silver',4,11551043,577552,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00154','Advanced Fabrication Inc','109478750','Corporation',2009,638,47350447,@ManufKey,'2000','31-33','B','B','Middle Market','Silver',8,29409935,1470496,0,1,0,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00155','Country Agriculture Inc','093710252','LLC',2007,95,4212296,@AgricultureKey,'0100','1111','BBB','BBB','Small Business','Bronze',2,4865920,243296,0,1,1,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00156','Elite Inn Inc','716030450','Corporation',2016,38,2206433,@HospitalityKey,'7000','7211','A','A','Small Business','Bronze',3,4343211,217160,0,1,1,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00157','Premier Partners Holdings','196272446','LLC',2011,605,33756477,@ProfServKey,'8100','5416','BBB','BBB','Middle Market','Gold',3,17651254,882562,0,1,0,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00158','Quality Goods Corporation','164527372','Corporation',2010,52,4235083,@RetailKey,'5200','44-45','BBB','BBB','Small Business','Bronze',2,3171616,158580,0,1,0,0,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00159','City Retail Enterprises','079864094','LLC',2005,879,7640258,@RetailKey,'5200','44-45','B','B','Middle Market','Gold',6,30958346,1547917,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00160','Cloud Analytics Services','364469668','LLC',2017,9439,361639373,@TechKey,'7370','5112','BBB','BBB','Large Corporate','Platinum',14,69452759,3472637,0,1,0,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00161','City Shops Services','691443548','Corporation',2017,5746,179560016,@RetailKey,'5200','44-45','BB','BB','Large Corporate','Gold',9,85562315,4278115,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00162','Interstate Fleet Solutions','207727637','Corporation',2018,91,1276576,@TransportKey,'4000','4841','BB','BB','Small Business','Silver',1,4849025,242451,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00163','Rapid Carriers Industries','954735287','LLC',2012,25,2108555,@TransportKey,'4000','4841','A','A','Small Business','Silver',1,3774001,188700,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00164','Expert Building LLC','655615675','Corporation',2009,384,5255084,@ConstructionKey,'1500','2361','BB','BB','Middle Market','Silver',3,28494161,1424708,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00165','Express Freight Technologies','020829990','LLC',2006,92,1458433,@TransportKey,'4000','4841','BBB','BBB','Small Business','Silver',3,3842393,192119,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00166','Quality Shops Holdings','053085960','LLC',2008,179,41123927,@RetailKey,'5200','44-45','BBB','BBB','Middle Market','Silver',7,9446063,472303,0,1,0,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00167','Prime Ventures Enterprises','701582718','LLC',2019,80,3075384,@RealEstateKey,'6500','5311','BB','BB','Small Business','Platinum',3,1793925,89696,0,1,0,1,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00168','Premier Retreat Group','998768623','LLC',2019,88,2201694,@HospitalityKey,'7000','7211','A','A','Small Business','Bronze',1,1400919,70045,0,1,1,0,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00169','Precision Machinery Holdings','062314640','Corporation',2019,306,37153629,@ManufKey,'2000','31-33','B','B','Middle Market','Silver',6,7917770,395888,0,1,0,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00170','Fresh Agriculture Systems','874196855','LLC',2014,44,4102925,@AgricultureKey,'0100','1111','BBB','BBB','Small Business','Bronze',3,4192453,209622,0,1,1,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00171','Industrial Components Solutions','526359305','LLC',2011,232,44234547,@ManufKey,'2000','31-33','CCC','CCC','Middle Market','Silver',3,24840575,1242028,0,1,1,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00172','Grand Accommodations Systems','627939016','Corporation',2014,563,23539686,@HospitalityKey,'7000','7211','BBB','BBB','Middle Market','Silver',8,18580319,929015,0,1,1,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00173','Valley Agribusiness Partners','423961046','Corporation',2016,9146,137657312,@AgricultureKey,'0100','1111','B','B','Large Corporate','Platinum',8,98732456,4936622,0,1,1,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00174','Green Agribusiness Partners','104449830','LLC',2005,12,2217699,@AgricultureKey,'0100','1111','AA','AA','Small Business','Silver',3,832196,41609,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00175','Fresh Produce Inc','914371311','LLC',2018,99,1756502,@AgricultureKey,'0100','1111','BBB','BBB','Small Business','Bronze',1,3864853,193242,0,1,1,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00176','Fast Distribution Inc','019478706','Corporation',2013,4422,249839185,@TransportKey,'4000','4841','BBB','BBB','Large Corporate','Platinum',18,82523771,4126188,0,1,0,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00177','Advanced Clinic Solutions','046327974','LLC',2007,46,3445121,@HealthKey,'8000','62','BBB','BBB','Small Business','Bronze',2,4736369,236818,0,1,0,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00178','Elite Health Services Technologies','646234638','LLC',2019,2940,381661730,@HealthKey,'8000','62','B','B','Large Corporate','Platinum',14,35569214,1778460,0,1,0,0,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00179','Premier Hotels Technologies','629544522','Corporation',2009,9371,407279462,@HospitalityKey,'7000','7211','BB','BB','Large Corporate','Platinum',10,37044869,1852243,0,1,1,0,'2024-01-03',NULL,1,GETDATE(),GETDATE()),
('CUST00180','Elite Medical Solutions Corporation','384541154','LLC',2014,49,4582845,@HealthKey,'8000','62','A','A','Small Business','Silver',3,4210273,210513,0,1,0,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00181','Interstate Shipping Inc','924315252','Corporation',2019,475,47829842,@TransportKey,'4000','4841','B','B','Middle Market','Silver',6,9902911,495145,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00182','Premier Building Partners','902570481','Corporation',2016,87,2008438,@ConstructionKey,'1500','2361','A','A','Small Business','Silver',1,3377820,168891,0,1,1,0,'2024-01-06',NULL,1,GETDATE(),GETDATE());

SELECT 'Batch completed: 149 to 182' AS Status, COUNT(*) AS TotalCustomers FROM dim.DimCustomer;

-- ============================================================================
-- Batch 4: Customers 183-216
-- ============================================================================

-- Auto-generated customer batch
DECLARE @ManufKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Manufacturing');
DECLARE @HealthKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Healthcare');
DECLARE @TechKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Technology');
DECLARE @RetailKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Retail');
DECLARE @RealEstateKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Real Estate');
DECLARE @ProfServKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Professional Services');
DECLARE @ConstructionKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Construction');
DECLARE @TransportKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Transportation');
DECLARE @HospitalityKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Hospitality');
DECLARE @AgricultureKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Agriculture');

INSERT INTO dim.DimCustomer (
    CustomerId, CompanyName, TaxId, LegalEntityType, YearFounded, EmployeeCount, AnnualRevenue,
    PrimaryIndustryId, PrimarySICCode, PrimaryNAICSCode, CreditRating_SP, InternalRiskRating,
    CustomerSegment, CustomerTier, TotalLoansCount, TotalLoanVolume, LifetimeRevenue, DefaultCount,
    IsActive, IsHighRisk, IsVIP, EffectiveDate, EndDate, IsCurrent, CreatedDate, ModifiedDate
)
VALUES
('CUST00183','Premier Partners Industries','353291450','LLC',2018,6533,310852236,@ProfServKey,'8100','5416','BB','BB','Large Corporate','Gold',10,74342554,3717127,0,1,0,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00184','Premier Strategies Holdings','691888373','LLC',2013,18,3581111,@ProfServKey,'8100','5416','A','A','Small Business','Bronze',1,1331467,66573,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00185','Advanced Projects Group','124296035','LLC',2006,75,909254,@ConstructionKey,'1500','2361','BB','BB','Small Business','Bronze',3,2138968,106948,0,1,1,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00186','Prime Investments Holdings','185473988','Corporation',2013,5560,116659132,@RealEstateKey,'6500','5311','BB','BB','Large Corporate','Gold',17,54436738,2721836,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00187','Cyber Analytics Partners','282624463','LLC',2010,69,1279392,@TechKey,'7370','5112','B','B','Small Business','Silver',3,1554666,77733,0,1,0,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00188','Classic Stay LLC','398395873','Corporation',2005,43,1805044,@HospitalityKey,'7000','7211','BBB','BBB','Small Business','Silver',2,1627009,81350,0,1,1,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00189','Cyber Systems LLC','654646619','LLC',2020,74,892056,@TechKey,'7370','5112','CCC','CCC','Small Business','Silver',2,3015043,150752,0,1,1,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00190','Green Agribusiness Inc','451934465','LLC',2009,672,5595825,@AgricultureKey,'0100','1111','AA','AA','Middle Market','Silver',5,20477949,1023897,0,1,1,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00191','National Delivery Technologies','427205309','Corporation',2017,35,4436386,@TransportKey,'4000','4841','A','A','Small Business','Bronze',2,4284137,214206,0,1,0,0,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00192','Premier Shopping Inc','854770076','LLC',2016,4924,220567383,@RetailKey,'5200','44-45','BB','BB','Large Corporate','Gold',8,49869340,2493467,0,1,0,0,'2024-01-13',NULL,1,GETDATE(),GETDATE()),
('CUST00193','Quality Development Corporation','266306810','LLC',2005,74,4861806,@ConstructionKey,'1500','2361','BB','BB','Small Business','Silver',2,2419002,120950,0,1,1,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00194','Country Agriculture Services','083619148','LLC',2019,34,4476779,@AgricultureKey,'0100','1111','BBB','BBB','Small Business','Silver',1,1832143,91607,0,1,1,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00195','Country Farming Group','168672739','Corporation',2013,7,609954,@AgricultureKey,'0100','1111','BB','BB','Small Business','Bronze',1,4081153,204057,0,1,1,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00196','Premier Management Technologies','102556051','Corporation',2014,682,34222875,@RealEstateKey,'6500','5311','BBB','BBB','Middle Market','Gold',7,32732812,1636640,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00197','Data Labs Solutions','543325020','LLC',2019,9629,211508640,@TechKey,'7370','5112','BB','BB','Large Corporate','Gold',12,51921444,2596072,0,1,0,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00198','Regional Health Systems Systems','743936926','LLC',2008,76,3582265,@HealthKey,'8000','62','A','A','Small Business','Bronze',3,1734286,86714,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00199','Regional Medical Group','731799717','LLC',2005,70,4410460,@HealthKey,'8000','62','CCC','CCC','Small Business','Silver',2,4740201,237010,0,1,1,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00200','Professional Consulting Corporation','259200998','LLC',2011,639,17903355,@ProfServKey,'8100','5416','AA','AA','Middle Market','Silver',8,21788944,1089447,0,1,0,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00201','Global Associates Systems','680295142','LLC',2011,5272,383570076,@ProfServKey,'8100','5416','B','B','Large Corporate','Platinum',16,61673445,3083672,0,1,0,0,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00202','Express Logistics Inc','979826208','LLC',2018,18,4148008,@TransportKey,'4000','4841','BB','BB','Small Business','Bronze',3,3357124,167856,0,1,0,0,'2024-01-13',NULL,1,GETDATE(),GETDATE()),
('CUST00203','Metro Holdings Systems','719401724','LLC',2017,359,7912355,@RealEstateKey,'6500','5311','BB','BB','Middle Market','Silver',3,16618118,830905,0,1,0,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00204','Boutique Vacation Technologies','945202880','LLC',2020,433,42016026,@HospitalityKey,'7000','7211','BBB','BBB','Middle Market','Silver',6,16973185,848659,0,1,1,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00205','Cloud Platform Industries','932420199','LLC',2017,707,30443321,@TechKey,'7370','5112','A','A','Middle Market','Silver',8,27284986,1364249,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00206','Grand Accommodations Solutions','120554064','LLC',2005,9355,208961974,@HospitalityKey,'7000','7211','B','B','Large Corporate','Platinum',14,63787595,3189379,0,1,1,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00207','Fresh Farms Services','745323242','Corporation',2018,8800,423635638,@AgricultureKey,'0100','1111','BBB','BBB','Large Corporate','Platinum',11,89596662,4479833,0,1,1,1,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00208','Advanced Medical Solutions LLC','838154189','LLC',2013,5433,417430739,@HealthKey,'8000','62','BB','BB','Large Corporate','Platinum',12,47545456,2377272,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00209','Elite Hospital Industries','326163091','Corporation',2009,26,1531018,@HealthKey,'8000','62','CCC','CCC','Small Business','Bronze',2,3820678,191033,0,1,1,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00210','Valley Farms Inc','235122172','Corporation',2011,72,3293748,@AgricultureKey,'0100','1111','AA','AA','Small Business','Silver',1,4366622,218331,0,1,1,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00211','Metro Mart Systems','492044854','Corporation',2011,90,3163683,@RetailKey,'5200','44-45','AA','AA','Small Business','Platinum',1,3917257,195862,0,1,0,1,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00212','Strategic Experts Enterprises','514690534','LLC',2014,525,44235942,@ProfServKey,'8100','5416','BB','BB','Middle Market','Gold',6,22983673,1149183,0,1,0,0,'2024-01-13',NULL,1,GETDATE(),GETDATE()),
('CUST00213','Cloud Systems Technologies','908800405','Corporation',2020,76,4104736,@TechKey,'7370','5112','B','B','Small Business','Bronze',3,4723542,236177,0,1,0,0,'2024-01-04',NULL,1,GETDATE(),GETDATE()),
('CUST00214','Strategic Consulting Industries','401821564','LLC',2009,71,4355510,@ProfServKey,'8100','5416','BB','BB','Small Business','Bronze',1,3423997,171199,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00215','Premier Medical Inc','125433292','Corporation',2012,90,3271851,@HealthKey,'8000','62','B','B','Small Business','Silver',1,4989927,249496,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00216','Cyber Innovation Corporation','885491302','LLC',2014,75,2911521,@TechKey,'7370','5112','BBB','BBB','Small Business','Bronze',1,941939,47096,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE());

SELECT 'Batch completed: 183 to 216' AS Status, COUNT(*) AS TotalCustomers FROM dim.DimCustomer;

-- ============================================================================
-- Batch 5: Customers 217-249
-- ============================================================================

-- Auto-generated customer batch
DECLARE @ManufKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Manufacturing');
DECLARE @HealthKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Healthcare');
DECLARE @TechKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Technology');
DECLARE @RetailKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Retail');
DECLARE @RealEstateKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Real Estate');
DECLARE @ProfServKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Professional Services');
DECLARE @ConstructionKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Construction');
DECLARE @TransportKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Transportation');
DECLARE @HospitalityKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Hospitality');
DECLARE @AgricultureKey INT = (SELECT IndustryKey FROM dim.DimIndustry WHERE IndustryName = 'Agriculture');

INSERT INTO dim.DimCustomer (
    CustomerId, CompanyName, TaxId, LegalEntityType, YearFounded, EmployeeCount, AnnualRevenue,
    PrimaryIndustryId, PrimarySICCode, PrimaryNAICSCode, CreditRating_SP, InternalRiskRating,
    CustomerSegment, CustomerTier, TotalLoansCount, TotalLoanVolume, LifetimeRevenue, DefaultCount,
    IsActive, IsHighRisk, IsVIP, EffectiveDate, EndDate, IsCurrent, CreatedDate, ModifiedDate
)
VALUES
('CUST00217','Digital Systems Corporation','911184275','Corporation',2018,80,1203368,@TechKey,'7370','5112','BBB','BBB','Small Business','Bronze',1,2474848,123742,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00218','Global Partners Holdings','091330436','Corporation',2019,6150,212252124,@ProfServKey,'8100','5416','AA','AA','Large Corporate','Platinum',13,64393320,3219666,0,1,0,1,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00219','Tech Platform Group','260708391','Corporation',2012,8774,453357089,@TechKey,'7370','5112','B','B','Large Corporate','Gold',13,95074841,4753742,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00220','Quality Mart Holdings','209182896','LLC',2016,68,1104649,@RetailKey,'5200','44-45','CCC','CCC','Small Business','Bronze',3,3794279,189713,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00221','Advanced Healthcare Enterprises','730459647','LLC',2019,85,4567974,@HealthKey,'8000','62','BB','BB','Small Business','Bronze',3,3653904,182695,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00222','Super Shops Enterprises','445070214','Corporation',2020,514,31771000,@RetailKey,'5200','44-45','C','C','Middle Market','Silver',8,30189301,1509465,0,1,1,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00223','Value Commerce Systems','915330203','Corporation',2018,20,2529737,@RetailKey,'5200','44-45','A','A','Small Business','Bronze',3,1555816,77790,0,1,0,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00224','Country Produce Inc','941356926','LLC',2009,483,10313974,@AgricultureKey,'0100','1111','B','B','Middle Market','Gold',8,5610756,280537,0,1,1,0,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00225','Harvest Agribusiness Holdings','993265636','LLC',2010,73,2162681,@AgricultureKey,'0100','1111','BB','BB','Small Business','Bronze',3,2070370,103518,0,1,1,0,'2024-01-13',NULL,1,GETDATE(),GETDATE()),
('CUST00226','Elite Consulting LLC','555400053','Corporation',2012,50,3900228,@ProfServKey,'8100','5416','BB','BB','Small Business','Bronze',1,2691764,134588,0,1,0,0,'2024-01-14',NULL,1,GETDATE(),GETDATE()),
('CUST00227','Industrial Parts Holdings','741906146','Corporation',2017,90,3116125,@ManufKey,'2000','31-33','BBB','BBB','Small Business','Bronze',1,2541486,127074,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00228','Harvest Farms Technologies','581356140','Corporation',2007,17,1530925,@AgricultureKey,'0100','1111','BBB','BBB','Small Business','Silver',2,4229016,211450,0,1,1,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00229','Global Manufacturing Industries','451534849','Corporation',2013,38,2646211,@ManufKey,'2000','31-33','BB','BB','Small Business','Bronze',3,653895,32694,0,1,0,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00230','Regional Healthcare Solutions','197304494','Corporation',2019,9129,470372392,@HealthKey,'8000','62','CCC','CCC','Large Corporate','Gold',18,39808282,1990414,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00231','Industrial Tools Solutions','675412789','Corporation',2010,38,4258627,@ManufKey,'2000','31-33','B','B','Small Business','Bronze',3,862319,43115,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00232','Premier Capital Holdings','653271118','LLC',2008,68,4749563,@RealEstateKey,'6500','5311','CCC','CCC','Small Business','Platinum',2,3513526,175676,0,1,1,1,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00233','Advanced Medical Solutions Services','310121967','LLC',2020,62,1505860,@HealthKey,'8000','62','BB','BB','Small Business','Bronze',2,1190518,59525,0,1,0,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00234','Regional Transport Enterprises','548721064','Corporation',2009,39,4408420,@TransportKey,'4000','4841','CCC','CCC','Small Business','Bronze',1,4522099,226104,0,1,1,0,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00235','Data Analytics Solutions','295162497','LLC',2012,2369,186596812,@TechKey,'7370','5112','BBB','BBB','Large Corporate','Gold',12,38125806,1906290,0,1,0,0,'2024-01-13',NULL,1,GETDATE(),GETDATE()),
('CUST00236','Cyber Labs Holdings','601514220','LLC',2012,75,4654264,@TechKey,'7370','5112','AA','AA','Small Business','Platinum',1,2682398,134119,0,1,0,1,'2024-01-14',NULL,1,GETDATE(),GETDATE()),
('CUST00237','City Mart Technologies','206164810','Corporation',2005,374,25218025,@RetailKey,'5200','44-45','A','A','Middle Market','Gold',3,24674889,1233744,0,1,0,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00238','Advanced Health Systems Group','691952686','LLC',2009,53,3427546,@HealthKey,'8000','62','BB','BB','Small Business','Platinum',1,3665552,183277,0,1,0,1,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00239','Classic Vacation Systems','686080659','LLC',2009,90,2751635,@HospitalityKey,'7000','7211','BB','BB','Small Business','Silver',2,2858503,142925,0,1,1,0,'2024-01-07',NULL,1,GETDATE(),GETDATE()),
('CUST00240','Prime Produce Enterprises','788376130','Corporation',2017,4650,445046728,@AgricultureKey,'0100','1111','BBB','BBB','Large Corporate','Platinum',16,88810383,4440519,0,1,1,0,'2024-01-08',NULL,1,GETDATE(),GETDATE()),
('CUST00241','National Carriers Enterprises','219637766','LLC',2016,73,3559933,@TransportKey,'4000','4841','A','A','Small Business','Bronze',2,1926927,96346,0,1,0,0,'2024-01-09',NULL,1,GETDATE(),GETDATE()),
('CUST00242','Expert Works Industries','277930196','LLC',2010,99,1864366,@ConstructionKey,'1500','2361','BB','BB','Small Business','Silver',1,1376613,68830,0,1,1,0,'2024-01-10',NULL,1,GETDATE(),GETDATE()),
('CUST00243','Boutique Accommodations Industries','891815133','LLC',2006,346,36354886,@HospitalityKey,'7000','7211','BBB','BBB','Middle Market','Silver',4,27514758,1375737,0,1,1,0,'2024-01-11',NULL,1,GETDATE(),GETDATE()),
('CUST00244','Premier Structures Services','585372010','LLC',2013,9,1065714,@ConstructionKey,'1500','2361','B','B','Small Business','Bronze',3,1290303,64515,0,1,1,0,'2024-01-12',NULL,1,GETDATE(),GETDATE()),
('CUST00245','Cyber Technologies Systems','516716157','Corporation',2014,94,1487456,@TechKey,'7370','5112','B','B','Small Business','Silver',2,4564275,228213,0,1,0,0,'2024-01-13',NULL,1,GETDATE(),GETDATE()),
('CUST00246','Grand Stay Technologies','773143050','LLC',2008,759,21580758,@HospitalityKey,'7000','7211','A','A','Middle Market','Silver',8,20480449,1024022,0,1,1,0,'2024-01-14',NULL,1,GETDATE(),GETDATE()),
('CUST00247','Country Crops Partners','244284635','Corporation',2015,474,36497106,@AgricultureKey,'0100','1111','B','B','Middle Market','Silver',7,7968628,398431,0,1,1,0,'2024-01-05',NULL,1,GETDATE(),GETDATE()),
('CUST00248','Prime Realty Holdings','332244409','Corporation',2012,86,3014027,@RealEstateKey,'6500','5311','BBB','BBB','Small Business','Bronze',1,562550,28127,0,1,0,0,'2024-01-06',NULL,1,GETDATE(),GETDATE()),
('CUST00249','Grand Retreat Holdings','129155017','LLC',2018,744,32946905,@HospitalityKey,'7000','7211','BBB','BBB','Middle Market','Silver',7,27185618,1359280,0,1,1,0,'2024-01-07',NULL,1,GETDATE(),GETDATE());

SELECT 'Batch completed: 217 to 249' AS Status, COUNT(*) AS TotalCustomers FROM dim.DimCustomer;

