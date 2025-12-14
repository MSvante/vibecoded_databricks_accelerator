# Future Tasks & Improvements

This document tracks implementation tasks for the Databricks ETL Framework.

## BUGS - HIGHEST PRIORITY!

*No known bugs yet - initial implementation*

## High Priority Tasks

**1. Create Core Framework Structure**
- Remove FastAPI template from repository
- Create `pipelines/` directory structure
- Create `transformations/` subdirectories (bronze/, silver/, gold/)
- Create placeholder `__init__.py` files
- Create `workflows/` directory
- Create root-level `config.yml` template

**2. Implement LDP Engine Core**
- Create `pipelines/ldp_engine.py` with main entry point
- Implement YAML configuration parser for `config.yml`
- Implement configuration validation (duplicate names, missing dependencies, circular dependencies)
- Implement tag filtering logic (filter tables by specified tags)
- Implement topological sort for dependency resolution
- Add command-line argument parsing (--tags, --mode)

**3. Create Example Transformations**
- Implement `transformations/bronze/customers_bronze.py` example
- Implement `transformations/silver/customers_silver.py` example
- Implement `transformations/gold/customers_gold.py` example
- Use proper `@dlt.table` decorators
- Add docstrings explaining transformation purpose

**4. Create Sample Config File**
- Create `config.yml` with 3-5 example tables
- Include bronze → silver → gold pipeline examples
- Add varied tags (daily, hourly, critical, etc.)
- Define clear dependencies between tables
- Document each field with comments

**5. Implement Databricks Asset Bundle Configuration**
- Create `databricks.yml` with bundle definition
- Define workspace paths
- Configure dev and prod targets
- Reference workflow configuration

**6. Create Databricks Workflow Configuration**
- Create `workflows/etl_job.yml` with job definition
- Configure parameterized execution (tags, mode)
- Define cluster configuration
- Set up job scheduling options
- Configure alerting (email on failure)

**7. Set Up CI/CD Pipeline (GitHub Actions)**
- Create `.github/workflows/deploy.yml`
- Add validation stage (Python linting, YAML validation)
- Add DAB validation step
- Add deployment stages (dev on merge, prod on tag)
- Configure secrets for Databricks authentication

**8. Update Repository Documentation**
- Update `README.md` with framework overview
- Add quickstart guide
- Document configuration format
- Add example usage scenarios
- Include deployment instructions

## Medium Priority Tasks

**9. Add Python Project Configuration**
- Create `pyproject.toml` or `setup.py`
- Define dependencies (pyspark, databricks-sdk, pyyaml)
- Configure package metadata
- Add development dependencies (pytest, black, ruff)

**10. Implement Dynamic Module Loading**
- Update LDP engine to dynamically import transformation modules
- Handle import errors gracefully with clear error messages
- Support hot-reloading for development mode (optional)

**11. Add Configuration Validation Tests**
- Test YAML parsing with valid configuration
- Test error handling for invalid YAML syntax
- Test duplicate table name detection
- Test circular dependency detection
- Test missing dependency detection

**12. Create Development Documentation**
- Document how to add a new table to the pipeline
- Document tag strategy and naming conventions
- Add troubleshooting guide
- Document local development setup
- Add architecture diagrams

**13. Add Logging and Monitoring**
- Implement structured logging in LDP engine
- Log configuration loading and validation
- Log execution plan (which tables will run, in what order)
- Log transformation start/completion
- Add execution metrics (runtime per table)

**14. Support Both AND and OR Tag Logic**
- Add `--tag-mode` parameter (AND vs OR)
- AND mode: table must have ALL specified tags
- OR mode: table must have ANY specified tag
- Document the difference and use cases

## Low Priority Tasks

**15. Create Example Alternative Data Sources**
- Add commented-out examples for S3 sources in config.yml
- Add commented-out examples for JDBC sources
- Add commented-out examples for Kafka sources
- Document how these will be implemented in future

**16. Add Pre-commit Hooks**
- Configure pre-commit for Python linting (black, ruff)
- Add YAML validation pre-commit hook
- Add configuration validation pre-commit hook

**17. Create Visualization of Pipeline DAG**
- Implement `--visualize` flag to generate DAG graph
- Export as DOT format or image
- Show table dependencies and execution order
- Useful for debugging complex pipelines

**18. Add Dry-Run Mode**
- Implement `--dry-run` flag
- Show which tables would execute without actually running them
- Display execution order
- Useful for validating configuration changes

**19. Create Azure DevOps Pipeline Alternative**
- Create `azure-pipelines.yml` as alternative to GitHub Actions
- Mirror functionality of GitHub Actions workflow
- Document differences and setup instructions

**20. Add Example Unit Tests**
- Create `tests/` directory
- Add example unit test for transformation function
- Add mock data fixtures
- Document how to run tests locally

## Technical Debt

**NOTE: Extraction Layer**
- Data extraction is currently marked as TBD/future work
- Need to design how sources are configured in config.yml
- Need to implement connector logic for various source types
- Consider using existing libraries (spark-jdbc, boto3, kafka-python)

## Documentation

**21. Add Contribution Guidelines**
- Document coding standards
- Document PR process
- Add code of conduct
- Document testing requirements

**22. Create Example Scenarios**
- Daily batch ETL scenario
- Real-time streaming scenario
- Backfill scenario (historical data processing)
- Multi-environment deployment example

**23. Add FAQ Section**
- Common configuration errors
- Performance tuning tips
- Debugging failed transformations
- Cost optimization strategies

## How to Use This File

1. **Adding New Tasks**: Add new tasks under the appropriate priority section
2. **Task Format**: Use `**Task Name** - brief description with bullet points for details`
3. **Prioritization**: Move tasks between sections as priorities change
4. **Completion**: Remove completed tasks or move them to a "Recently Completed" section
5. **Review**: Regularly review and update this file during planning sessions

## Notes

- Tasks 1-8 (High Priority) form the MVP (Minimum Viable Product)
- Tasks 9-14 (Medium Priority) enhance usability and robustness
- Tasks 15-20 (Low Priority) are nice-to-have features
- Technical Debt section tracks known limitations
- Regular reviews ensure roadmap stays relevant and achievable
