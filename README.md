# Databricks ETL Framework

A configuration-driven ETL framework using **Databricks Lakeflow Declarative Pipelines (LDP)** for building scalable, maintainable data pipelines with tag-based orchestration and Bronze-Silver-Gold architecture.

## Overview

This framework enables data engineers to build production-ready ETL pipelines on Databricks using a declarative, configuration-first approach. Define your tables in YAML, write transformations in Python, and let the framework handle dependency resolution, orchestration, and deployment.

## Key Features

- **Configuration-Driven**: Define all tables and dependencies in `config.yml`
- **Tag-Based Execution**: Run subsets of pipelines using tags (`daily`, `critical`, `bronze`, etc.)
- **Automatic Dependency Resolution**: Topological sorting ensures correct execution order
- **Medallion Architecture**: Bronze → Silver → Gold data quality progression
- **Python Transformations**: Write all transformations in Python (no SQL limitations)
- **Databricks Native**: Leverages Lakeflow Declarative Pipelines and Delta Lake
- **CI/CD Ready**: Deploy via Databricks Asset Bundles with GitHub Actions
- **Batch & Streaming**: Single codebase supports both execution modes

## Quick Start

### Prerequisites

- Databricks workspace (Azure, AWS, or GCP)
- Python 3.10+
- Databricks CLI installed
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/your-org/databricks_etl_framework.git
cd databricks_etl_framework

# Install dependencies
pip install -r requirements.txt

# Or install as a package
pip install -e .
```

### Basic Usage

1. **Define tables in `config.yml`**:

```yaml
tables:
  - name: customers_bronze
    layer: bronze
    tags: [bronze, daily]
    depends_on: []

  - name: customers_silver
    layer: silver
    tags: [silver, daily]
    depends_on: [customers_bronze]
```

2. **Create transformation files**:

```python
# pipelines/transformations/bronze/customers_bronze.py
import dlt
from pyspark.sql import DataFrame

@dlt.table(name="customers_bronze")
def customers_bronze() -> DataFrame:
    # Your transformation logic
    return spark.read.format("json").load("source_path")
```

3. **Deploy to Databricks**:

```bash
# Validate configuration
databricks bundle validate -t dev

# Deploy to dev environment
databricks bundle deploy -t dev
```

4. **Run the pipeline**:

```bash
# Run all tables tagged with 'daily'
python pipelines/ldp_engine.py --tags daily --mode batch

# Run tables with multiple tags (OR logic)
python pipelines/ldp_engine.py --tags bronze,critical --mode batch

# Run in streaming mode
python pipelines/ldp_engine.py --tags streaming --mode streaming
```

## Project Structure

```
databricks_etl_framework/
├── config.yml                          # Pipeline configuration
├── databricks.yml                      # Databricks Asset Bundle config
├── pyproject.toml                      # Python project configuration
├── pipelines/
│   ├── ldp_engine.py                   # Main orchestration engine
│   └── transformations/
│       ├── bronze/                     # Raw data ingestion
│       │   ├── customers_bronze.py
│       │   └── orders_bronze.py
│       ├── silver/                     # Cleaned & validated data
│       │   ├── customers_silver.py
│       │   └── orders_silver.py
│       └── gold/                       # Business aggregations
│           └── customer_metrics_gold.py
├── workflows/
│   └── etl_job.yml                     # Databricks job definition
├── .github/workflows/
│   └── deploy.yml                      # CI/CD pipeline
└── docs/
    ├── project-description.md          # Project overview
    ├── requirements.md                 # Business requirements
    ├── design.md                       # Technical architecture
    └── tasks.md                        # Development roadmap
```

## Configuration

### config.yml Structure

```yaml
tables:
  - name: table_name              # Must match transformation file name
    layer: bronze|silver|gold     # Data quality layer
    tags:                         # Tags for selective execution
      - daily
      - critical
    depends_on:                   # Upstream dependencies
      - upstream_table_1
      - upstream_table_2
    source:                       # Source configuration (TBD)
      type: TBD
      path: TBD
    description: "Table purpose"  # Human-readable description
```

### Tag-Based Execution

Execute specific subsets of your pipeline using tags:

```bash
# Run all daily tables
python ldp_engine.py --tags daily

# Run critical bronze tables (OR logic - any tag matches)
python ldp_engine.py --tags bronze,critical

# Run tables with BOTH tags (AND logic - all tags must match)
python ldp_engine.py --tags daily,critical --tag-mode AND
```

The engine automatically includes upstream dependencies even if they're not tagged.

## Architecture

### Medallion Architecture

- **Bronze Layer**: Raw data ingestion with minimal transformation
  - Add ingestion timestamps and source metadata
  - Preserve original data structure
  - Lenient data quality (log warnings)

- **Silver Layer**: Cleaned and validated data
  - Standardize formats (dates, strings, etc.)
  - Deduplicate records
  - Enforce data quality rules
  - Enrich with reference data

- **Gold Layer**: Business-level aggregations
  - Calculate KPIs and metrics
  - Join multiple silver tables
  - Create analytics-ready datasets
  - Materialized views for BI tools

### Dependency Resolution

The LDP engine uses topological sorting to determine execution order:

```yaml
# Configuration
customers_bronze: []
orders_bronze: []
customers_silver: [customers_bronze]
orders_silver: [orders_bronze, customers_silver]

