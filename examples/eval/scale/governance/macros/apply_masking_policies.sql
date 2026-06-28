{% macro apply_masking_policies() %}
    {#
        Reads column-level meta from the model's compiled schema and attaches
        the configured Snowflake masking policy to every column flagged with
        meta.pii = true. Columns without the flag are published in the clear.
    #}
    {% if execute %}
        {% set node = graph.nodes.get(model.unique_id) %}
        {% if node is none %}
            {% do return('') %}
        {% endif %}

        {% set statements = [] %}
        {% set relation = this %}

        {% for col_name, col in node.columns.items() %}
            {% set meta = col.meta or {} %}
            {% if meta.get('pii', false) %}
                {% set policy = meta.get('masking_policy', var('default_masking_policy')) %}
                {% set ddl %}
                    alter table {{ relation }}
                    modify column {{ col_name }}
                    set masking policy {{ target.database }}.governance.{{ policy }}
                    force
                {% endset %}
                {% do statements.append(ddl) %}
            {% endif %}
        {% endfor %}

        {% for ddl in statements %}
            {% do run_query(ddl) %}
        {% endfor %}

        {% do log(
            "apply_masking_policies: " ~ statements | length ~
            " policies attached on " ~ relation, info=true
        ) %}
    {% endif %}
{% endmacro %}
