-- Mart: daily revenue per customer tier. Demonstrates window functions,
-- CTEs, and aggregated business metrics.
{{ config(materialized='table') }}

with fct as (
    select * from {{ ref('fct_orders') }}
)

select
    date_trunc('day', created_at)::date   as order_day,
    customer_tier,
    count(*)                              as orders_count,
    sum(amount)                           as revenue,
    avg(amount)                           as avg_ticket
from fct
where status in ('paid', 'shipped', 'delivered')
group by 1, 2
order by 1 desc, 2
