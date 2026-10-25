select
    feeder_id,
    substation,
    latitude,
    longitude,
    customers_served
from {{ source('bronze', 'feeders') }}
