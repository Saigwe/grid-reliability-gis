-- OpenStreetMap substations with a network level inferred from their tags:
--   primary    transforms from 22-132 kV down to 11 kV or 6.6 kV (feeds the 11 kV feeders customers hang off)
--   grid       132 kV and above with no 11 kV side
--   secondary  minor_distribution, or distribution without a voltage tag (11 kV / LV)
--   traction   railway and Underground supplies (excluded from the public network)
select
    s.osm_id,
    s.name,
    s.operator,
    s.voltage,
    s.substation_type,
    s.lon,
    s.lat,
    case
        when s.substation_type = 'traction' or s.operator in ('Network Rail', 'London Underground', 'Transport for London')
            then 'traction'
        when (s.voltage like '%11000%' or s.voltage like '%6600%')
         and (s.voltage like '%22000%' or s.voltage like '%33000%' or s.voltage like '%66000%' or s.voltage like '%132000%')
            then 'primary'
        when s.voltage like '%132000%' or s.voltage like '%275000%' or s.voltage like '%400000%' then 'grid'
        when s.substation_type = 'minor_distribution' or (s.substation_type = 'distribution' and s.voltage is null)
            then 'secondary'
        else 'unclassified'
    end                                                                 as network_level,
    z.zone,
    {{ to_bng(wgs84_point('s.lon', 's.lat')) }}                         as geom_bng
from {{ source('bronze', 'osm_substations') }} s
left join {{ ref('stg_lpn_zones') }} z on ST_Contains(z.geom, {{ wgs84_point('s.lon', 's.lat') }})
