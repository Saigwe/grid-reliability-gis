-- How complete the open network map is: OpenStreetMap against UKPN's own published counts for London (LPN), and
-- Census households against UKPN's customer count (which also includes businesses).
with osm as (
    select
        count(*) filter (where network_level = 'primary' and zone is not null)          as osm_primary,
        count(*) filter (where network_level = 'grid' and zone is not null)             as osm_grid,
        count(*) filter (where network_level = 'secondary' and zone is not null)        as osm_secondary,
        count(*) filter (where network_level = 'unclassified' and zone is not null)     as osm_unclassified
    from {{ ref('stg_osm_substations') }}
),
ukpn as (
    select
        cast(primary_substation as integer)                             as ukpn_primary,
        cast(grid_substation as integer)                                as ukpn_grid,
        cast(secondary_substations_gm as integer) + cast(secondary_substations_pm as integer) as ukpn_secondary,
        cast(no_of_customers as double) * 1000000                       as ukpn_customers
    from {{ source('bronze', 'network_statistics') }}
    where licence_area like 'London%'
),
census as (select sum(households) as households from {{ ref('stg_lsoa_customers') }})
select
    o.*, u.*, c.households,
    1.0 * o.osm_primary / u.ukpn_primary                                as primary_coverage,
    1.0 * o.osm_secondary / u.ukpn_secondary                            as secondary_coverage,
    c.households / u.ukpn_customers                                     as households_share_of_customers
from osm o, ukpn u, census c
