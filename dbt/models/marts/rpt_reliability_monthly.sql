-- SAIDI (customer minutes interrupted per customer served) and SAIFI (interruptions per customer served).
with served as (select sum(customers_served) as customers_served from {{ ref('stg_bronze__feeders') }})
select
    cast({{ dbt.date_trunc('month', 'o.start_ts') }} as date)                   as outage_month,
    count(*)                                                                    as outages,
    sum(o.customers_affected * o.duration_minutes) / max(s.customers_served)    as saidi_minutes,
    1.0 * sum(o.customers_affected) / max(s.customers_served)                   as saifi
from {{ ref('stg_bronze__outages') }} o
cross join served s
group by 1
