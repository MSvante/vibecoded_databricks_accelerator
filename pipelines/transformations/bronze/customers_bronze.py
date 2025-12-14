"""Bronze layer transformation for customers data.

This module ingests raw customer data from the source system.
Bronze layer performs minimal transformation - primarily schema enforcement and metadata addition.
"""

import dlt
from pyspark.sql import DataFrame
from pyspark.sql.functions import current_timestamp, lit


@dlt.table(
    name="customers_bronze",
    comment="Raw customer data from source system with ingestion metadata",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.managed": "true"
    }
)
def customers_bronze() -> DataFrame:
    """
    Ingest raw customer data from source system.

    Bronze layer transformations:
    - Add ingestion timestamp
    - Add source system identifier
    - Preserve all source columns as-is
    - No data quality enforcement at this layer

    Returns:
        DataFrame: Raw customer data with metadata columns

    Note:
        Source extraction is currently TBD. This is a placeholder that would
        typically read from S3, JDBC, Kafka, or other source systems.
    """

    # TODO: Replace with actual source extraction
    # Example patterns:
    # - S3: spark.read.format("json").load("s3://bucket/path/")
    # - JDBC: spark.read.format("jdbc").options(...).load()
    # - Kafka: spark.readStream.format("kafka").options(...).load()

    # Placeholder: Create sample schema for demonstration
    # In production, this would read from actual source
    from pyspark.sql.types import StructType, StructField, StringType, IntegerType, TimestampType

    schema = StructType([
        StructField("customer_id", StringType(), False),
        StructField("first_name", StringType(), True),
        StructField("last_name", StringType(), True),
        StructField("email", StringType(), True),
        StructField("phone", StringType(), True),
        StructField("created_at", TimestampType(), True),
    ])

    # Placeholder: Would read from source in production
    # df = spark.read.format("json").schema(schema).load("source_path")

    # For now, return empty DataFrame with correct schema
    df = spark.createDataFrame([], schema)

    # Add bronze layer metadata
    bronze_df = df.withColumn("_ingestion_timestamp", current_timestamp()) \
                  .withColumn("_source_system", lit("source_system_name"))

    return bronze_df


# Data quality expectations can be added as separate functions
@dlt.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
def customers_bronze_quality():
    """
    Optional: Define data quality expectations for bronze layer.

    Bronze layer typically uses lenient quality rules (log warnings vs. drop rows).
    """
    pass
