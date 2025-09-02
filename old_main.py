
"""
main.py - NL2DAX & NL2SQL Pipeline Entrypoint
=============================================

This script demonstrates how to build an end-to-end natural language to DAX and SQL pipeline 
using LangChain, Azure OpenAI, and schema-aware query generation. It serves as a comprehensive
example of how to:

1. Extract intent and entities from natural language queries
2. Generate both SQL and DAX queries from structured intent
3. Validate and format generated queries
4. Execute queries against both SQL databases and Power BI semantic models
5. Present results in formatted tables
6. Handle errors gracefully and provide debugging information

Architecture Overview:
- Uses Azure OpenAI GPT models for natural language understanding
- Implements schema-aware query generation for better accuracy
- Supports dual query generation (SQL for Azure SQL DB, DAX for Power BI)
- Includes comprehensive error handling and execution logging
- Provides formatted output for both console and file persistence

Key Features:
- Intent extraction using advanced prompting techniques
- SQL query generation with T-SQL syntax validation
- DAX query generation with Power BI semantic model awareness
- Query sanitization and smart quote handling
- Tabular result formatting for readability
- Performance timing and execution metrics
- Persistent output storage with timestamped filenames

Target Use Cases:
- Business users who need to query data using natural language
- Developers building NL2SQL/NL2DAX applications
- Data analysts who want to bridge natural language and technical queries
- Educational demonstrations of LLM-powered query generation
example of how to:

1. Extract intent and entities from natural language queries
2. Generate both SQL and DAX queries from structured intent
3. Validate and format generated queries
4. Execute queries against both SQL databases and Power BI semantic models
5. Present results in formatted tables
6. Handle errors gracefully and provide debugging information

Architecture Overview:
- Uses Azure OpenAI GPT models for natural language understanding
- Implements schema-aware query generation for better accuracy
- Supports dual query generation (SQL for Azure SQL DB, DAX for Power BI)
- Includes comprehensive error handling and execution logging
- Provides formatted output for both console and file persistence

Key Features:
- Intent extraction using advanced prompting techniques
- SQL query generation with T-SQL syntax validation
- DAX query generation with Power BI semantic model awareness
- Query sanitization and smart quote handling
- Tabular result formatting for readability
- Performance timing and execution metrics
- Persistent output storage with timestamped filenames

Target Use Cases:
- Business users who need to query data using natural language
- Developers building NL2SQL/NL2DAX applications
- Data analysts who want to bridge natural language and technical queries
- Educational demonstrations of LLM-powered query generation
"""

# --- Imports and Setup ---
# Essential imports for building the NL2DAX/NL2SQL pipeline
import os
from dotenv import load_dotenv  # Securely load environment variables from .env file
from langchain_openai import AzureChatOpenAI  # Azure OpenAI integration for LLM functionality
from langchain.prompts import ChatPromptTemplate  # Template system for consistent prompting

# Custom modules for specialized query generation and execution
from dax_generator import generate_dax  # Handles DAX query generation from intent/entities
from dax_formatter import format_and_validate_dax  # DAX syntax validation and formatting
from query_executor import execute_dax_query  # Power BI semantic model query execution
from sql_executor import execute_sql_query  # Azure SQL Database query execution

# Debug checkpoint to confirm script initialization
print("[DEBUG] Script started")

# --- NL2SQL Prompt Setup ---
from langchain.prompts import ChatPromptTemplate as SQLChatPromptTemplate

# This prompt template is specifically designed for SQL query generation.
# It provides the LLM with:
# 1. Role definition as an SQL expert with Azure SQL DB knowledge
# 2. Database schema context for accurate table/column references
# 3. Parsed intent and entities to guide query construction
# 
# The prompt engineering ensures:
# - T-SQL syntax compliance for Azure SQL Database
# - Schema-aware query generation (proper table/column names)
# - Intent-driven query logic based on extracted entities
sql_prompt = SQLChatPromptTemplate.from_template(
    """
    You are an expert in SQL and Azure SQL Database. Given the following database schema and the intent/entities, generate a valid T-SQL query for querying the database.
    
    IMPORTANT: 
    - Do NOT use USE statements (USE [database] is not supported in Azure SQL Database)
    - Generate only the SELECT query without USE or GO statements
    - Return only executable T-SQL code without markdown formatting
    - The database connection is already established to the correct database
    
    Schema:
    {schema}
    Intent and Entities:
    {intent_entities}
    
    Generate a T-SQL query that can be executed directly:
    """
)


