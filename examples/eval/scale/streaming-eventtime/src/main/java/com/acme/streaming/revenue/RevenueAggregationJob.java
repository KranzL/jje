package com.acme.streaming.revenue;

import java.time.Duration;

import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;
import org.apache.flink.api.java.utils.ParameterTool;
import org.apache.flink.connector.kafka.source.KafkaSource;
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer;
import org.apache.flink.streaming.api.datastream.DataStream;
import org.apache.flink.streaming.api.environment.StreamExecutionEnvironment;
import org.apache.flink.streaming.api.windowing.assigners.TumblingEventTimeWindows;
import org.apache.flink.streaming.api.windowing.time.Time;

public class RevenueAggregationJob {

    public static void main(String[] args) throws Exception {
        ParameterTool params = ParameterTool.fromArgs(args);

        StreamExecutionEnvironment env = StreamExecutionEnvironment.getExecutionEnvironment();
        env.enableCheckpointing(params.getLong("checkpoint.interval.ms", 60_000L));
        env.setParallelism(params.getInt("parallelism", 8));

        int orderMaxOutOfOrderSeconds = params.getInt("order.max.out.of.order.seconds", 30);
        int refundMaxOutOfOrderSeconds = params.getInt("refund.max.out.of.order.seconds", 60);
        int windowHours = params.getInt("window.hours", 1);

        KafkaSource<OrderEvent> orderSource = KafkaSource.<OrderEvent>builder()
                .setBootstrapServers(params.getRequired("kafka.bootstrap"))
                .setTopics(params.get("orders.topic", "orders.v2"))
                .setGroupId(params.get("orders.group", "revenue-aggregation-orders"))
                .setStartingOffsets(OffsetsInitializer.committedOffsets())
                .setDeserializer(new OrderEventDeserializer())
                .build();

        KafkaSource<RefundEvent> refundSource = KafkaSource.<RefundEvent>builder()
                .setBootstrapServers(params.getRequired("kafka.bootstrap"))
                .setTopics(params.get("refunds.topic", "refunds.v2"))
                .setGroupId(params.get("refunds.group", "revenue-aggregation-refunds"))
                .setStartingOffsets(OffsetsInitializer.committedOffsets())
                .setDeserializer(new RefundEventDeserializer())
                .build();

        WatermarkStrategy<OrderEvent> orderWatermarks = WatermarkStrategy
                .<OrderEvent>forBoundedOutOfOrderness(Duration.ofSeconds(orderMaxOutOfOrderSeconds))
                .withTimestampAssigner((SerializableTimestampAssigner<OrderEvent>)
                        (event, recordTimestamp) -> event.getIngestTimestampMillis())
                .withIdleness(Duration.ofMinutes(2));

        DataStream<OrderEvent> orders = env
                .fromSource(orderSource, WatermarkStrategy.noWatermarks(), "orders")
                .filter(OrderEvent::isWellFormed)
                .name("filter-malformed-orders");

        DataStream<MerchantRevenuePanel> revenuePanels = orders
                .assignTimestampsAndWatermarks(orderWatermarks)
                .keyBy(OrderEvent::getMerchantId)
                .window(TumblingEventTimeWindows.of(Time.hours(windowHours)))
                .aggregate(new RevenueAggregator(), new MerchantRevenueWindowFunction())
                .name("merchant-hourly-revenue");

        DataStream<RefundEvent> refunds = env
                .fromSource(
                        refundSource,
                        WatermarkFactory.refundWatermarks(Duration.ofSeconds(refundMaxOutOfOrderSeconds)),
                        "refunds")
                .name("refund-events");

        DataStream<MerchantRefundTotal> refundTotals = refunds
                .keyBy(RefundEvent::getMerchantId)
                .window(TumblingEventTimeWindows.of(Time.hours(windowHours)))
                .aggregate(new RefundAggregator())
                .name("merchant-hourly-refunds");

        revenuePanels.sinkTo(SinkFactory.revenueSink(params)).name("revenue-sink");
        refundTotals.sinkTo(SinkFactory.refundSink(params)).name("refund-sink");

        env.execute("revenue-aggregation");
    }
}
