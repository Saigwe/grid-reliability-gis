-- The feeder, monthly and LSOA views of reliability add up to the same customer minutes and interruptions, and
-- nothing is restored before it started.
with f as (select sum(customers * duration_min) filter (where counts_for_indices) as cml,
                  sum(customers) filter (where counts_for_indices) as ci from {{ ref('fct_interruption') }}),
m as (select sum(customer_minutes_lost) as cml, sum(customers_interrupted) as ci from {{ ref('rpt_reliability_monthly') }}),
l as (select sum(customer_minutes_lost) as cml, sum(customers_interrupted) as ci from {{ ref('rpt_lsoa_reliability') }})
select 'monthly' as view from f, m where abs(f.cml - m.cml) > 0.01 or f.ci <> m.ci
union all select 'lsoa' from f, l where abs(f.cml - l.cml) > 0.01 or f.ci <> l.ci
union all select 'restored before start' from {{ ref('fct_interruption') }} where restored_at < started_at