# Execution Order:
# 1. customers_bronze, orders_bronze (parallel)
# 2. customers_silver
# 3. orders_silver
```

## Development Workflow

### Adding a New Table

1. **Add table to `config.yml`**:
```yaml
  - name: products_bronze
    layer: bronze
    tags: [bronze, daily]
    depends_on: []
```

2. **Create transformation file**:
```bash
touch pipelines/transformations/bronze/products_bronze.py
```

3. **Implement transformation**:
```python
import dlt
from pyspark.sql import DataFrame

@dlt.table(name="products_bronze", comment="Raw product data")
def products_bronze() -> DataFrame:
    return spark.read.format("json").load("s3://bucket/products/")
```

4. **Deploy and run**:
```bash
databricks bundle deploy -t dev
python ldp_engine.py --tags bronze
```

### Data Quality Expectations

Use DLT expectations for data quality:

```python
@dlt.table(name="customers_silver")
@dlt.expect_or_drop("valid_email", "email IS NOT NULL")
@dlt.expect_or_fail("unique_id", "customer_id IS NOT NULL")
def customers_silver() -> DataFrame:
    # Transformation logic
    pass
```

## Deployment

### Databricks Asset Bundles (DAB)

Deploy to different environments using DAB targets:

```bash
# Development
databricks bundle deploy -t dev

# Production
databricks bundle deploy -t prod
```

### CI/CD with GitHub Actions

The framework includes automated deployment pipelines:

- **Pull Request**: Validation and linting
- **Merge to `main`**: Deploy to dev
- **Tag creation (`v*`)**: Deploy to prod

Required GitHub secrets:
- `DATABRICKS_DEV_HOST`
- `DATABRICKS_DEV_TOKEN`
- `DATABRICKS_PROD_HOST`
- `DATABRICKS_PROD_TOKEN`

## Monitoring & Debugging

### Validate Configuration

```bash
# Check YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yml'))"

# Validate dependencies
python ldp_engine.py --tags daily --dry-run
```

### View Execution Plan

```bash
# See which tables will run and in what order
python ldp_engine.py --tags daily,critical
```

The engine logs:
- Configuration loading
- Tag filtering results
- Dependency resolution (execution order)
- Module loading status

## Examples

### Example 1: Daily Batch Pipeline

```yaml
# config.yml
tables:
  - name: transactions_bronze
    tags: [bronze, daily]
  - name: transactions_silver
    tags: [silver, daily]
    depends_on: [transactions_bronze]
```

```bash
# Schedule as cron job: daily at 2 AM
python ldp_engine.py --tags daily --mode batch
```

### Example 2: Streaming Pipeline

```yaml
# config.yml
tables:
  - name: events_bronze
    tags: [bronze, streaming]
  - name: events_silver
    tags: [silver, streaming]
    depends_on: [events_bronze]
```

```bash
# Run continuously
python ldp_engine.py --tags streaming --mode streaming
```

### Example 3: Critical Tables Only

```bash
# Run only critical tables during business hours
python ldp_engine.py --tags critical --mode batch
```

## Future Roadmap

See `docs/tasks.md` for detailed task breakdown.

### Planned Features

- **Extraction Layer**: Support for S3, JDBC, Kafka, REST APIs
- **Data Quality Framework**: Built-in validation rules in config.yml
- **Dry-Run Mode**: Preview execution without running transformations
- **DAG Visualization**: Generate execution plan diagrams
- **Cost Monitoring**: Track compute costs per pipeline
- **Schema Evolution**: Handle upstream schema changes gracefully

## Documentation

Comprehensive documentation in the `docs/` directory:

- **[Project Description](docs/project-description.md)**: Overview and key principles
- **[Requirements](docs/requirements.md)**: User stories and acceptance criteria
- **[Design](docs/design.md)**: Technical architecture and components
- **[Tasks](docs/tasks.md)**: Development roadmap and priorities

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Commit Message Format

- `feat: Add new transformation for product data`
- `fix: Resolve dependency resolution bug`
- `refactor: Simplify tag filtering logic`
- `docs: Update README with examples`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: Check the `docs/` directory
- **Issues**: Create a GitHub issue with details
- **Questions**: Use GitHub Discussions

## Acknowledgments

- Built for Databricks platform
- Uses Lakeflow Declarative Pipelines (DLT)
- Inspired by modern data engineering best practices
- Designed for Claude Code integration

## Related Resources

- [Databricks LDP Documentation](https://www.databricks.com/product/data-engineering/spark-declarative-pipelines)
- [Delta Lake](https://delta.io/)
- [Databricks Asset Bundles](https://docs.databricks.com/dev-tools/bundles/index.html)
- [Medallion Architecture](https://www.databricks.com/glossary/medallion-architecture)
