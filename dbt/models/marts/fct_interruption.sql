-- One row per outage, LSOA and restoration stage: who was off, for how long, and whether it counts.
-- Regulatory rule: customer interruptions (CI) and minutes lost (CML) count unplanned interruptions of at least
-- var('min_interruption_minutes'); shorter ones are short interruptions; planned works are reported separately.
select
    o.outage_id,
    o.primary_id,
    c.zone,
    o.lsoa_code,
    o.stage,
    o.voltage_level,
    o.planned,
    o.cause,
    o.started_at,
    o.restored_at,
    cast(date_trunc('month', o.started_at) as date)                     as month,
    o.customers,
    {{ minutes_between('o.started_at', 'o.restored_at') }}              as duration_min,
    not o.planned and {{ minutes_between('o.started_at', 'o.restored_at') }} >= {{ var('min_interruption_minutes') }}
                                                                        as counts_for_indices,
    not o.planned and {{ minutes_between('o.started_at', 'o.restored_at') }} < {{ var('min_interruption_minutes') }}
                                                                        as is_short_interruption
from {{ ref('stg_outages') }} o
join {{ ref('int_customer_feeder') }} c using (lsoa_code)
