-- London Power Networks' four operational zones: the study area.
select zone, {{ wgs84_from_wkt('wkt') }} as geom
from {{ source('bronze', 'lpn_zones') }}
