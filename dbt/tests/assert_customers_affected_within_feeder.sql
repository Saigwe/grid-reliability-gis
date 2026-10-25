-- An outage can't affect more customers than its feeder serves.
select o.*
from {{ ref('stg_bronze__outages') }} o
join {{ ref('stg_bronze__feeders') }} f on f.feeder_id = o.feeder_id
where o.customers_affected > f.customers_served
