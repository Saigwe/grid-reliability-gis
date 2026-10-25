select
    outage_id,
    feeder_id,
    start_ts,
    duration_minutes,
    cause,
    customers_affected
from {{ source('bronze', 'outages') }}
