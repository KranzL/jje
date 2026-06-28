package com.acme.streaming.revenue;

public class RevenueAccumulator {

    public long grossCents = 0L;
    public long orderCount = 0L;
    public long maxEventTimestampMillis = 0L;
    public long maxIngestTimestampMillis = 0L;
}
