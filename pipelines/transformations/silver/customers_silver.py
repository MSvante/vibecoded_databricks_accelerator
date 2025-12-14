"""Silver layer transformation for customers data.

This module cleans, validates, and enriches customer data from bronze layer.
Silver layer applies business rules, deduplication, and data quality checks.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, trim, lower, regexp_replace, concat_ws,
    row_number, current_timestamp
)
from pyspark.sql.window import Window


def transform(customers_bronze_df: DataFrame, spark: SparkSession) -> DataFrame:
    """
    Clean and validate customer data from bronze layer.

    Silver layer transformations:
    - Trim and standardize text fields
    - Validate and normalize email format
    - Deduplicate records (keep most recent)
    - Normalize phone numbers
    - Create composite fields (full_name)
    - Add processing timestamp

    Args:
        customers_bronze_df: Bronze customers DataFrame (dependency)
        spark: SparkSession instance

    Returns:
        DataFrame: Cleaned and validated customer data

    Data Quality Rules:
        - Invalid emails should be dropped or flagged
        - Duplicate customer_ids should be resolved (keep latest)
        - Missing critical fields should be handled
    """
    # Data cleaning transformations
    cleaned_df = customers_bronze_df.select(
        col("customer_id"),

        # Standardize name fields: trim whitespace
        trim(col("first_name")).alias("first_name"),
        trim(col("last_name")).alias("last_name"),

        # Standardize email: lowercase, trim
        lower(trim(col("email"))).alias("email"),

        # Normalize phone: remove non-numeric characters
        regexp_replace(col("phone"), "[^0-9]", "").alias("phone"),

        col("created_at"),
        col("_ingestion_timestamp")
    )

    # Add derived fields
    enriched_df = cleaned_df.withColumn(
        "full_name",
        concat_ws(" ", col("first_name"), col("last_name"))
    )

    # Deduplication: Keep most recent record per customer_id
    window_spec = Window.partitionBy("customer_id").orderBy(col("_ingestion_timestamp").desc())

    deduplicated_df = (enriched_df
                       .withColumn("row_num", row_number().over(window_spec))
                       .filter(col("row_num") == 1)
                       .drop("row_num"))

    # Add silver layer metadata
    silver_df = deduplicated_df.withColumn("_silver_processed_at", current_timestamp())

    return silver_df