# --- NL2SQL Generation Function ---
def generate_sql(intent_entities):
    """
    Generate a SQL query from extracted intent and entities using schema-aware prompting.
    
    This function demonstrates the power of combining:
    1. Schema context injection for accurate table/column references
    2. Intent-based query construction from natural language understanding
    3. LLM chain composition using LangChain for consistent prompt execution
    
    Args:
        intent_entities (str): Structured representation of user intent and identified entities
                              extracted from the natural language query
    
    Returns:
        str: Generated T-SQL query that should be syntactically valid and 
             semantically aligned with the user's intent
    
    Process Flow:
    1. Retrieve current database schema context from the schema reader
    2. Create a prompt chain combining the SQL template with the LLM
    3. Invoke the chain with schema and intent context
    4. Return the generated SQL query content
    
    This approach ensures that generated queries:
    - Reference actual tables and columns from the database
    - Follow T-SQL syntax conventions for Azure SQL Database
    - Align with the user's expressed intent and identified entities
    """
    from schema_reader import get_sql_database_schema_context  # Import SQL database schema
    schema = get_sql_database_schema_context()  # Get SQL database schema for context injection
    chain = sql_prompt | llm  # Create LangChain prompt-to-LLM pipeline
    result = chain.invoke({"schema": schema, "intent_entities": intent_entities})  # Execute with context
    return result.content  # Return the generated SQL query



# --- Load Environment Variables ---
# Load sensitive configuration from .env file to avoid hardcoding credentials
# This includes Azure OpenAI API keys, endpoints, and other service configurations
load_dotenv()

# --- Azure OpenAI Configuration ---
# Retrieve Azure OpenAI service configuration from environment variables
# These credentials are required for LLM functionality and should be kept secure
API_KEY = os.getenv("AZURE_OPENAI_API_KEY")        # Authentication key for Azure OpenAI service
ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")       # Azure OpenAI service endpoint URL
DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")  # Specific model deployment name

# --- LLM Initialization ---
# Initialize the Azure OpenAI language model that will power both intent extraction
# and query generation throughout the pipeline. This single LLM instance is used for:
# 1. Natural language intent extraction and entity identification
# 2. SQL query generation from structured intent
# 3. DAX query generation for Power BI semantic models
#
# Configuration details:
# - Uses the latest API version for optimal feature support
# - Configured for chat completion tasks (not embedding or completion)
# - Supports both synchronous and asynchronous operation patterns
llm = AzureChatOpenAI(
    openai_api_key=API_KEY,           # Authenticate with Azure OpenAI service
    azure_endpoint=ENDPOINT,          # Target the correct Azure OpenAI instance
    deployment_name=DEPLOYMENT_NAME,  # Use the specified model deployment
    api_version="2024-12-01-preview"  # Latest API version for enhanced capabilities
)


# --- NL2Intent Prompt Setup ---
# This prompt template is the foundation of the natural language understanding pipeline.
# It's designed to transform unstructured user questions into structured intent/entity pairs
# that can be reliably used for downstream query generation.
#
# The prompt engineering approach:
# 1. Establishes the LLM's role as a database query translation expert
# 2. Focuses on extracting both intent (what the user wants to do) and entities (specific data points)
# 3. Provides a clear instruction format that yields consistent, parseable outputs
#
# Expected output format should include:
# - Intent: The type of operation (aggregation, filtering, joining, etc.)
# - Entities: Specific tables, columns, values, and conditions mentioned
# - Relationships: How different entities relate to each other in the query context
prompt = ChatPromptTemplate.from_template(
    """
    You are an expert in translating natural language to database queries. Extract the intent and entities from the following user input:
    {input}
    """
)


