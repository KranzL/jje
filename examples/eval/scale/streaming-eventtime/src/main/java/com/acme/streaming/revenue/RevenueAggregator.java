package com.acme.streaming.revenue;

import org.apache.flink.api.common.functions.AggregateFunction;

public class RevenueAggregator
        implements AggregateFunction<OrderEvent, RevenueAccumulator, RevenueAccumulator> {

    @Override
    public RevenueAccumulator createAccumulator() {
        return new RevenueAccumulator();
    }

    @Override
    public RevenueAccumulator add(OrderEvent value, RevenueAccumulator acc) {
        acc.grossCents += value.getAmountCents();
        acc.orderCount += 1;
        if (value.getEventTimestampMillis() > acc.maxEventTimestampMillis) {
            acc.maxEventTimestampMillis = value.getEventTimestampMillis();
        }
        if (value.getIngestTimestampMillis() > acc.maxIngestTimestampMillis) {
            acc.maxIngestTimestampMillis = value.getIngestTimestampMillis();
        }
        return acc;
    }

    @Override
    public RevenueAccumulator getResult(RevenueAccumulator acc) {
        return acc;
    }

    @Override
    public RevenueAccumulator merge(RevenueAccumulator a, RevenueAccumulator b) {
        RevenueAccumulator out = new RevenueAccumulator();
        out.grossCents = a.grossCents + b.grossCents;
        out.orderCount = a.orderCount + b.orderCount;
        out.maxEventTimestampMillis = Math.max(a.maxEventTimestampMillis, b.maxEventTimestampMillis);
        out.maxIngestTimestampMillis = Math.max(a.maxIngestTimestampMillis, b.maxIngestTimestampMillis);
        return out;
    }
}
