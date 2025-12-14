# Getting Started with Databricks ETL Framework

This guide will walk you through setting up and running the Databricks ETL Framework from scratch.

## Prerequisites

Before you begin, ensure you have:

1. **Databricks Workspace** (Azure, AWS, or GCP)
2. **Azure Storage Account** (or equivalent cloud storage)
   - Named pattern: `storage_account_dev`, `storage_account_test`, `storage_account_prod`
3. **Databricks CLI** installed locally
4. **Python 3.10+** installed
5. **Git** installed
6. **Access permissions**:
   - Workspace admin or contributor
   - Storage account access (read/write to landing zone)

## Step 1: Clone the Repository

```bash
git clone https://github.com/your-org/vibecoded_databricks_accelerator.git
cd vibecoded_databricks_accelerator
```

## Step 2: Set Up Storage Account

### Create Landing Zone Container

In your Azure Storage Account (or cloud equivalent):

```bash
# Azure CLI example
az storage container create \
  --name landing-zone \
  --account-name storage_account_dev

# Create raw data directory structure
az storage blob directory create \
  --container-name landing-zone \
  --directory raw \
  --account-name storage_account_dev
```

### Landing Zone Structure

Your storage should look like:
```
storage_account_dev/
└── landing-zone/
    └── raw/
        ├── customers/     # Raw customer files land here
        ├── orders/        # Raw order files land here
        └── products/      # Raw product files land here
```

## Step 3: Configure Databricks Authentication

```bash
# Install Databricks CLI
pip install databricks-cli

# Configure authentication
databricks configure --token

# When prompted, enter:
# - Databricks Host: https://adb-xxxxx.azuredatabricks.net
# - Token: Your personal access token (generate from User Settings)
```

## Step 4: Update Configuration Files

### Update `databricks.yml`

Replace placeholder workspace URLs with your actual workspaces:

```yaml
targets:
  dev:
    workspace:
      host: "https://adb-YOUR-DEV-WORKSPACE.azuredatabricks.net"

  prod:
    workspace:
      host: "https://adb-YOUR-PROD-WORKSPACE.azuredatabricks.net"
```

### Update `config.yml` (if needed)

The default configuration uses:
- Storage account pattern: `storage_account_{env}`
- Container: `landing-zone`
- Base path: `raw`

If your naming differs, update the `landing_zone` section.

## Step 5: Set Up Environment Variables

```bash
# For local development/testing
export DATABRICKS_ENVIRONMENT=dev
export DATABRICKS_HOST=https://adb-xxxxx.azuredatabricks.net
export DATABRICKS_TOKEN=your-token-here
```

## Step 6: Configure GitHub Secrets (for CI/CD)

In your GitHub repository settings, add these secrets:

```
DATABRICKS_DEV_HOST=https://adb-xxxxx.azuredatabricks.net
DATABRICKS_DEV_TOKEN=dapi-xxxxx
DATABRICKS_PROD_HOST=https://adb-yyyyy.azuredatabricks.net
DATABRICKS_PROD_TOKEN=dapi-yyyyy
```

## Step 7: Deploy to Databricks

### Validate Configuration

```bash
# Validate DAB configuration
databricks bundle validate -t dev
```

### Deploy to Dev Environment

```bash
# Deploy to dev workspace
databricks bundle deploy -t dev
```

This will:
- Upload pipeline code to workspace
- Create DLT pipelines
- Create scheduled workflows (2 AM finance, 3 AM daily)
- Set up permissions

## Step 8: Upload Sample Data to Landing Zone

For testing, upload sample data files:

```bash
# Example: Upload sample customer data (parquet format)
az storage blob upload-batch \
  --destination landing-zone/raw/customers \
  --source ./sample-data/customers/ \
  --account-name storage_account_dev
```

Sample parquet files should have schemas matching your transformation expectations.

## Step 9: Test the Pipeline

### Manual Run via Databricks UI

1. Go to Databricks Workflows
2. Find "ETL Pipeline - Finance" or "ETL Pipeline - Daily"
3. Click "Run Now"
4. Optionally override parameters (tags, mode)

### Manual Run via CLI

```bash
# Run finance pipeline
databricks jobs run-now --job-id <job-id> \
  --parameters '{"tags": "finance", "mode": "batch"}'
```

