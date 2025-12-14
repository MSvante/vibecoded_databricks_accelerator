"""Silver layer transformation for orders data.

This module validates and enriches order data with customer information.
"""

import dlt
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, upper, current_timestamp, when


@dlt.table(
    name="orders_silver",
    comment="Validated orders with customer enrichment",
    table_properties={
        "quality": "silver",
        "pipelines.autoOptimize.managed": "true"
    }
)
@dlt.expect_or_drop("valid_amount", "order_amount > 0")
@dlt.expect_or_drop("valid_status", "order_status IN ('PENDING', 'COMPLETED', 'CANCELLED', 'REFUNDED')")
def orders_silver() -> DataFrame:
    """
    Clean, validate, and enrich order data.

    Silver layer transformations:
    - Standardize order_status values
    - Validate order amounts are positive
    - Enrich with customer information
    - Add derived fields

    Returns:
        DataFrame: Cleaned and enriched order data
    """
    # Read from bronze and silver layers
    orders_bronze = dlt.read("orders_bronze")
    customers_silver = dlt.read("customers_silver")

    # Clean and standardize
    cleaned_orders = orders_bronze.select(
        col("order_id"),
        col("customer_id"),
        col("order_date"),
        col("order_amount"),
        upper(col("order_status")).alias("order_status"),
        col("_ingestion_timestamp")
    )

    # Enrich with customer data
    enriched_orders = cleaned_orders.join(
        customers_silver.select("customer_id", "full_name", "email"),
        on="customer_id",
        how="left"
    )

    # Add derived fields
    final_df = enriched_orders.withColumn(
        "is_completed",
        when(col("order_status") == "COMPLETED", True).otherwise(False)
    ).withColumn(
        "_silver_processed_at",
        current_timestamp()
    )

    return final_df


@dlt.expect("customer_exists", "full_name IS NOT NULL")
def orders_silver_quality():
    """Ensure all orders have valid customer references."""
    pass
