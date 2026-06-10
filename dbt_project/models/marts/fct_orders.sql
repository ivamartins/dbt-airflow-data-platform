-- Mart: order enriched with customer attributes. The classic "wide table"
-- used by BI tools.
{{ config(materialized='table') }}

with orders as (
    select * from {{ ref('stg_orders') }}
),

customers as (
    select * from {{ ref('stg_customers') }}
)

select
    o.order_id,
    o.customer_id,
    c.name              as customer_name,
    c.tier              as customer_tier,
    c.email             as customer_email,
    o.amount,
    o.currency,
    o.status,
    o.created_at
from orders o
left join customers c on o.customer_id = c.customer_id
