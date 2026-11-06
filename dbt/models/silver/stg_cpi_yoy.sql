select
    index_id,
    period,
    cast(value as double) as yoy_pct
from {{ source('bronze', 'cpi_observations') }}
where measure = '3'
