# Design Document

## Introduction

This document describes the technical architecture of the **Databricks ETL Framework**, a Python-based system for building scalable data pipelines using Lakeflow Declarative Pipelines (LDP) and Databricks Workflows.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CI/CD Pipeline                            │
│              (GitHub Actions / Azure DevOps)                 │
└─────────────────────┬───────────────────────────────────────┘
                      │ Deploy via DAB
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Databricks Workspace                            │
│  ┌────────────────────────────────────────────────────────┐ │
│  │           Databricks Workflow (Lakeflow)               │ │
│  │   Parameters: tags=["daily","critical"], mode="batch"  │ │
│  └──────────────────────┬─────────────────────────────────┘ │
│                         │ Invokes                            │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              LDP Engine (ldp_engine.py)                │ │
│  │  • Reads config.yml                                    │ │
│  │  • Filters tables by tags                              │ │
│  │  • Resolves dependencies                               │ │
│  │  • Dynamically loads transformations                   │ │
│  └──────────────────────┬─────────────────────────────────┘ │
│                         │ Executes                           │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Transformation Modules (Python)                │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐            │ │
│  │  │  Bronze  │→ │  Silver  │→ │   Gold   │            │ │
│  │  │  Layer   │  │  Layer   │  │  Layer   │            │ │
│  │  └──────────┘  └──────────┘  └──────────┘            │ │
│  └──────────────────────┬─────────────────────────────────┘ │
│                         │ Writes                             │
│                         ▼                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │              Delta Lake Tables                         │ │
│  │    (Bronze Tables → Silver Tables → Gold Tables)       │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Configuration Management (`config.yml`)

**Purpose**: Central metadata store for all tables in the pipeline.

**Structure**:
```yaml
tables:
  - name: customers_bronze
    layer: bronze
    tags:
      - bronze
      - daily
      - critical
    depends_on: []
    source:
      type: TBD  # Future: s3, jdbc, kafka, etc.
      path: TBD

  - name: customers_silver
    layer: silver
    tags:
      - silver
      - daily
    depends_on:
      - customers_bronze

  - name: customers_gold
    layer: gold
    tags:
      - gold
      - daily
    depends_on:
      - customers_silver
```

**Key Fields**:
- `name`: Table identifier (must match transformation file name)
- `layer`: Data layer (bronze/silver/gold)
- `tags`: List of tags for selective execution
- `depends_on`: List of upstream table dependencies
- `source`: Source configuration (TBD - future enhancement)

### 2. LDP Engine (`pipelines/ldp_engine.py`)

**Purpose**: Orchestrates pipeline execution based on configuration and runtime parameters.

**Responsibilities**:
1. **Configuration Loading**: Parse and validate `config.yml`
2. **Tag Filtering**: Filter tables based on input tags (e.g., `--tags daily,critical`)
3. **Dependency Resolution**: Build execution DAG respecting `depends_on` relationships
4. **Dynamic Module Loading**: Import transformation modules from `pipelines/transformations/{layer}/{name}.py`
5. **LDP Integration**: Leverage Databricks LDP framework for incremental processing and state management

**Key Algorithms**:
- **Topological Sort**: Ensure tables execute in dependency order
- **Tag Intersection**: Select tables matching ALL specified tags (AND logic) or ANY tag (OR logic - configurable)
- **Module Discovery**: Use Python `importlib` to dynamically load transformation functions

**Interface**:
```python
# Command-line invocation
python ldp_engine.py --tags daily,critical --mode batch
python ldp_engine.py --tags bronze --mode streaming
```

### 3. Transformation Modules (`pipelines/transformations/`)

**Purpose**: Contain table-specific transformation logic.

**Structure**:
```
transformations/
├── bronze/
│   ├── __init__.py
│   └── customers_bronze.py
├── silver/
│   ├── __init__.py
│   └── customers_silver.py
└── gold/
    ├── __init__.py
    └── customers_gold.py
```

**Expected Interface** (each transformation module):
```python
# transformations/bronze/customers_bronze.py
import dlt
from pyspark.sql import DataFrame

@dlt.table(
    name="customers_bronze",
    comment="Raw customer data from source system"
)
def customers_bronze() -> DataFrame:
    # Transformation logic here
    # Return DataFrame
    pass
```

**Design Principles**:
- **Single Responsibility**: One file per table
- **Testable**: Pure functions that can be unit tested
- **Idempotent**: Safe to re-run without side effects
- **Type Hints**: Use Python type annotations for clarity

### 4. Databricks Workflow (`workflows/etl_job.yml`)

**Purpose**: Orchestrate LDP engine execution with parameterized tags.

**Structure**:
```yaml
resources:
  jobs:
    etl_pipeline:
      name: ETL Pipeline
      tasks:
        - task_key: run_ldp_engine
          python_wheel_task:
            package_name: databricks_etl_framework
            entry_point: ldp_engine
            parameters:
              - "--tags"
              - "{{job.parameters.tags}}"
              - "--mode"
              - "{{job.parameters.mode}}"
      parameters:
        - name: tags
          default: "daily"
        - name: mode
          default: "batch"
```

