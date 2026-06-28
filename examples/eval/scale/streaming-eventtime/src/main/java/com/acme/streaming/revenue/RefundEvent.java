package com.acme.streaming.revenue;

public class RefundEvent {

    private String refundId;
    private String merchantId;
    private long amountCents;
    private long eventTimestampMillis;
    private long ingestTimestampMillis;

    public RefundEvent() {
    }

    public String getRefundId() {
        return refundId;
    }

    public void setRefundId(String refundId) {
        this.refundId = refundId;
    }

    public String getMerchantId() {
        return merchantId;
    }

    public void setMerchantId(String merchantId) {
        this.merchantId = merchantId;
    }

    public long getAmountCents() {
        return amountCents;
    }

    public void setAmountCents(long amountCents) {
        this.amountCents = amountCents;
    }

    public long getEventTimestampMillis() {
        return eventTimestampMillis;
    }

    public void setEventTimestampMillis(long eventTimestampMillis) {
        this.eventTimestampMillis = eventTimestampMillis;
    }

    public long getIngestTimestampMillis() {
        return ingestTimestampMillis;
    }

    public void setIngestTimestampMillis(long ingestTimestampMillis) {
        this.ingestTimestampMillis = ingestTimestampMillis;
    }
}