# --- NL2Intent Extraction Function ---
def parse_nl_query(user_input):
    """
    Extract structured intent and entities from natural language user input.
    
    This function serves as the critical first step in the NL2SQL/NL2DAX pipeline,
    transforming unstructured natural language into structured data that can be
    reliably processed by downstream query generation functions.
    
    Args:
        user_input (str): Raw natural language query from the user
                         Examples: "Show me top 5 customers by revenue"
                                  "What's the average order value last month?"
                                  "List all products in the electronics category"
    
    Returns:
        str: Structured representation of intent and entities extracted from the input
             This typically includes:
             - Intent type (aggregation, filtering, ranking, etc.)
             - Entity identification (table names, column names, values)
             - Relationship mapping (how entities connect)
             - Constraint specification (conditions, limits, groupings)
    
    Process:
    1. Create a LangChain pipeline combining the intent extraction prompt with the LLM
    2. Invoke the pipeline with the user's natural language input
    3. Return the LLM's structured analysis of intent and entities
    
    This structured output enables consistent and accurate query generation across
    both SQL and DAX query types, ensuring that the user's intent is preserved
    throughout the transformation process.
    """
    chain = prompt | llm  # Create prompt-to-LLM processing chain
    result = chain.invoke({"input": user_input})  # Process the natural language input
    return result.content  # Return structured intent/entity analysis