**Features**:
- **Parameterized Execution**: Pass different tag combinations per run
- **Scheduling**: Support cron-based scheduling for batch jobs
- **Monitoring**: Integrate with Databricks job monitoring
- **Alerting**: Email/webhook notifications on failure

### 5. Databricks Asset Bundle (`databricks.yml`)

**Purpose**: Package and deploy the framework to Databricks.

**Structure**:
```yaml
bundle:
  name: databricks_etl_framework

workspace:
  root_path: /Workspace/etl_framework

resources:
  jobs:
    etl_pipeline:
      name: ETL Pipeline Job
      # Job definition from workflows/etl_job.yml

targets:
  dev:
    workspace:
      host: https://adb-xxxxx.azuredatabricks.net
  prod:
    workspace:
      host: https://adb-yyyyy.azuredatabricks.net
```

### 6. CI/CD Pipeline (`.github/workflows/deploy.yml` or Azure DevOps)

**Purpose**: Automate validation, testing, and deployment.

**Stages**:
1. **Validate**: Lint Python code, validate YAML syntax
2. **Test**: Run unit tests for transformation modules (future)
3. **Package**: Bundle code using DAB CLI
4. **Deploy**: Deploy to target Databricks workspace (dev/prod)

**Triggers**:
- Pull Request: Validate and test only
- Merge to `main`: Deploy to dev
- Tag creation (`v*`): Deploy to prod

## Data Flow

### Batch Mode
1. Workflow triggered (manual or scheduled)
2. LDP engine reads `config.yml`
3. Filter tables by tags (e.g., `tags=daily`)
4. Build execution DAG
5. Execute transformations in topological order
6. Write Delta tables to workspace
7. Update job status and metrics

### Streaming Mode
1. Workflow triggered with `mode=streaming`
2. LDP engine starts streaming queries
3. Continuous processing of incremental data
4. Auto-recovery and checkpointing via LDP
5. Monitor streaming metrics

## Dependency Management

**Strategy**: Topological sorting of tables based on `depends_on` field.

**Example**:
```yaml
# Config
customers_bronze (depends_on: [])
customers_silver (depends_on: [customers_bronze])
orders_bronze (depends_on: [])
orders_silver (depends_on: [orders_bronze, customers_silver])
```

**Execution Order**:
1. customers_bronze, orders_bronze (parallel)
2. customers_silver
3. orders_silver

**Cycle Detection**: Validate configuration at startup to prevent circular dependencies.

## Error Handling

### Configuration Errors
- **Invalid YAML**: Fail fast with clear error message
- **Missing Dependencies**: Validate that all `depends_on` tables exist
- **Duplicate Names**: Ensure table names are unique

### Runtime Errors
- **Transformation Failures**: Capture exceptions, log details, fail job
- **Missing Modules**: Check that transformation file exists before execution
- **LDP Errors**: Propagate Databricks LDP errors with context

### Recovery Strategy
- **Retry Logic**: Databricks workflow built-in retry (configurable)
- **Incremental Processing**: LDP checkpointing enables restart from last successful state
- **Manual Rerun**: Support rerunning specific tables via tags

## Testing Strategy

### Unit Tests
- **Transformation Logic**: Test each transformation function with sample DataFrames
- **Engine Logic**: Test tag filtering, dependency resolution, module loading
- **Configuration Parsing**: Validate YAML parsing and validation logic

### Integration Tests
- **Local Spark**: Run transformations against local Spark session
- **Mock Data**: Use synthetic datasets for end-to-end testing
- **CI Pipeline**: Automated test execution on PR

### Validation Tests (Future)
- **Data Quality**: Schema validation, null checks, range checks
- **Data Freshness**: Ensure tables update within SLA
- **Volume Checks**: Alert on unexpected data volume changes

## Performance Considerations

1. **Parallel Execution**: Independent tables (no dependencies) run in parallel
2. **Incremental Processing**: Use LDP's built-in incremental reads to avoid full scans
3. **Partition Pruning**: Design transformations to leverage Delta Lake partitioning
4. **Caching**: Reuse DataFrames when same table needed by multiple downstream tables

## Security Considerations

1. **Secrets Management**: Use Databricks Secrets for credentials (not hardcoded)
2. **Access Control**: Leverage Unity Catalog for table-level permissions
3. **Audit Logging**: Track which tables were processed and by whom
4. **Data Encryption**: Delta Lake tables encrypted at rest

## Future Enhancements

1. **Extraction Layer**: Add support for S3, JDBC, Kafka, REST APIs
2. **Data Quality Framework**: Built-in validation rules in `config.yml`
3. **Monitoring Dashboard**: Real-time pipeline health metrics
4. **Cost Optimization**: Auto-scaling cluster policies
5. **Schema Evolution**: Handle schema changes gracefully
6. **Multi-Workspace Deployment**: Support deploying to multiple Databricks workspaces

## Technology Stack

- **Language**: Python 3.10+
- **Framework**: Databricks Lakeflow Declarative Pipelines (LDP)
- **Orchestration**: Databricks Workflows
- **Storage**: Delta Lake
- **Deployment**: Databricks Asset Bundles (DAB)
- **CI/CD**: GitHub Actions or Azure DevOps Pipelines
- **Configuration**: YAML
