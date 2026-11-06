select
    cast("date" as date) as rate_date,
    cast(cash_rate_target as double) as cash_rate_target,
    cast(cash_rate_change_published as double) as cash_rate_change_published,
    cast(overnight_cash_rate as double) as overnight_cash_rate
from {{ source('bronze', 'cash_rate_daily') }}
where cash_rate_target is not null
