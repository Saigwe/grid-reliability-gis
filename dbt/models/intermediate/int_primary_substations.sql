-- The feeder sources: OSM primary substations inside the study area.
select osm_id as primary_id, coalesce(name, osm_id) as primary_name, voltage, zone, lon, lat, geom_bng
from {{ ref('stg_osm_substations') }}
where network_level = 'primary' and zone is not null
