-- No outage interrupts more customers in an LSOA than live there, and every customer is mapped to exactly one
-- primary substation (households in = households mapped).
select o.outage_id, o.lsoa_code, 'more customers than households' as problem
from {{ ref('fct_interruption') }} o
join {{ ref('int_customer_feeder') }} c using (lsoa_code)
group by o.outage_id, o.lsoa_code, c.households
having sum(o.customers) > c.households
union all
select null, null, 'households lost in mapping'
from (select sum(households) as h from {{ ref('stg_lsoa_customers') }}) a,
     (select sum(households) as h from {{ ref('int_customer_feeder') }}) b
where a.h <> b.h
