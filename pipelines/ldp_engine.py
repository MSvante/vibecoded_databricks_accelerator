"""Lakeflow Declarative Pipeline (LDP) Engine.

This module orchestrates the execution of data pipelines based on configuration.
It reads config.yml, filters tables by tags, resolves dependencies, and
dynamically loads transformation modules.
"""

import argparse
import importlib
import sys
from pathlib import Path
from typing import List, Dict, Set, Any
import yaml


class LDPEngine:
    """
    Lakeflow Declarative Pipeline Engine.

    Orchestrates pipeline execution by:
    1. Loading and validating configuration
    2. Filtering tables by tags
    3. Resolving dependencies (topological sort)
    4. Dynamically importing transformation modules
    5. Executing pipelines via Databricks LDP
    """

    def __init__(self, config_path: str = "config.yml"):
        """
        Initialize LDP Engine.

        Args:
            config_path: Path to configuration YAML file
        """
        self.config_path = config_path
        self.config = None
        self.tables = []

    def load_config(self) -> None:
        """
        Load and validate configuration from YAML file.

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file has invalid YAML syntax
            ValueError: If configuration is invalid
        """
        config_file = Path(self.config_path)

        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(config_file, 'r') as f:
            self.config = yaml.safe_load(f)

        if not self.config or 'tables' not in self.config:
            raise ValueError("Configuration must contain 'tables' key")

        self.tables = self.config['tables']

        print(f"Loaded configuration with {len(self.tables)} tables")

    def validate_config(self) -> None:
        """
        Validate configuration for common errors.

        Checks:
        - No duplicate table names
        - All dependencies exist
        - No circular dependencies

        Raises:
            ValueError: If configuration is invalid
        """
        table_names = [t['name'] for t in self.tables]

        # Check for duplicates
        if len(table_names) != len(set(table_names)):
            duplicates = [name for name in table_names if table_names.count(name) > 1]
            raise ValueError(f"Duplicate table names found: {set(duplicates)}")

        # Check dependencies exist
        for table in self.tables:
            for dep in table.get('depends_on', []):
                if dep not in table_names:
                    raise ValueError(
                        f"Table '{table['name']}' depends on non-existent table '{dep}'"
                    )

        # Check for circular dependencies
        self._check_circular_dependencies()

        print("Configuration validation passed")

    def _check_circular_dependencies(self) -> None:
        """
        Detect circular dependencies using DFS.

        Raises:
            ValueError: If circular dependency detected
        """
        graph = {t['name']: t.get('depends_on', []) for t in self.tables}

        def has_cycle(node: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        visited = set()
        for node in graph:
            if node not in visited:
                if has_cycle(node, visited, set()):
                    raise ValueError(f"Circular dependency detected involving '{node}'")

    def filter_tables_by_tags(self, tags: List[str], tag_mode: str = "OR") -> List[Dict]:
        """
        Filter tables based on specified tags.

        Args:
            tags: List of tags to filter by
            tag_mode: "OR" (any tag matches) or "AND" (all tags must match)

        Returns:
            List of table configurations matching the tag criteria
        """
        if not tags:
            return self.tables

        filtered = []

        for table in self.tables:
            table_tags = set(table.get('tags', []))

            if tag_mode == "OR":
                # Table must have at least one of the specified tags
                if any(tag in table_tags for tag in tags):
                    filtered.append(table)
            elif tag_mode == "AND":
                # Table must have all specified tags
                if all(tag in table_tags for tag in tags):
                    filtered.append(table)
            else:
                raise ValueError(f"Invalid tag_mode: {tag_mode}. Must be 'OR' or 'AND'")

        print(f"Filtered to {len(filtered)} tables with tags {tags} (mode={tag_mode})")
        return filtered

    def resolve_dependencies(self, filtered_tables: List[Dict]) -> List[str]:
        """
        Resolve table execution order using topological sort.

        Args:
            filtered_tables: List of tables to execute

        Returns:
            List of table names in execution order (dependencies first)
        """
        # Build dependency graph
        filtered_names = {t['name'] for t in filtered_tables}
        graph = {}
        in_degree = {}

        for table in filtered_tables:
            name = table['name']
            graph[name] = []
            in_degree[name] = 0

        for table in filtered_tables:
            name = table['name']
            for dep in table.get('depends_on', []):
                # Only include dependencies that are in filtered set
                # Or always include dependencies even if not tagged
                if dep in filtered_names or dep not in filtered_names:
                    # Always process dependencies first
                    if dep not in graph:
                        # Add dependency to graph if not filtered but required
                        dep_config = next((t for t in self.tables if t['name'] == dep), None)
                        if dep_config:
                            graph[dep] = []
                            in_degree[dep] = 0
                            filtered_tables.append(dep_config)

                    graph[dep].append(name)
                    in_degree[name] = in_degree.get(name, 0) + 1

        # Kahn's algorithm for topological sort
        queue = [node for node in graph if in_degree[node] == 0]
        execution_order = []

        while queue:
            # Sort queue for deterministic order
            queue.sort()
            node = queue.pop(0)
            execution_order.append(node)

            for neighbor in graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(execution_order) != len(graph):
            raise ValueError("Dependency resolution failed - possible circular dependency")

        print(f"Execution order: {' -> '.join(execution_order)}")
        return execution_order

    def load_transformation_module(self, table_name: str, layer: str) -> Any:
        """
        Dynamically import transformation module for a table.

        Args:
            table_name: Name of the table
            layer: Data layer (bronze/silver/gold)

        Returns:
            Imported module

        Raises:
            ImportError: If module cannot be imported
        """
        module_path = f"pipelines.transformations.{layer}.{table_name}"

        try:
            module = importlib.import_module(module_path)
            print(f"Loaded transformation module: {module_path}")
            return module
        except ImportError as e:
            raise ImportError(
                f"Failed to import transformation for '{table_name}' at '{module_path}': {e}"
            )

    def execute_pipeline(self, tags: List[str], mode: str = "batch", tag_mode: str = "OR") -> None:
        """
        Execute the data pipeline based on tags and mode.

        Args:
            tags: List of tags to filter tables
            mode: Execution mode ("batch" or "streaming")
            tag_mode: Tag filtering mode ("OR" or "AND")
        """
        print(f"\n{'='*60}")
        print(f"Starting LDP Engine")
        print(f"Mode: {mode}")
        print(f"Tags: {tags}")
        print(f"Tag Mode: {tag_mode}")
        print(f"{'='*60}\n")

        # Load and validate configuration
        self.load_config()
        self.validate_config()

        # Filter tables by tags
        filtered_tables = self.filter_tables_by_tags(tags, tag_mode)

        if not filtered_tables:
            print("No tables match the specified tags. Exiting.")
            return

        # Resolve dependencies and get execution order
        execution_order = self.resolve_dependencies(filtered_tables)

        # Load transformation modules
        print(f"\nLoading {len(execution_order)} transformation modules...")
        for table_name in execution_order:
            table_config = next(t for t in self.tables if t['name'] == table_name)
            layer = table_config['layer']

            try:
                self.load_transformation_module(table_name, layer)
            except ImportError as e:
                print(f"ERROR: {e}")
                sys.exit(1)

        print(f"\n{'='*60}")
        print("Pipeline execution plan ready")
        print(f"{'='*60}\n")

        # Note: Actual execution is handled by Databricks LDP runtime
        # The transformations are defined using @dlt.table decorators
        # and are automatically executed when this module is run in a DLT pipeline

        print("Transformation modules loaded successfully.")
        print("Pipeline will be executed by Databricks DLT runtime.")


def main():
    """
    Main entry point for LDP Engine CLI.
    """
    parser = argparse.ArgumentParser(
        description="Lakeflow Declarative Pipeline Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tables tagged with 'daily'
  python ldp_engine.py --tags daily

  # Run tables with both 'bronze' AND 'critical' tags
  python ldp_engine.py --tags bronze,critical --tag-mode AND

  # Run in streaming mode
  python ldp_engine.py --tags streaming --mode streaming

  # Run with custom config file
  python ldp_engine.py --config custom_config.yml --tags daily
        """
    )

    parser.add_argument(
        '--tags',
        type=str,
        required=True,
        help='Comma-separated list of tags to filter tables (e.g., "daily,critical")'
    )

    parser.add_argument(
        '--mode',
        type=str,
        choices=['batch', 'streaming'],
        default='batch',
        help='Execution mode: batch or streaming (default: batch)'
    )

    parser.add_argument(
        '--tag-mode',
        type=str,
        choices=['OR', 'AND'],
        default='OR',
        help='Tag matching mode: OR (any tag) or AND (all tags) (default: OR)'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='config.yml',
        help='Path to configuration file (default: config.yml)'
    )

    args = parser.parse_args()

    # Parse tags
    tags = [tag.strip() for tag in args.tags.split(',')]

    # Initialize and execute engine
    engine = LDPEngine(config_path=args.config)

    try:
        engine.execute_pipeline(tags=tags, mode=args.mode, tag_mode=args.tag_mode)
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
