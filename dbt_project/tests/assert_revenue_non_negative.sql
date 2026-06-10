-- Custom singular test: revenue must never be negative.
select *
from {{ ref('daily_revenue_by_tier') }}
where revenue < 0