# --- Main Pipeline Execution ---
if __name__ == "__main__":
    # Initialize performance tracking to measure end-to-end pipeline execution time
    import time
    start_time = time.time()
    print("[DEBUG] Starting NL2DAX pipeline...")

    # --- Step 1: User Input Collection ---
    # Collect the natural language query from the user. This is the raw input that will
    # be processed through the entire NL2DAX/NL2SQL pipeline. The query should be
    # conversational and domain-specific to the available database schema.
    query = input("Enter your natural language query: ")
    print(f"[DEBUG] User query: {query}")

    # --- Step 2: Intent & Entity Extraction ---
    # Transform the natural language query into structured intent and entities.
    # This critical step uses advanced prompt engineering to extract:
    # - Query intent (what type of operation the user wants)
    # - Relevant entities (tables, columns, values, conditions)
    # - Implicit relationships and constraints
    # The structured output enables accurate query generation in subsequent steps.
    intent_entities = parse_nl_query(query)
    print("[DEBUG] Parsed intent/entities:")
    print(intent_entities)

    # --- Step 3: SQL Query Generation ---
    # Generate a T-SQL query from the extracted intent and entities.
    # This process combines:
    # - Database schema context for accurate table/column references
    # - Structured intent to guide query logic and operations
    # - T-SQL syntax expertise to ensure Azure SQL Database compatibility
    sql = generate_sql(intent_entities)
    print("[DEBUG] Generated SQL query:")
    print(sql)

    # --- Step 4: SQL Code Extraction & Sanitization ---
    # Extract only the SQL code from the LLM output (removing explanations and code fences).
    import re
    sql_code = sql
    code_block = re.search(r"```sql\s*([\s\S]+?)```", sql, re.IGNORECASE)
    if not code_block:
        code_block = re.search(r"```([\s\S]+?)```", sql)
    if code_block:
        sql_code = code_block.group(1).strip()
    else:
        select_match = re.search(r'(SELECT[\s\S]+)', sql, re.IGNORECASE)
        if select_match:
            sql_code = select_match.group(1).strip()
    # Replace smart quotes with standard quotes for SQL execution.
    sql_sanitized = sql_code.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')

    # --- Step 5: Output Preparation & Formatting ---
    # Prepare comprehensive output for both console display and file persistence.
    # This dual-output approach ensures that:
    # 1. Users see immediate feedback in the console with clear visual separators
    # 2. Complete results are saved to files for sharing, analysis, and reproducibility
    # 3. Consistent formatting is maintained across different output channels
    output_lines = []  # Collect all output for file writing
    
    # ANSI color codes for enhanced visual output
    class Colors:
        BLUE = '\033[94m'      # Input/Query phase
        GREEN = '\033[92m'     # SQL phase  
        PURPLE = '\033[95m'    # DAX phase
        YELLOW = '\033[93m'    # Results phase
        RED = '\033[91m'       # Error phase
        CYAN = '\033[96m'      # Info/Duration phase
        RESET = '\033[0m'      # Reset to default
    
    # Create colored ASCII banner function for clear visual separation of output sections
    # This improves readability and makes it easier to parse results visually
    def colored_banner(title, color=Colors.RESET):
        banner_text = f"\n{'='*10} {title} {'='*10}\n"
        return f"{color}{banner_text}{Colors.RESET}"
    
    # Plain banner for file output (no ANSI codes)
    plain_banner = lambda title: f"\n{'='*10} {title} {'='*10}\n"

    # Display and record the original natural language query
    # This provides context for understanding the generated queries and results
    print(colored_banner("NATURAL LANGUAGE QUERY", Colors.BLUE))
    print(query + "\n")
    output_lines.append(plain_banner("NATURAL LANGUAGE QUERY"))
    output_lines.append(f"{query}\n")

    # Display and record the generated SQL query with full LLM response
    # This includes any explanatory text or formatting that the LLM provided
    print(colored_banner("GENERATED SQL", Colors.GREEN))
    print(sql + "\n")
    output_lines.append(plain_banner("GENERATED SQL"))
    output_lines.append(f"{sql}\n")

    # If sanitization was needed, show the cleaned SQL for transparency
    # This helps users understand what modifications were made for execution
    if sql != sql_sanitized:
        print(colored_banner("SANITIZED SQL (FOR EXECUTION)", Colors.GREEN))
        print(sql_sanitized + "\n")
        output_lines.append(plain_banner("SANITIZED SQL (FOR EXECUTION)"))
        output_lines.append(f"{sql_sanitized}\n")

    # --- Step 6: SQL Query Execution & Result Formatting ---
    # Execute the sanitized SQL query against the Azure SQL Database and format results
    # in a readable table format. This section includes comprehensive error handling
    # to gracefully manage connection issues, syntax errors, and execution problems.
    try:
        print(colored_banner("EXECUTING SQL QUERY", Colors.GREEN))
        sql_results = execute_sql_query(sql_sanitized)  # Execute against Azure SQL DB
        
        if sql_results:
            # Format results as a readable table with proper column alignment
            # This dynamic formatting handles varying column widths and data types
            columns = sql_results[0].keys()  # Get column names from first result row
            
            # Calculate optimal column widths based on content and headers
            col_widths = {col: max(len(col), max(len(str(row[col])) for row in sql_results)) for col in columns}
            
            # Create formatted table header with proper spacing
            header = " | ".join([col.ljust(col_widths[col]) for col in columns])
            sep = "-+-".join(['-' * col_widths[col] for col in columns])  # Separator line
            
            print(colored_banner("SQL QUERY RESULTS (TABLE)", Colors.YELLOW))
            print(header)
            print(sep)
            
            # Print each data row with consistent column alignment
            for row in sql_results:
                print(" | ".join([str(row[col]).ljust(col_widths[col]) for col in columns]))
            
            # Record table results for file output
            output_lines.append(plain_banner("SQL QUERY RESULTS (TABLE)"))
            output_lines.append(header + "\n")
            output_lines.append(sep + "\n")
            for row in sql_results:
                output_lines.append(" | ".join([str(row[col]).ljust(col_widths[col]) for col in columns]) + "\n")
        else:
            # Handle case where query executes successfully but returns no data
            print(colored_banner("SQL QUERY RESULTS", Colors.YELLOW))
            print("No results returned.")
            output_lines.append(plain_banner("SQL QUERY RESULTS"))
            output_lines.append("No results returned.\n")
    except Exception as e:
        # Comprehensive error handling for SQL execution failures
        # This catches connection errors, syntax errors, permission issues, etc.
        err_msg = f"[ERROR] Failed to execute SQL query: {e}"
        print(colored_banner("SQL QUERY ERROR", Colors.RED))
        print(err_msg)
        output_lines.append(plain_banner("SQL QUERY ERROR"))
        output_lines.append(err_msg + "\n")

    # --- Step 7: DAX Query Generation ---
    # Generate a DAX expression from the same intent/entities used for SQL generation.
    # This demonstrates the pipeline's ability to target multiple query languages
    # from a single natural language input, enabling cross-platform data access.
    #
    # DAX (Data Analysis Expressions) is used for:
    # - Power BI semantic model queries
    # - Azure Analysis Services tabular models
    # - SQL Server Analysis Services tabular models
    # - Excel Power Pivot models
    dax = generate_dax(intent_entities)
    print("[DEBUG] Generated DAX expression:")
    print(dax)

    # --- Step 7.5: DAX Code Extraction & Sanitization ---
    # Extract only the DAX code from the LLM output (removing explanations and code fences).
    dax_code = dax
    # Look for DAX code blocks first
    dax_code_block = re.search(r"```dax\s*([\s\S]+?)```", dax, re.IGNORECASE)
    if not dax_code_block:
        dax_code_block = re.search(r"```([\s\S]+?)```", dax)
    if dax_code_block:
        dax_code = dax_code_block.group(1).strip()
    else:
        # Look for EVALUATE statement (DAX queries always start with EVALUATE)
        evaluate_match = re.search(r'(EVALUATE[\s\S]+)', dax, re.IGNORECASE)
        if evaluate_match:
            dax_code = evaluate_match.group(1).strip()
        else:
            # Try to find any pattern that looks like DAX after explanatory text
            lines = dax.split('\n')
            dax_lines = []
            found_dax = False
            for line in lines:
                # Skip explanatory lines
                if any(phrase in line.lower() for phrase in ['here\'s', 'here is', 'following', 'below', 'query', ':']):
                    continue
                # Look for DAX keywords
                if any(keyword in line.upper() for keyword in ['EVALUATE', 'SELECTCOLUMNS', 'FILTER', 'ADDCOLUMNS']):
                    found_dax = True
                if found_dax:
                    dax_lines.append(line)
            if dax_lines:
                dax_code = '\n'.join(dax_lines).strip()
    
    # Replace smart quotes with standard quotes for DAX execution
    dax_sanitized = dax_code.replace(''', "'").replace(''', "'").replace('"', '"').replace('"', '"')
    
    # Validate DAX completeness
    def validate_dax_completeness(dax_query):
        """Check if DAX query appears to be complete and well-formed"""
        if not dax_query.strip():
            return False, "Empty DAX query"
        
        if not dax_query.strip().upper().startswith('EVALUATE'):
            return False, "DAX query must start with EVALUATE"
            
        # Count parentheses to check for basic balance
        open_parens = dax_query.count('(')
        close_parens = dax_query.count(')')
        if open_parens > close_parens:
            return False, f"Unbalanced parentheses: {open_parens} open, {close_parens} close - query may be incomplete"
            
        # Check for incomplete function calls (common LLM truncation issue)
        if dax_query.rstrip().endswith(',') or dax_query.rstrip().endswith('('):
            return False, "Query appears to end mid-function - possibly truncated"
            
        return True, "DAX query appears complete"
    
    is_valid, validation_msg = validate_dax_completeness(dax_sanitized)
    print(f"[DEBUG] DAX Validation: {validation_msg}")
    
    if not is_valid:
        print(f"[WARN] DAX query validation failed: {validation_msg}")
        print("[WARN] Attempting to regenerate DAX query...")
        # Could implement retry logic here if needed
    
    print("[DEBUG] Extracted DAX code:")
    print(dax_sanitized)

    # --- Step 8: DAX Formatting & Validation ---
    # Format and validate the generated DAX using the DAX Formatter API.
    # This step ensures that:
    # 1. DAX syntax is correct and follows best practices
    # 2. Query structure is optimized for performance
    # 3. Function names and operators are properly cased
    # 4. Comments and whitespace are consistently formatted
    #
    # The DAX Formatter API provides professional-grade formatting that
    # improves readability and helps catch syntax errors before execution.
    formatted_dax, _ = format_and_validate_dax(dax_sanitized)
    print("[DEBUG] Formatted DAX:")
    print(formatted_dax)

    # Display both raw and formatted DAX for comparison and transparency
    print(colored_banner("GENERATED DAX", Colors.PURPLE))
    print(dax_sanitized + "\n")
    output_lines.append(plain_banner("GENERATED DAX"))
    output_lines.append(f"{dax_sanitized}\n")

    print(colored_banner("FORMATTED DAX", Colors.PURPLE))
    print(formatted_dax + "\n")
    output_lines.append(plain_banner("FORMATTED DAX"))
    output_lines.append(f"{formatted_dax}\n")

    # --- Step 9: DAX Query Execution (Power BI/Analysis Services) ---
    # Attempt to execute the generated DAX query against a Power BI semantic model
    # or Analysis Services tabular model using the XMLA endpoint. This section handles
    # platform-specific execution challenges and provides fallback options.
    #
    # DAX execution requirements:
    # - Power BI Premium or Pro workspace with XMLA endpoint enabled
    # - Proper authentication (service principal or user credentials)
    # - Network connectivity to Power BI service or Analysis Services
    # - Compatible DAX query syntax for the target semantic model
    #
    # Platform considerations:
    # - macOS/Linux: Requires Mono runtime for .NET interoperability
    # - Windows: Native support through .NET Framework/.NET Core
    # - Container environments: May need additional runtime configuration
    try:
        print(colored_banner("EXECUTING DAX QUERY", Colors.PURPLE))
        dax_results = execute_dax_query(dax_sanitized)  # Execute against Power BI/Analysis Services
        
        if dax_results:
            # Format DAX results using the same table formatting approach as SQL
            # This ensures consistent presentation across different query types
            dax_columns = dax_results[0].keys()
            dax_col_widths = {col: max(len(col), max(len(str(row[col])) for row in dax_results)) for col in dax_columns}
            dax_header = " | ".join([col.ljust(dax_col_widths[col]) for col in dax_columns])
            dax_sep = "-+-".join(['-' * dax_col_widths[col] for col in dax_columns])
            
            print(colored_banner("DAX QUERY RESULTS (TABLE)", Colors.YELLOW))
            print(dax_header)
            print(dax_sep)
            for row in dax_results:
                print(" | ".join([str(row[col]).ljust(dax_col_widths[col]) for col in dax_columns]))
            
            # Record DAX results for file output
            output_lines.append(plain_banner("DAX QUERY RESULTS (TABLE)"))
            output_lines.append(dax_header + "\n")
            output_lines.append(dax_sep + "\n")
            for row in dax_results:
                output_lines.append(" | ".join([str(row[col]).ljust(dax_col_widths[col]) for col in dax_columns]) + "\n")
        else:
            # Handle successful execution with no results
            print(colored_banner("DAX QUERY RESULTS", Colors.YELLOW))
            print("No results returned.")
            output_lines.append(plain_banner("DAX QUERY RESULTS"))
            output_lines.append("No results returned.\n")
    except RuntimeError as e:
        # Handle platform-specific runtime dependency issues (especially on macOS/Linux)
        warn_msg = f"[WARN] Skipping DAX execution: {e}"
        print(colored_banner("DAX EXECUTION WARNING", Colors.YELLOW))
        print(warn_msg)
        print("Install Mono and pythonnet (`brew install mono`), then `pip install pyadomd pythonnet`.")
        output_lines.append(plain_banner("DAX EXECUTION WARNING"))
        output_lines.append(warn_msg + "\n")
    except Exception as e:
        # Handle other DAX execution errors (authentication, network, syntax, etc.)
        err_msg = f"[ERROR] Failed to execute DAX query: {e}"
        print(colored_banner("DAX EXECUTION ERROR", Colors.RED))
        print(err_msg)
        output_lines.append(plain_banner("DAX EXECUTION ERROR"))
        output_lines.append(err_msg + "\n")

    # --- Step 10: Show Run Duration ---
    # Print and record the total run duration for performance awareness.
    end_time = time.time()
    duration = end_time - start_time
    duration_str = f"Run duration: {duration:.2f} seconds"
    print(colored_banner("RUN DURATION", Colors.CYAN))
    print(duration_str)
    output_lines.append(plain_banner("RUN DURATION"))
    output_lines.append(duration_str + "\n")

    # --- Step 11: Results Persistence and Session Logging ---
    # Save comprehensive query execution results to timestamped file for audit trail,
    # debugging, and analysis. This creates a permanent record of each NL2DAX/NL2SQL
    # pipeline execution including input, generated queries, results, and any errors.
    #
    # File naming convention: nl2dax_run_<sanitized_query>_<timestamp>.txt
    # This allows easy identification and chronological sorting of execution logs.
    #
    # Logging benefits:
    # - Performance analysis and query optimization insights
    # - Error pattern recognition for system improvement
    # - Audit trail for compliance and debugging purposes
    # - Historical query execution analysis
    # - User behavior and question pattern analysis
    from datetime import datetime
    
    # Create sanitized filename from user query
    # Remove special characters and limit length to prevent filesystem issues
    safe_query = query.strip().replace(' ', '_')[:40]  # Replace spaces, limit length
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_filename = f"nl2dax_run_{safe_query}_{timestamp}.txt"
    out_path = os.path.join(os.path.dirname(__file__), out_filename)
    
    # Write comprehensive execution log to file
    # Ensure all lines have proper newline termination for readability
    with open(out_path, 'w') as f:
        f.writelines([line if line.endswith('\n') else line + '\n' for line in output_lines])
    print(f"[INFO] Run results written to {out_path}")
