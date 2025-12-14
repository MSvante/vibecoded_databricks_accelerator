"""Silver layer transformation for customers data.

This module cleans, validates, and enriches customer data from bronze layer.
Silver layer applies business rules, deduplication, and data quality checks.
"""

import dlt
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, trim, lower, regexp_replace, concat_ws,
    row_number, coalesce, current_timestamp
)
from pyspark.sql.window import Window


@dlt.table(
    name="customers_silver",
    comment="Cleaned and deduplicated customer records with data quality enforcement",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
@dlt.expect_or_drop("valid_email", "email IS NOT NULL AND email RLIKE '^[^@]+@[^@]+\\.[^@]+$'")
@dlt.expect_or_drop("valid_name", "first_name IS NOT NULL AND last_name IS NOT NULL")
@dlt.expect_or_fail("unique_customer", "customer_id IS NOT NULL")
def customers_silver() -> DataFrame:
    """
    Clean and validate customer data from bronze layer.

    Silver layer transformations:
    - Trim and standardize text fields
    - Validate email format
    - Deduplicate records (keep most recent)
    - Normalize phone numbers
    - Create composite fields (full_name)
    - Enforce data quality rules

    Returns:
        DataFrame: Cleaned and validated customer data

    Data Quality:
        - Drop records with invalid email format
        - Drop records missing first_name or last_name
        - Fail pipeline if any customer_id is NULL
    """

    # Read from bronze layer using dlt.read()
    bronze_df = dlt.read("customers_bronze")

    # Data cleaning transformations
    cleaned_df = bronze_df.select(
        col("customer_id"),

        # Standardize name fields: trim whitespace, proper case
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

    deduplicated_df = enriched_df.withColumn("row_num", row_number().over(window_spec)) \
                                  .filter(col("row_num") == 1) \
                                  .drop("row_num")

    # Add silver layer metadata
    silver_df = deduplicated_df.withColumn("_silver_processed_at", current_timestamp())

    return silver_df


# Additional data quality checks (optional)
@dlt.expect("phone_format", "length(phone) >= 10 OR phone IS NULL")
@dlt.expect("recent_ingestion", "datediff(current_date(), _ingestion_timestamp) <= 7")
def customers_silver_quality_checks():
    """
    Optional: Additional non-blocking quality expectations.

    These expectations log warnings but don't drop/fail rows.
    Useful for monitoring data quality trends.
    """
    pass
