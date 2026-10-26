-- SAIFI and SAIDI per primary substation and month (and so per feeder group):
--   SAIFI = customers interrupted / customers served        (x100 = CI, interruptions per 100 customers)
--   SAIDI = customer minutes interrupted / customers served (= CML, minutes lost per customer)
-- Every primary appears every month, so a quiet month counts as zero rather than disappearing. Restoration stages
-- split an outage's customers (each customer is in exactly one stage), so summing customers counts each once.
with spine as (
    select p.primary_id, p.zone, p.customers, cast(m as date) as month
    from {{ ref('dim_primary_substation') }} p
    cross join generate_series(date '{{ var("first_month") }}', date '{{ var("last_month") }}', interval '1 month') as t(m)
    where p.customers > 0
),
monthly as (
    select
        primary_id,
        month,
        count(distinct outage_id) filter (where counts_for_indices)     as interruptions,
        sum(customers) filter (where counts_for_indices)                as customers_interrupted,
        sum(customers * duration_min) filter (where counts_for_indices) as customer_minutes_lost,
        sum(customers) filter (where is_short_interruption)             as customers_short_interrupted,
        sum(customers * duration_min) filter (where planned)            as planned_customer_minutes
    from {{ ref('fct_interruption') }}
    group by 1, 2
)
select
    s.primary_id,
    s.zone,
    s.month,
    s.customers                                                         as customers_served,
    coalesce(m.interruptions, 0)                                        as interruptions,
    coalesce(m.customers_interrupted, 0)                                as customers_interrupted,
    coalesce(m.customer_minutes_lost, 0)                                as customer_minutes_lost,
    coalesce(m.customers_short_interrupted, 0)                          as customers_short_interrupted,
    coalesce(m.planned_customer_minutes, 0)                             as planned_customer_minutes,
    coalesce(m.customers_interrupted, 0) * 1.0 / s.customers            as saifi,
    coalesce(m.customer_minutes_lost, 0) * 1.0 / s.customers            as saidi_min
from spine s
left join monthly m using (primary_id, month)
