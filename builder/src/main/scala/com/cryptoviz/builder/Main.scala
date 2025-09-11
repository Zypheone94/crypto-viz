package com.cryptoviz.builder

import org.apache.spark.sql.SparkSession
import org.apache.spark.sql.functions._

object Main {
  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("CryptoVizBuilder")
      .master("local[*]")
      .getOrCreate()

    import spark.implicits._

    val rawSchema = new org.apache.spark.sql.types.StructType()
      .add("title", "string")
      .add("url", "string")
      .add("source", "string")
      .add("published_at", "string")
      .add("fetched_at", "string")
      .add("_corrupt_record", "string")

    val df = spark.readStream
      .schema(rawSchema)
      .option("mode", "PERMISSIVE")
      .json("data/raw/*/*/*")

    val clean = df
      .withColumn("ts", to_timestamp($"published_at"))
      .withColumn("date", to_date($"ts"))

    val query = clean.writeStream
      .format("parquet")
      .option("path", "data/clean/parquet")
      .option("checkpointLocation", "chk/clean")
      .partitionBy("date")
      .outputMode("append")
      .trigger(org.apache.spark.sql.streaming.Trigger.ProcessingTime("10 seconds"))
      .start()

    query.awaitTermination()
  }
}
