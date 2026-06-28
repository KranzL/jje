package com.acme.streaming.revenue;

import java.time.Duration;

import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner;
import org.apache.flink.api.common.eventtime.WatermarkStrategy;

public final class WatermarkFactory {

    private static final Duration DEFAULT_IDLENESS = Duration.ofMinutes(2);

    private WatermarkFactory() {
    }

    public static WatermarkStrategy<RefundEvent> refundWatermarks(Duration maxOutOfOrder) {
        return WatermarkStrategy
                .<RefundEvent>forBoundedOutOfOrderness(maxOutOfOrder)
                .withTimestampAssigner((SerializableTimestampAssigner<RefundEvent>)
                        (event, recordTimestamp) -> event.getEventTimestampMillis())
                .withIdleness(DEFAULT_IDLENESS);
    }
}
