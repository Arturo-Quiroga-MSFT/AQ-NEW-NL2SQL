# NL2SQL Standalone Package

This is a self-contained version of the NL2SQL pipeline that can run independently.

## Contents

This directory contains all the files needed to run the NL2SQL pipeline:

### Core Files
- `nl2sql_main.py` - Main entry point for the NL2SQL pipeline
- `schema_reader.py` - Database schema reading utility
- `sql_executor.py` - SQL query execution utility

### Configuration Files
- `.env` - Environment variables (Azure OpenAI and SQL credentials)
- `azure_openai_pricing.json` - Token pricing configuration
- `requirements.txt` - Python package dependencies

## Setup

1. **Create a virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On macOS/Linux
   # or
   .venv\Scripts\activate  # On Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Edit `.env` file with your Azure OpenAI and SQL credentials
   - Required variables:
     - `AZURE_OPENAI_API_KEY`
     - `AZURE_OPENAI_ENDPOINT`
     - `AZURE_OPENAI_DEPLOYMENT_NAME`
     - `AZURE_OPENAI_API_VERSION`
     - `AZURE_SQL_SERVER`
     - `AZURE_SQL_DB`
     - `AZURE_SQL_USER`
     - `AZURE_SQL_PASSWORD`

## Usage

Run the NL2SQL pipeline:

```bash
python nl2sql_main.py
```

### Command-line Options

- `--query "your question"` - Provide query inline
- `--refresh-schema` - Refresh schema cache before generation
- `--no-reasoning` - Skip the reasoning/plan step
- `--explain-only` - Show intent + reasoning only, skip SQL & execution
- `--no-exec` - Generate SQL but don't execute
- `--whoami` - Print script purpose and exit

### Example

```bash
python nl2sql_main.py --query "How many customers do I have?"
```

## Output

Results are saved to a `RESULTS/` directory (created automatically) with timestamped filenames.

## Notes

- Ensure Microsoft ODBC Driver 18 for SQL Server is installed on your system
- The schema cache will be created on first run
- Python 3.11+ recommended