### Local Testing (Development)

```bash
# Test configuration validation
python pipelines/ldp_engine.py --tags finance --mode batch

# This will validate config and show execution plan
# (Actual execution requires Databricks runtime)
```

## Step 10: Monitor Execution

### Via Databricks UI

1. Go to **Workflows** → Select your job
2. Click on latest run
3. View task logs and execution details

### Via CLI

```bash
# Get run status
databricks runs get --run-id <run-id>

# Get run output
databricks runs get-output --run-id <run-id>
```

## Common Tasks

### Adding a New Table

1. **Add to `config.yml`**:
```yaml
  - name: products_bronze
    layer: bronze
    tags: [bronze, daily]
    depends_on: []
    source:
      format: parquet
```

2. **Create transformation file**:
```bash
# Create new file
touch pipelines/transformations/bronze/products_bronze.py
```

3. **Implement transformation**:
```python
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, lit, input_file_name

def transform(source_df: DataFrame, spark: SparkSession) -> DataFrame:
    return (source_df
            .withColumn("_ingestion_timestamp", current_timestamp())
            .withColumn("_source_system", lit("landing_zone"))
            .withColumn("_source_file", input_file_name()))
```

4. **Deploy changes**:
```bash
databricks bundle deploy -t dev
```

### Changing Schedules

Edit `workflows/etl_job.yml`:

```yaml
schedule:
  quartz_cron_expression: "0 0 4 * * ?"  # Change to 4 AM
```

Then redeploy:
```bash
databricks bundle deploy -t dev
```

### Deploying to Production

1. **Merge to main branch**
2. **Create a release tag**:
```bash
git tag -a v1.0.0 -m "Production release 1.0.0"
git push origin v1.0.0
```

3. **GitHub Actions** will automatically deploy to prod

## Troubleshooting

### Issue: "Configuration file not found"

**Solution**: Ensure you're running commands from the repository root directory.

### Issue: "Storage account not found"

**Solution**:
- Verify storage account naming matches pattern: `storage_account_{env}`
- Check environment variable: `echo $DATABRICKS_ENVIRONMENT`
- Verify storage account exists in Azure

### Issue: "Import error: Cannot import transformation module"

**Solution**:
- Ensure transformation file name matches table name
- Check that `transform` function exists in the module
- Verify Python syntax is correct

### Issue: "No files found in landing zone"

**Solution**:
- Check file path derivation (table name → entity name)
- Verify files exist in correct location: `landing-zone/raw/{entity_name}/`
- Check file format matches config (`parquet`, `csv`, etc.)

### Issue: "Workflow fails immediately"

**Solution**:
- Check Databricks cluster logs
- Verify environment variables are set
- Ensure DAB deployment succeeded
- Check for Python import errors in logs

## Next Steps

- Review `docs/design.md` for architecture details
- Read `docs/requirements.md` for feature requirements
- Check `docs/tasks.md` for development roadmap
- Explore example transformations in `pipelines/transformations/`

## Support

- **Documentation**: `docs/` directory
- **Issues**: Create GitHub issue
- **Questions**: Contact data engineering team

## Auto-Deploy on Tag Creation

When you create a git tag starting with `v` (e.g., `v1.0.0`), the CI/CD pipeline automatically:

1. **Validates** code and configuration
2. **Runs tests** (if configured)
3. **Deploys to production** using `databricks bundle deploy -t prod`
4. **Creates GitHub Release** with deployment details

### Creating a Production Release

```bash
# Ensure main branch is ready
git checkout main
git pull

# Create and push tag
git tag -a v1.0.0 -m "Production release: Initial ETL framework"
git push origin v1.0.0

# GitHub Actions will automatically deploy to prod
# Check Actions tab for deployment status
```

### Tag Naming Convention

- **v{major}.{minor}.{patch}**: Production releases (e.g., `v1.0.0`, `v1.2.3`)
- Triggers production deployment automatically
- Creates immutable release in GitHub

### Deployment Stages

1. **Pull Request**: Validation only (linting, YAML check)
2. **Merge to main**: Auto-deploy to **dev**
3. **Tag creation (v*)**: Auto-deploy to **prod** + create release

This ensures:
- Dev environment stays up-to-date with latest changes
- Production deployments are intentional and versioned
- Full audit trail of what was deployed when
