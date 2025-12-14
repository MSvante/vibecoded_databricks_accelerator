"""Lakeflow Declarative Pipeline (LDP) Engine.

This module is the core orchestrator that:
1. Reads config.yml and filters tables by tags (passed from workflow)
2. Resolves dependencies using topological sort
3. Derives landing zone paths from table names and environment
4. Dynamically creates @dp.table decorated functions for each table
5. Imports and executes transformation functions

The workflow calls this engine with tags like "finance" or "daily",
and this engine creates the actual DLT pipeline tables.
"""

import os
import importlib
from pathlib import Path
from typing import List, Dict, Set
import yaml

# Use Databricks Declarative Pipelines API
from pyspark.pipelines import dp
from pyspark.sql import SparkSession


class LDPEngine:
    """
    Lakeflow Declarative Pipeline Engine.

    This engine reads configuration, filters by tags, and dynamically
    creates @dp.table decorated functions that execute transformations.
    """

    def __init__(self, config_path: str = "config.yml", environment: str = None):
        """
        Initialize LDP Engine.

        Args:
            config_path: Path to configuration YAML file
            environment: Deployment environment (dev/test/prod)
                        If not provided, reads from DATABRICKS_ENVIRONMENT env var
        """
        self.config_path = config_path
        self.environment = environment or os.getenv("DATABRICKS_ENVIRONMENT", "dev")
        self.config = None
        self.tables = []
        self.landing_zone_config = None
        self.spark = SparkSession.builder.getOrCreate()

        # Registry of created table functions (for dependency resolution)
        self.table_registry = {}

    def load_config(self) -> None:
        """Load and validate configuration from YAML file."""
        config_file = Path(self.config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        if not self.config or 'tables' not in self.config:
            raise ValueError("Configuration must contain 'tables' key")

        self.tables = self.config['tables']
        self.landing_zone_config = self.config.get('landing_zone', {})

        print(f"Loaded configuration with {len(self.tables)} tables")
        print(f"Environment: {self.environment}")

    def derive_landing_zone_path(self, table_name: str, source_format: str) -> str:
        """
        Derive landing zone path from table name and environment.

        Args:
            table_name: Full table name (e.g., "customers_bronze")
            source_format: File format (parquet, csv, json, delta)

        Returns:
            ABFSS path to landing zone files

        Example:
            table_name="customers_bronze", env="dev" →
            abfss://landing-zone@storage_account_dev.dfs.core.windows.net/raw/customers/
        """
        # Remove layer suffix from table name (e.g., customers_bronze → customers)
        for suffix in ['_bronze', '_silver', '_gold']:
            if table_name.endswith(suffix):
                entity_name = table_name[:-len(suffix)]
                break
        else:
            entity_name = table_name

        # Get landing zone configuration
        storage_pattern = self.landing_zone_config.get('storage_account_pattern', 'storage_account_{env}')
        storage_account = storage_pattern.format(env=self.environment)
        container = self.landing_zone_config.get('container', 'landing-zone')
        base_path = self.landing_zone_config.get('base_path', 'raw')

        # Construct ABFSS path
        path = f"abfss://{container}@{storage_account}.dfs.core.windows.net/{base_path}/{entity_name}/"

        print(f"  Derived path for {table_name}: {path}")
        return path

    def filter_tables_by_tags(self, tags: List[str], tag_mode: str = "OR") -> List[Dict]:
        """Filter tables based on specified tags."""
        if not tags:
            return self.tables

        filtered = []
        for table in self.tables:
            table_tags = set(table.get('tags', []))

            if tag_mode == "OR":
                if any(tag in table_tags for tag in tags):
                    filtered.append(table)
            elif tag_mode == "AND":
                if all(tag in table_tags for tag in tags):
                    filtered.append(table)

        print(f"Filtered to {len(filtered)} tables with tags {tags} (mode={tag_mode})")
        return filtered

    def resolve_dependencies(self, filtered_tables: List[Dict]) -> List[str]:
        """
        Resolve table execution order using topological sort.

        Returns:
            List of table names in execution order (dependencies first)
        """
        # Build dependency graph including upstream dependencies
        all_required_tables = set()
        for table in filtered_tables:
            all_required_tables.add(table['name'])
            all_required_tables.update(table.get('depends_on', []))

        # Get full config for all required tables
        required_configs = [t for t in self.tables if t['name'] in all_required_tables]

        # Topological sort using Kahn's algorithm
        graph = {t['name']: t.get('depends_on', []) for t in required_configs}
        in_degree = {name: 0 for name in graph}

        for deps in graph.values():
            for dep in deps:
                in_degree[dep] = in_degree.get(dep, 0)

        for name, deps in graph.items():
            for dep in deps:
                in_degree[name] += 1

        queue = [node for node, degree in in_degree.items() if degree == 0]
        execution_order = []

        while queue:
            queue.sort()
            node = queue.pop(0)
            execution_order.append(node)

            for other_node, deps in graph.items():
                if node in deps:
                    in_degree[other_node] -= 1
                    if in_degree[other_node] == 0:
                        queue.append(other_node)

        print(f"Execution order: {' -> '.join(execution_order)}")
        return execution_order, required_configs

    def create_table_function(self, table_config: Dict) -> None:
        """
        Dynamically create a @dp.table decorated function for a table.

        This is where the magic happens:
        - Bronze: Read from landing zone, apply transformation
        - Silver/Gold: Read dependencies, apply transformation
        - Register with @dp.table decorator
        """
        table_name = table_config['name']
        layer = table_config['layer']
        depends_on = table_config.get('depends_on', [])

        print(f"  Creating table function: {table_name}")

        # Import transformation module
        module_path = f"pipelines.transformations.{layer}.{table_name}"
        try:
            transform_module = importlib.import_module(module_path)
        except ImportError as e:
            raise ImportError(f"Failed to import {module_path}: {e}")

        # Get the transform function
        transform_func = getattr(transform_module, 'transform')

        # Create table function based on layer
        if layer == 'bronze':
            # Bronze: Read from landing zone
            source_format = table_config['source'].get('format', self.landing_zone_config.get('default_format', 'parquet'))
            source_path = self.derive_landing_zone_path(table_name, source_format)

            @dp.table(
                name=table_name,
                comment=table_config.get('description', ''),
                table_properties={"quality": layer}
            )
            def table_func():
                # Read from landing zone
                source_df = self.spark.read.format(source_format).load(source_path)
                # Apply transformation (adds housekeeping columns)
                return transform_func(source_df, self.spark)

        else:
            # Silver/Gold: Read from dependencies
            @dp.table(
                name=table_name,
                comment=table_config.get('description', ''),
                table_properties={"quality": layer}
            )
            def table_func():
                # Read dependency DataFrames
                dep_dfs = [dp.read(dep_name) for dep_name in depends_on]
                # Apply transformation
                return transform_func(*dep_dfs, self.spark)

        # Store in registry
        self.table_registry[table_name] = table_func

    def execute_pipeline(self, tags: List[str], mode: str = "batch", tag_mode: str = "OR") -> None:
        """
        Execute the data pipeline based on tags and mode.

        Args:
            tags: List of tags to filter tables (from workflow parameter)
            mode: Execution mode ("batch" or "streaming")
            tag_mode: Tag filtering mode ("OR" or "AND")
        """
        print(f"\n{'='*60}")
        print(f"LDP Engine Starting")
        print(f"Environment: {self.environment}")
        print(f"Mode: {mode}")
        print(f"Tags: {tags}")
        print(f"Tag Mode: {tag_mode}")
        print(f"{'='*60}\n")

        # Load configuration
        self.load_config()

        # Filter tables by tags
        filtered_tables = self.filter_tables_by_tags(tags, tag_mode)

        if not filtered_tables:
            print("No tables match the specified tags.")
            return

        # Resolve dependencies
        execution_order, all_tables = self.resolve_dependencies(filtered_tables)

        # Create @dp.table functions for all required tables
        print(f"\nCreating {len(execution_order)} table functions...")
        table_configs_dict = {t['name']: t for t in all_tables}

        for table_name in execution_order:
            self.create_table_function(table_configs_dict[table_name])

        print(f"\n{'='*60}")
        print("Pipeline ready for execution by Databricks runtime")
        print(f"Tables created: {len(self.table_registry)}")
        print(f"{'='*60}\n")


# Entry point for Databricks workflow
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lakeflow Declarative Pipeline Engine")
    parser.add_argument('--tags', type=str, required=True, help='Comma-separated tags (e.g., "finance,daily")')
    parser.add_argument('--mode', type=str, default='batch', choices=['batch', 'streaming'])
    parser.add_argument('--tag-mode', type=str, default='OR', choices=['OR', 'AND'])
    parser.add_argument('--config', type=str, default='config.yml')
    parser.add_argument('--environment', type=str, help='Environment (dev/test/prod)')

    args = parser.parse_args()
    tags = [tag.strip() for tag in args.tags.split(',')]

    engine = LDPEngine(config_path=args.config, environment=args.environment)
    engine.execute_pipeline(tags=tags, mode=args.mode, tag_mode=args.tag_mode)
