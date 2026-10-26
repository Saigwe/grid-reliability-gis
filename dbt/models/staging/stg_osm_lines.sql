-- OpenStreetMap power lines and cables in the study area's bounding box, with length in metres.
select
    osm_id,
    power,
    voltage,
    operator,
    location,
    wkt,
    {{ length_m(wgs84_from_wkt('wkt')) }}                               as length_m
from {{ source('bronze', 'osm_lines') }}
