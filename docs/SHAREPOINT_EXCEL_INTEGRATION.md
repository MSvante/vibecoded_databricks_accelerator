# SharePoint & Excel Integration Guide

## Overview

This guide explains how to integrate SharePoint Excel files as data sources for the ETL framework using Databricks' SharePoint connector and Excel reading capabilities.

## Architecture

```
SharePoint Site
  └── Document Library
      └── Data Files/
          ├── customers.xlsx
          ├── orders.xlsx
          └── products.xlsx
                ↓
        [Manual/Automated Upload]
                ↓
Unity Catalog Volume: /Volumes/etl_framework_dev/landing_zone/raw/
  ├── customers/
  │   └── customers.parquet (converted)
  ├── orders/
  │   └── orders.parquet
  └── products/
      └── products.parquet
                ↓
        [Bronze Layer Ingestion]
                ↓
        Delta Tables (customers_bronze, orders_bronze, etc.)
```

## Option 1: SharePoint Connector (Automated)

Databricks provides a native SharePoint connector for automated file synchronization.

### Setup SharePoint Connection

```python
# In a Databricks notebook or init script

from databricks.sharepoint import SharePointClient

# Configure SharePoint connection
sp_client = SharePointClient(
    site_url="https://yourcompany.sharepoint.com/sites/DataTeam",
    client_id="your-app-client-id",  # Azure AD App Registration
    client_secret=dbutils.secrets.get("sharepoint", "client-secret"),
    tenant_id="your-tenant-id"
)

# List files in document library
files = sp_client.list_files(library_name="Data Files", folder_path="Daily Reports")

# Download Excel file to landing zone volume
for file in files:
    if file.endswith('.xlsx'):
        # Download to volume
        sp_client.download_file(
            library_name="Data Files",
            file_path=f"Daily Reports/{file}",
            local_path=f"/Volumes/etl_framework_dev/landing_zone/raw/temp/{file}"
        )

        # Convert Excel to Parquet
        entity_name = file.replace('.xlsx', '')
        df = spark.read.format("com.crealytics.spark.excel") \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .load(f"/Volumes/etl_framework_dev/landing_zone/raw/temp/{file}")

        # Write as parquet to landing zone
        df.write.mode("overwrite").parquet(
            f"/Volumes/etl_framework_dev/landing_zone/raw/{entity_name}/"
        )
```

### Azure AD App Registration

1. Go to Azure Portal → Azure Active Directory → App Registrations
2. Create new registration:
   - Name: "Databricks SharePoint Connector"
   - Supported account types: Single tenant
3. Add API Permissions:
   - Microsoft Graph: `Sites.Read.All`, `Files.Read.All`
4. Create client secret (store in Databricks Secrets)
5. Grant admin consent for permissions

## Option 2: Manual Upload to Landing Zone

For simpler scenarios, manually convert and upload Excel files.

### Step 1: Convert Excel to Parquet Locally

```python
# Local Python script or notebook
import pandas as pd

# Read Excel
df = pd.read_excel('customers.xlsx')

# Write as Parquet
df.to_parquet('customers.parquet', index=False)
```

### Step 2: Upload to Volume via Databricks UI

1. Open Databricks workspace
2. Go to **Catalog** → **etl_framework_dev** → **landing_zone** → **raw**
3. Click **Upload** → Select parquet file
4. Place in appropriate entity folder (e.g., `customers/`)

### Step 3: Verify Upload

```python
# In Databricks notebook
dbutils.fs.ls("/Volumes/etl_framework_dev/landing_zone/raw/customers/")

# Should show: customers.parquet
```

## Option 3: Databricks Excel Reader (Direct)

Read Excel files directly from volumes without conversion.

### Install Excel Library

```python
# In cluster init script or notebook
%pip install openpyxl xlrd
```

### Update Bronze Transformation

For Excel sources, update `source.format` in `config.yml`:

```yaml
tables:
  - name: customers_bronze
    layer: bronze
    tags: [bronze, daily]
    source:
      format: excel  # Instead of parquet
```

### Modify LDP Engine to Handle Excel

In `ldp_engine.py`, update `create_table_function` to handle Excel format:

```python
if source_format == 'excel':
    source_df = self.spark.read.format("com.crealytics.spark.excel") \
        .option("header", "true") \
        .option("inferSchema", "true") \
        .option("dataAddress", "'Sheet1'!A1") \
        .load(source_path + "*.xlsx")
else:
    source_df = self.spark.read.format(source_format).load(source_path)
```

## Recommended Approach for Daily Reporting

For your daily reporting use case, I recommend:

### **Hybrid Approach:**

