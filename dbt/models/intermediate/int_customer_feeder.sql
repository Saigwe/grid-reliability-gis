-- Each LSOA's customers mapped to the nearest primary substation (straight-line distance in British National Grid).
-- OSM has no feeder connectivity, so nearest-asset is the proxy; distances are kept to show how far it stretches.
with ranked as (
    select
        c.lsoa_code,
        c.zone,
        c.households,
        c.lon,
        c.lat,
        p.primary_id,
        ST_Distance(c.geom_bng, p.geom_bng)                             as distance_m,
        row_number() over (partition by c.lsoa_code
                           order by ST_Distance(c.geom_bng, p.geom_bng), p.primary_id) as rnk
    from {{ ref('stg_lsoa_customers') }} c
    cross join {{ ref('int_primary_substations') }} p
)
select lsoa_code, zone, households, lon, lat, primary_id, distance_m
from ranked
where rnk = 1
