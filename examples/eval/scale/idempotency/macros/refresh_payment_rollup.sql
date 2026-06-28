{% macro refresh_payment_rollup() %}

    {% set rollup_sql %}
        insert into {{ target.schema }}.payment_daily_rollup as tgt (
            event_date,
            currency_code,
            captured_minor,
            refunded_minor,
            refreshed_at
        )
        select
            event_date,
            currency_code,
            sum(case when event_type = 'captured' then amount_minor else 0 end),
            sum(case when event_type = 'refunded' then amount_minor else 0 end),
            current_timestamp
        from {{ ref('fct_payment_events') }}
        group by event_date, currency_code
        on conflict (event_date, currency_code) do update set
            captured_minor = excluded.captured_minor,
            refunded_minor = excluded.refunded_minor,
            refreshed_at   = excluded.refreshed_at;
    {% endset %}

    {% do run_query(rollup_sql) %}
    {{ log("payment_daily_rollup refreshed", info=True) }}

{% endmacro %}
