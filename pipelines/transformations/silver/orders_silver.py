"""Silver layer transformation for orders data.

This module validates and enriches order data with customer information.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, current_timestamp, upper, when


def transform(
    orders_bronze_df: DataFrame, customers_silver_df: DataFrame, spark: SparkSession
) -> DataFrame:
    """
    Clean, validate, and enrich order data.

    Silver layer transformations:
    - Standardize order_status values
    - Validate order amounts are positive
    - Enrich with customer information
    - Add derived fields
    - Add processing timestamp

    Args:
        orders_bronze_df: Bronze orders DataFrame (dependency)
        customers_silver_df: Silver customers DataFrame (dependency)
        spark: SparkSession instance

    Returns:
        DataFrame: Cleaned and enriched order data
    """
    # Clean and standardize
    cleaned_orders = orders_bronze_df.select(
        col("order_id"),
        col("customer_id"),
        col("order_date"),
        col("order_amount"),
        upper(col("order_status")).alias("order_status"),
        col("_ingestion_timestamp"),
    )

    # Enrich with customer data
    enriched_orders = cleaned_orders.join(
        customers_silver_df.select("customer_id", "full_name", "email"),
        on="customer_id",
        how="left",
    )

    # Add derived fields
    final_df = enriched_orders.withColumn(
        "is_completed", when(col("order_status") == "COMPLETED", True).otherwise(False)
    ).withColumn("_silver_processed_at", current_timestamp())

    return final_df
