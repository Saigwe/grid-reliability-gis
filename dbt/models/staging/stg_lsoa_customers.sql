-- Customers: Census 2021 households per LSOA, located at the LSOA's population-weighted centroid, for the LSOAs
-- inside the study area. Households stand in for domestic customers; UKPN's customer count also includes businesses.
select
    c.lsoa_code,
    z.zone,
    cast(h.households as integer)                                       as households,
    c.lon,
    c.lat,
    {{ to_bng(wgs84_point('c.lon', 'c.lat')) }}                         as geom_bng
from {{ source('bronze', 'lsoa_centroids') }} c
join {{ source('bronze', 'households') }} h using (lsoa_code)
join {{ ref('stg_lpn_zones') }} z on ST_Contains(z.geom, {{ wgs84_point('c.lon', 'c.lat') }})
