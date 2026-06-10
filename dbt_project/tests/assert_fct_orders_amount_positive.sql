-- Custom singular test: every order amount must be strictly positive.
-- This is the "data quality framework" component of the JD — same kind
-- of rule a Soda or Great Expectations check would express.
select *
from {{ ref('fct_orders') }}
where amount <= 0
