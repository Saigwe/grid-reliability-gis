-- Primary substations with the customers mapped to them and how far those customers are.
select
    p.primary_id,
    p.primary_name,
    p.voltage,
    p.zone,
    p.lon,
    p.lat,
    count(c.lsoa_code)                                                  as lsoas,
    coalesce(sum(c.households), 0)                                      as customers,
    percentile_cont(0.5) within group (order by c.distance_m)            as median_distance_m,
    max(c.distance_m)                                                   as max_distance_m
from {{ ref('int_primary_substations') }} p
left join {{ ref('int_customer_feeder') }} c using (primary_id)
group by 1, 2, 3, 4, 5, 6
