select
    f.feeder_id,
    f.substation,
    f.latitude,
    f.longitude,
    f.customers_served,
    count(o.outage_id)                                                          as outages,
    coalesce(sum(o.customers_affected * o.duration_minutes), 0) / f.customers_served as saidi_minutes,
    1.0 * coalesce(sum(o.customers_affected), 0) / f.customers_served           as saifi
from {{ ref('stg_bronze__feeders') }} f
left join {{ ref('stg_bronze__outages') }} o on o.feeder_id = f.feeder_id
group by 1, 2, 3, 4, 5
