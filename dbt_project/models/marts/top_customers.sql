-- Mart: top customers by total revenue.
{{ config(materialized='table') }}

with fct as (
    select * from {{ ref('fct_orders') }}
)

select
    customer_id,
    customer_name,
    customer_tier,
    count(*)        as orders_count,
    sum(amount)     as lifetime_revenue,
    max(created_at) as last_order_at
from fct
where status in ('paid', 'shipped', 'delivered')
group by 1, 2, 3
order by lifetime_revenue desc
