select *
from {{ ref('mart_category_monthly') }}
where period = (
    select max(period)
    from {{ ref('mart_category_monthly') }}
    where index_id = '10001' and yoy_pct is not null
)
