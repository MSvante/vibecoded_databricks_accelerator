"""Bronze layer transformation for orders data.

This module ingests raw order transactions from the source system.
"""

import dlt
from pyspark.sql import DataFrame
from pyspark.sql.functions import current_timestamp, lit


@dlt.table(
    name="orders_bronze",
    comment="Raw order transactions from source system",
    table_properties={
        "quality": "bronze",
        "pipelines.autoOptimize.managed": "true"
    }
)
def orders_bronze() -> DataFrame:
    """
    Ingest raw order transaction data.

    Returns:
        DataFrame: Raw order data with ingestion metadata
    """
    from pyspark.sql.types import StructType, StructField, StringType, DecimalType, TimestampType

    schema = StructType([
        StructField("order_id", StringType(), False),
        StructField("customer_id", StringType(), False),
        StructField("order_date", TimestampType(), True),
        StructField("order_amount", DecimalType(10, 2), True),
        StructField("order_status", StringType(), True),
    ])

    # Placeholder: Would read from source in production
    df = spark.createDataFrame([], schema)

    # Add bronze metadata
    bronze_df = df.withColumn("_ingestion_timestamp", current_timestamp()) \
                  .withColumn("_source_system", lit("order_system"))

    return bronze_df


@dlt.expect_or_drop("valid_order_id", "order_id IS NOT NULL")
@dlt.expect_or_drop("valid_customer_id", "customer_id IS NOT NULL")
def orders_bronze_quality():
    """Data quality expectations for orders bronze layer."""
    pass
