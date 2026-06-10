{#
  Macro: cents_to_dollars
  Description: converts an integer cents column to numeric dollars with 2dp.
#}
{% macro cents_to_dollars(column_name) %}
    ({{ column_name }}::numeric / 100)::numeric(18, 2)
{% endmacro %}