1. **SharePoint as Source of Truth**
   - Business users upload Excel files to SharePoint
   - Files organized in folders by entity (Customers, Orders, etc.)

2. **Automated ETL Job to Landing Zone**
   - Nightly job (1 AM) downloads Excel from SharePoint
   - Converts to Parquet
   - Writes to Unity Catalog volume
   - Job logs which files were processed

3. **ETL Framework Processes Parquet**
   - Finance pipeline (2 AM) processes converted files
   - Daily pipeline (3 AM) processes all entities
   - Bronze layer adds housekeeping columns
   - Silver/Gold create reporting tables

### Implementation: SharePoint Sync Job

Create a new workflow that runs before the ETL pipelines:

```yaml
# workflows/sharepoint_sync.yml
resources:
  jobs:
    sharepoint_to_landing_zone:
      name: "SharePoint to Landing Zone Sync"

      schedule:
        quartz_cron_expression: "0 0 1 * * ?"  # 1 AM daily
        timezone_id: "UTC"

      tasks:
        - task_key: sync_sharepoint_files
          notebook_task:
            notebook_path: "/Workspace/etl_framework/scripts/sharepoint_sync"
            base_parameters:
              sharepoint_site: "https://yourcompany.sharepoint.com/sites/DataTeam"
              library_name: "Data Files"
              target_volume: "/Volumes/etl_framework_dev/landing_zone/raw"
```

### SharePoint Sync Notebook

```python
# /scripts/sharepoint_sync.py
from databricks.sharepoint import SharePointClient
from pyspark.sql import SparkSession

spark = SparkSession.builder.getOrCreate()

# Configuration
ENTITIES = ['customers', 'orders', 'products']
SHAREPOINT_FOLDER = "Daily Reports"

sp_client = SharePointClient(
    site_url=dbutils.widgets.get("sharepoint_site"),
    client_id=dbutils.secrets.get("sharepoint", "client-id"),
    client_secret=dbutils.secrets.get("sharepoint", "client-secret"),
    tenant_id=dbutils.secrets.get("sharepoint", "tenant-id")
)

for entity in ENTITIES:
    try:
        # Download latest Excel file
        files = sp_client.list_files(
            library_name="Data Files",
            folder_path=f"{SHAREPOINT_FOLDER}/{entity}"
        )

        latest_file = max(files, key=lambda f: f.modified_date)

        # Read Excel
        temp_path = f"/tmp/{entity}.xlsx"
        sp_client.download_file(
            library_name="Data Files",
            file_path=f"{SHAREPOINT_FOLDER}/{entity}/{latest_file.name}",
            local_path=temp_path
        )

        # Convert to Parquet
        df = spark.read.format("com.crealytics.spark.excel") \
            .option("header", "true") \
            .option("inferSchema", "true") \
            .load(temp_path)

        # Write to landing zone
        target_path = f"/Volumes/etl_framework_dev/landing_zone/raw/{entity}/"
        df.write.mode("overwrite").parquet(target_path)

        print(f"✓ Synced {entity}: {latest_file.name} → {target_path}")

    except Exception as e:
        print(f"✗ Failed to sync {entity}: {e}")
        # Log to monitoring system
        raise
```

## Data Flow Timeline

```
1:00 AM - SharePoint Sync Job
  ↓ Downloads Excel from SharePoint
  ↓ Converts to Parquet
  ↓ Writes to landing zone volumes

2:00 AM - Finance ETL Pipeline
  ↓ Processes finance-tagged tables
  ↓ Bronze → Silver → Gold

3:00 AM - Daily ETL Pipeline
  ↓ Processes all daily tables
  ↓ Bronze → Silver → Gold

8:00 AM - Business users access reports
  ↓ Query gold layer tables
  ↓ Dashboards refresh
```

## Troubleshooting

### Issue: SharePoint authentication fails

**Solution:**
- Verify Azure AD app permissions
- Check client secret hasn't expired
- Confirm tenant ID is correct
- Ensure admin consent granted

### Issue: Excel files not found

**Solution:**
- Check SharePoint folder path
- Verify file naming convention
- Ensure service account has read access

### Issue: Excel schema changes

**Solution:**
- Add schema validation in sync job
- Log schema mismatches
- Alert data team if schema changes detected

## Next Steps

1. Set up Azure AD app registration
2. Store credentials in Databricks Secrets
3. Create SharePoint sync notebook
4. Test with sample Excel file
5. Schedule sync job before ETL pipelines
6. Monitor sync job logs

This approach ensures:
- Business users continue using familiar Excel/SharePoint
- Automated, reliable data ingestion
- Clean separation between source and processing
- Easy troubleshooting and monitoring
