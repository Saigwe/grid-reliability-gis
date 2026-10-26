-- REAL outages from UKPN's open feeds at download time, placed on the network: nearest primary substation and
-- the LSOA they fall in (nearest centroid).
with nearest_primary as (
    select o.outage_ref, p.primary_id, ST_Distance(o.geom_bng, p.geom_bng) as distance_m,
           row_number() over (partition by o.outage_ref order by ST_Distance(o.geom_bng, p.geom_bng), p.primary_id) as rnk
    from {{ ref('stg_live_outages') }} o cross join {{ ref('int_primary_substations') }} p
)
select
    o.outage_ref, o.feed, o.outage_type, o.started_at, o.restored_at, o.customers_affected, o.zone, o.lon, o.lat,
    case when o.restored_at is not null then {{ minutes_between('o.started_at', 'o.restored_at') }} end as duration_min,
    n.primary_id,
    n.distance_m                                                        as distance_to_primary_m
from {{ ref('stg_live_outages') }} o
join nearest_primary n on n.outage_ref = o.outage_ref and n.rnk = 1
