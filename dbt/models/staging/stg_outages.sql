-- SYNTHETIC outage history: one row per outage, LSOA and restoration stage (customers restored together).
select
    i.outage_id,
    e.primary_id,
    e.voltage_level,
    e.planned,
    e.cause,
    cast(e.started_at as timestamp)                                     as started_at,
    i.lsoa_code,
    i.stage,
    cast(i.customers as integer)                                        as customers,
    cast(i.restored_at as timestamp)                                    as restored_at
from {{ source('bronze', 'outage_impacts') }} i
join {{ source('bronze', 'outage_events') }} e using (outage_id)
