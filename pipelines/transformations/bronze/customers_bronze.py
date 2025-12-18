"""Bronze layer transformation for customers data.

This module contains the transformation logic for ingesting raw customer data
from the landing zone. Bronze layer ONLY adds housekeeping columns - no business logic.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import current_timestamp, input_file_name, lit


def transform(source_df: DataFrame, spark: SparkSession) -> DataFrame:
    """
    Apply bronze layer transformation to customer data.

    Bronze layer transformation rules:
    - Add _ingestion_timestamp: When data was ingested
    - Add _source_system: Source identifier (landing_zone)
    - Add _source_file: Which file was processed
    - Preserve ALL source columns as-is
    - NO business logic transformations
    - NO data quality filtering (lenient)

    Args:
        source_df: Raw DataFrame read from landing zone
        spark: SparkSession instance

    Returns:
        DataFrame: Source data with housekeeping columns added
    """
    # Add housekeeping columns only
    bronze_df = (
        source_df.withColumn("_ingestion_timestamp", current_timestamp())
        .withColumn("_source_system", lit("landing_zone"))
        .withColumn("_source_file", input_file_name())
    )

    return bronze_df
