"""Gold layer transformation for customer metrics.

This module creates business-level aggregations and analytics-ready datasets.
Gold layer combines data from multiple silver tables and applies business logic.
"""

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import (
    col, count, sum as spark_sum, avg,
    current_timestamp, datediff, current_date
)


def transform(customers_silver_df: DataFrame, orders_silver_df: DataFrame, spark: SparkSession) -> DataFrame:
    """
    Calculate customer-level business metrics.

    Gold layer transformations:
    - Aggregate orders per customer
    - Calculate customer lifetime value (CLV)
    - Determine customer tenure
    - Compute engagement metrics
    - Join multiple silver tables

    Args:
        customers_silver_df: Silver customers DataFrame (dependency)
        orders_silver_df: Silver orders DataFrame (dependency)
        spark: SparkSession instance

    Returns:
        DataFrame: Customer metrics ready for BI/analytics consumption

    Metrics calculated:
        - total_orders: Count of all orders
        - total_revenue: Sum of order amounts
        - avg_order_value: Average order amount
        - customer_tenure_days: Days since account creation
    """
    # Customer base metrics
    customer_base = customers_silver_df.select(
        col("customer_id"),
        col("full_name"),
        col("email"),
        col("created_at").alias("account_created_date"),

        # Calculate customer tenure
        datediff(current_date(), col("created_at")).alias("customer_tenure_days")
    )

    # Order aggregations
    order_aggregations = orders_silver_df.groupBy("customer_id").agg(
        count("order_id").alias("total_orders"),
        spark_sum("order_amount").alias("total_revenue"),
        avg("order_amount").alias("avg_order_value")
    )

    # Join customer base with order metrics
    customer_metrics = customer_base.join(
        order_aggregations,
        on="customer_id",
        how="left"
    )

    # Add gold layer metadata
    gold_df = customer_metrics.withColumn("_gold_processed_at", current_timestamp())

    return gold_df
