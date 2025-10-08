# Docker Build Optimization

## Purpose

The `.dockerignore` file in this directory optimizes the Docker build process for Azure Container Apps deployment by excluding unnecessary files from the build context.

## Why It's in the Root Directory

The `Dockerfile.multimodel` (located in `azure_deployment/`) builds from the **project root**, so the `.dockerignore` must be in the root directory to take effect.

## What Gets Excluded

The `.dockerignore` file excludes:

### 🚫 Development Files
- `.venv/`, `venv/`, virtual environments
- `__pycache__/`, `*.pyc`, Python cache files
- `.git/`, `.github/`, version control
- `.vscode/`, `.idea/`, IDE configurations

### 🚫 Documentation & Media
- `*.md` files (except README.md)
- `docs/`, documentation directory
- `*.png`, `*.jpg`, image files
- `diagrams/`, diagram files

### 🚫 Deployment Files
- `azure_deployment/` directory (except Dockerfile itself)
- `.env`, `.env.*` environment files
- `*.bicep`, `*.parameters.json`, infrastructure files
- `*.sh` deployment scripts

### 🚫 Test & Backup Files
- `tests/`, test directories
- `BACKUPS/`, backup directories
- `*.log`, log files
- `RESULTS/`, runtime results

### 🚫 Large Unused Directories
- `star_schema_poc/`
- `MSSQL_Extension_for_vscode/`
- Various tool directories

## What Gets Included ✅

The `.dockerignore` explicitly **includes** these essential files:
- `requirements.txt` - Python dependencies
- `credentials.json` - App configuration
- `schema_reader.py` - Database schema reader
- `sql_executor.py` - SQL execution module
- `nl2sql_main.py` - Core application logic
- `azure_openai_pricing.json` - Pricing configuration
- All files in `ui/streamlit_app/` - Application code
- All files in `nl2sql_standalone_Langchain/` - Core modules

## Benefits

✅ **Faster Builds** - Less data to upload to Azure Container Registry  
✅ **Smaller Images** - Only necessary files included  
✅ **Better Security** - Sensitive files (`.env`, secrets) excluded  
✅ **Cleaner Container** - No development clutter  

## Typical Build Context Reduction

- **Without `.dockerignore`**: ~500+ MB
- **With `.dockerignore`**: ~50-100 MB (10x smaller!)

## Testing the Build Context

To see what would be included in the Docker build:

```bash
# List files that would be sent to Docker
docker build --no-cache -f azure_deployment/Dockerfile.multimodel . 2>&1 | head -20

# Or check the actual build context size
docker build -f azure_deployment/Dockerfile.multimodel -t test-image . --progress=plain 2>&1 | grep "transferring context"
```

## Modifying the .dockerignore

If you need to include additional files:

1. Edit `.dockerignore` in the **root directory**
2. Add `!filename` to explicitly include a file
3. Test your changes with a build

Example:
```dockerfile
# Exclude all JSON files
*.json

# But include this specific one
!important-config.json
```

## Related Files

- **Dockerfile**: `azure_deployment/Dockerfile.multimodel`
- **Build Script**: `azure_deployment/deploy.sh`
- **Deployment Guide**: `azure_deployment/DEPLOYMENT_GUIDE.md`

---

**Note**: This file is automatically used by Docker when building from the project root. No action needed during normal deployment.
