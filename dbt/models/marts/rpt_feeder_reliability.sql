-- Annual reliability per primary substation (feeder group), ranked: CI per 100 customers and CML per customer,
-- with the share of customers on the worst-served decile.
with annual as (
    select
        primary_id,
        any_value(zone)                                                 as zone,
        extract(year from month)                                        as year,
        any_value(customers_served)                                     as customers_served,
        sum(interruptions)                                              as interruptions,
        sum(customers_interrupted)                                      as customers_interrupted,
        sum(customer_minutes_lost)                                      as customer_minutes_lost,
        sum(customers_short_interrupted)                                as customers_short_interrupted
    from {{ ref('rpt_reliability_monthly') }}
    group by 1, 3
)
select
    a.*,
    100.0 * a.customers_interrupted / a.customers_served                as ci_per_100,
    1.0 * a.customer_minutes_lost / a.customers_served                  as cml,
    rank() over (partition by a.year order by 1.0 * a.customer_minutes_lost / a.customers_served desc) as cml_rank,
    ntile(10) over (partition by a.year order by 1.0 * a.customer_minutes_lost / a.customers_served desc) = 1
                                                                        as worst_decile
from annual a
