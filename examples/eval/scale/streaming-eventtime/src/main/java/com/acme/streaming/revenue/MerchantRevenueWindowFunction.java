package com.acme.streaming.revenue;

import org.apache.flink.streaming.api.functions.windowing.ProcessWindowFunction;
import org.apache.flink.streaming.api.windowing.windows.TimeWindow;
import org.apache.flink.util.Collector;

public class MerchantRevenueWindowFunction
        extends ProcessWindowFunction<RevenueAccumulator, MerchantRevenuePanel, String, TimeWindow> {

    @Override
    public void process(
            String merchantId,
            Context context,
            Iterable<RevenueAccumulator> elements,
            Collector<MerchantRevenuePanel> out) {

        RevenueAccumulator acc = elements.iterator().next();

        MerchantRevenuePanel panel = new MerchantRevenuePanel();
        panel.merchantId = merchantId;
        panel.windowStartMillis = context.window().getStart();
        panel.windowEndMillis = context.window().getEnd();
        panel.grossCents = acc.grossCents;
        panel.orderCount = acc.orderCount;

        long observedLag = acc.maxIngestTimestampMillis - acc.maxEventTimestampMillis;
        panel.maxIngestionLagMillis = Math.max(0L, observedLag);
        panel.emittedAtMillis = context.currentProcessingTime();

        out.collect(panel);
    }
}

class MerchantRevenuePanel {
    public String merchantId;
    public long windowStartMillis;
    public long windowEndMillis;
    public long grossCents;
    public long orderCount;
    public long maxIngestionLagMillis;
    public long emittedAtMillis;
}
