with ordered as (
    select
        rate_date,
        cash_rate_target,
        cash_rate_change_published,
        overnight_cash_rate,
        lag(cash_rate_target) over (order by rate_date) as previous_target
    from {{ ref('stg_cash_rate') }}
)

select
    rate_date as decision_date,
    previous_target,
    cash_rate_target,
    round(cash_rate_target - previous_target, 2) as change_from_level,
    cash_rate_change_published,
    overnight_cash_rate,
    case
        when cash_rate_target > previous_target then 'hike'
        when cash_rate_target < previous_target then 'cut'
        else 'unchanged'
    end as move
from ordered
where previous_target is not null
  and cash_rate_target <> previous_target
