package com.acme.streaming.revenue;

import java.util.Objects;

public class OrderEvent {

    private String orderId;
    private String merchantId;
    private long amountCents;
    private String currency;
    private long eventTimestampMillis;
    private long ingestTimestampMillis;

    public OrderEvent() {
    }

    public OrderEvent(
            String orderId,
            String merchantId,
            long amountCents,
            String currency,
            long eventTimestampMillis,
            long ingestTimestampMillis) {
        this.orderId = orderId;
        this.merchantId = merchantId;
        this.amountCents = amountCents;
        this.currency = currency;
        this.eventTimestampMillis = eventTimestampMillis;
        this.ingestTimestampMillis = ingestTimestampMillis;
    }

    public String getOrderId() {
        return orderId;
    }

    public void setOrderId(String orderId) {
        this.orderId = orderId;
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

    public String getCurrency() {
        return currency;
    }

    public void setCurrency(String currency) {
        this.currency = currency;
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

    public boolean isWellFormed() {
        return merchantId != null && !merchantId.isEmpty() && amountCents >= 0 && eventTimestampMillis > 0;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) {
            return true;
        }
        if (o == null || getClass() != o.getClass()) {
            return false;
        }
        OrderEvent that = (OrderEvent) o;
        return Objects.equals(orderId, that.orderId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(orderId);
    }
}
