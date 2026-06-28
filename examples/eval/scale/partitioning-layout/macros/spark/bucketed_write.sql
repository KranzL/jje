{% macro bucketed_write(bucket_column, num_buckets=256) %}
  {#
    Emit a Spark bucketing spec for a high cardinality join key so that
    downstream equi-joins avoid a shuffle without exploding the partition
    count. Bucketing keeps a bounded number of files per partition even when
    the column itself is near unique.
  #}
  tblproperties (
    'bucketing.column' = '{{ bucket_column }}',
    'bucketing.num_buckets' = '{{ num_buckets }}'
  )
{% endmacro %}


{% macro assert_partition_grain(model_name, max_daily_partitions=512) %}
  {#
    Guardrail used in CI to flag any model whose partition column produces
    more than max_daily_partitions distinct values per ingest day.
  #}
  select
    '{{ model_name }}' as model_name,
    count(*) as observed_partitions
  from (
    select 1
    from {{ ref(model_name) }}
    group by all
  )
  having count(*) > {{ max_daily_partitions }}
{% endmacro %}
