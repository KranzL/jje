{% macro convert_to_reporting_currency(amount_column, fx_rate_column) %}
    cast({{ amount_column }} * {{ fx_rate_column }} as numeric(18,4))
{% endmacro %}


{% macro reporting_currency_code() %}
    'USD'
{% endmacro %}
