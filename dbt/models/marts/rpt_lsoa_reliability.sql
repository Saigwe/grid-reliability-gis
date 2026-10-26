-- Reliability as customers in each LSOA experienced it, per year: the input to the hex map.
with experienced as (
    select
        lsoa_code,
        extract(year from month)                                        as year,
        sum(customers) filter (where counts_for_indices)                as customers_interrupted,
        sum(customers * duration_min) filter (where counts_for_indices) as customer_minutes_lost
    from {{ ref('fct_interruption') }}
    group by 1, 2
),
years as (select distinct extract(year from month) as year from {{ ref('rpt_reliability_monthly') }})
select
    c.lsoa_code,
    c.zone,
    c.primary_id,
    c.households,
    c.lon,
    c.lat,
    c.distance_m                                                        as distance_to_primary_m,
    y.year,
    coalesce(e.customers_interrupted, 0)                                as customers_interrupted,
    coalesce(e.customer_minutes_lost, 0)                                as customer_minutes_lost,
    100.0 * coalesce(e.customers_interrupted, 0) / c.households         as ci_per_100,
    1.0 * coalesce(e.customer_minutes_lost, 0) / c.households           as cml
from {{ ref('int_customer_feeder') }} c
cross join years y
left join experienced e on e.lsoa_code = c.lsoa_code and e.year = y.year
