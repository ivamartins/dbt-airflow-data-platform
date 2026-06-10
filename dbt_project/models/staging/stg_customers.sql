-- Staging: customers.
{{ config(materialized='view') }}

with source as (
    select * from {{ source('raw', 'customers') }}
),

renamed as (
    select
        customer_id,
        name,
        lower(trim(email))      as email,
        upper(trim(tier))       as tier,
        created_at::timestamp   as created_at
    from source
)

select * from renamed
