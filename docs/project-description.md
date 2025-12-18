# Project Description

## Overview

The **Databricks ETL Framework** is a Python-based accelerator for building scalable, maintainable data pipelines using **Lakeflow Declarative Pipelines (LDP)** and **Databricks Workflows**.

## Purpose

This framework enables data engineers to:
- Define data pipelines declaratively through YAML configuration
- Implement transformations in modular Python files
- Orchestrate pipelines using tag-based execution
- Deploy pipelines as Databricks Asset Bundles (DAB) via CI/CD

## Key Principles

1. **Configuration-Driven**: Pipeline metadata (tables, tags, dependencies) defined in `config.yml`
2. **Python-First**: All transformations written in Python (no SQL limitations)
3. **Tag-Based Orchestration**: Execute subsets of pipelines using tags (e.g., `daily`, `critical`, `bronze`)
4. **Medallion Architecture**: Bronze → Silver → Gold data layers
5. **Infrastructure Independence**: Pipeline code separate from workspace/cluster management

## What This Framework Is NOT

- **NOT an infrastructure provisioning tool** - Databricks workspace, clusters, and permissions are managed by a separate DevOps repository
- **NOT a data extraction framework** - Extraction layer is planned for future development (currently TBD)

## Core Components

### 1. LDP Engine
Python-based engine that:
- Reads `config.yml` to discover tables and their metadata
- Filters tables based on tags passed as parameters
- Dynamically imports and executes transformation modules
- Leverages Databricks LDP framework for dependency management and incremental processing

### 2. Configuration File (`config.yml`)
YAML file containing table metadata:
- Table name and data layer (bronze/silver/gold)
- Associated tags for selective execution
- Dependencies between tables
- Source information (TBD)

### 3. Transformation Modules
Python files organized by data layer (`bronze/`, `silver/`, `gold/`) containing:
- Data transformation logic using PySpark
- Table-specific business rules
- Modular, testable code

### 4. Workflow Orchestration
Databricks workflow that:
- Invokes the LDP engine with parameterized tags
- Supports both batch and streaming execution modes
- Handles job scheduling and monitoring

### 5. Deployment Pipeline
CI/CD automation using GitHub Actions or Azure DevOps that:
- Validates configuration and code
- Packages pipelines as Databricks Asset Bundle
- Deploys to target Databricks workspace

## Target Users

Data engineers building ETL/ELT pipelines on Databricks who need:
- Reusable framework for common pipeline patterns
- Tag-based execution for flexible orchestration
- Maintainable, version-controlled pipeline code
- Automated deployment to Databricks

## Success Criteria

The framework is successful when:
1. Engineers can add new tables by creating a config entry and transformation file
2. Pipelines can be executed selectively using tags (e.g., "run only critical daily tables")
3. Dependencies are automatically resolved by the LDP engine
4. Changes deploy automatically via CI/CD
5. Code remains maintainable and testable outside of Databricks
