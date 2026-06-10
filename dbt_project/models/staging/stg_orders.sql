-- Staging: orders from a raw "raw.orders" source (loaded by an upstream job).
-- Adds: typed columns, light cleaning, and a surrogate primary key.
{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'orders') }}
),

renamed as (
    select
        order_id,
        customer_id,
        amount::numeric(18, 2) as amount,
        upper(trim(currency))   as currency,
        lower(trim(status))     as status,
        created_at::timestamp   as created_at
    from source
)

select * from renamed
