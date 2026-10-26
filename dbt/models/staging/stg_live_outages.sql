-- REAL outages from UKPN's two open feeds (snapshots at download time), inside the study area. An incident can
-- appear in both feeds; the live-faults record wins because it carries the number of customers affected.
with live as (
    select incident_ref as outage_ref, 'live faults' as feed, power_cut_type as outage_type,
           cast(created_at as timestamp) as started_at, cast(restored_at as timestamp) as restored_at,
           cast(customers_affected as integer) as customers_affected, lon, lat
    from {{ source('bronze', 'live_faults') }}
    where lon is not null
),
national as (
    select fault_id, 'national outages', case when planned = 'TRUE' then 'Planned' else 'Unplanned' end,
           cast(substr(start_at, 1, 19) as timestamp), cast(substr(restored_at, 1, 19) as timestamp),
           cast(null as integer), lon, lat
    from {{ source('bronze', 'national_outages') }}
    where lon is not null
)
select o.*, z.zone, {{ to_bng(wgs84_point('o.lon', 'o.lat')) }} as geom_bng
from (
    select *, row_number() over (partition by outage_ref order by case when feed = 'live faults' then 0 else 1 end) as pick
    from (select * from live union all select * from national) u
) o
join {{ ref('stg_lpn_zones') }} z on ST_Contains(z.geom, {{ wgs84_point('o.lon', 'o.lat') }})
where o.pick = 1
