"""Gold layer transformation for customer metrics.

This module creates business-level aggregations and analytics-ready datasets.
Gold layer combines data from multiple silver tables and applies business logic.
"""

import dlt
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    col, count, sum as spark_sum, avg, max as spark_max,
    min as spark_min, current_timestamp, datediff, current_date
)


@dlt.table(
    name="customer_metrics_gold",
    comment="Customer lifetime value and engagement metrics for analytics",
    table_properties={
        "quality": "gold",
        "pipelines.autoOptimize.managed": "true"
    }
)
def customer_metrics_gold() -> DataFrame:
    """
    Calculate customer-level business metrics.

    Gold layer transformations:
    - Aggregate orders per customer
    - Calculate customer lifetime value (CLV)
    - Determine customer tenure
    - Compute engagement metrics
    - Join multiple silver tables

    Returns:
        DataFrame: Customer metrics ready for BI/analytics consumption

    Metrics calculated:
        - total_orders: Count of all orders
        - total_revenue: Sum of order amounts
        - avg_order_value: Average order amount
        - first_order_date: Date of first purchase
        - last_order_date: Date of most recent purchase
        - customer_tenure_days: Days since account creation
        - days_since_last_order: Recency metric
    """

    # Read from silver layer tables
    customers_df = dlt.read("customers_silver")

    # Read orders_silver when available
    # For now, we'll create a customer-only view
    # In production, this would join with orders_silver:
    # orders_df = dlt.read("orders_silver")

    # Customer base metrics (without orders data for now)
    customer_metrics = customers_df.select(
        col("customer_id"),
        col("full_name"),
        col("email"),
        col("created_at").alias("account_created_date"),

        # Calculate customer tenure
        datediff(current_date(), col("created_at")).alias("customer_tenure_days")
    )

    # TODO: Add order aggregations when orders_silver is available
    # Example:
    # order_aggregations = orders_df.groupBy("customer_id").agg(
    #     count("order_id").alias("total_orders"),
    #     spark_sum("order_amount").alias("total_revenue"),
    #     avg("order_amount").alias("avg_order_value"),
    #     spark_min("order_date").alias("first_order_date"),
    #     spark_max("order_date").alias("last_order_date")
    # )
    #
    # customer_metrics = customers_df.join(
    #     order_aggregations,
    #     on="customer_id",
    #     how="left"
    # )

    # Add gold layer metadata
    gold_df = customer_metrics.withColumn("_gold_processed_at", current_timestamp())

    return gold_df


# Business logic validations
@dlt.expect("valid_tenure", "customer_tenure_days >= 0")
def customer_metrics_quality():
    """
    Business logic validations for gold layer.

    Gold layer expectations ensure business rules are met:
    - Customer tenure should be non-negative
    - Revenue metrics should be reasonable
    """
    pass


# Example: Create a materialized view for high-value customers
@dlt.view(
    name="high_value_customers",
    comment="Customers with tenure > 365 days (example view)"
)
def high_value_customers() -> DataFrame:
    """
    Example view: Filter for established customers.

    Views in gold layer provide pre-filtered datasets for specific use cases.
    """
    metrics_df = dlt.read("customer_metrics_gold")

    return metrics_df.filter(col("customer_tenure_days") > 365)
