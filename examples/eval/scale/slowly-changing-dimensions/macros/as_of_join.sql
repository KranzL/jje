{% macro as_of_join(dim_relation, dim_key, event_column) %}

    left join {{ dim_relation }} as dim
        on  dim.{{ dim_key }} = events.{{ dim_key }}
        and events.{{ event_column }} >= dim.valid_from
        and events.{{ event_column }} <  dim.valid_to

{% endmacro %}
