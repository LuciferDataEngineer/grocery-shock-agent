select
    index_id,
    index_name,
    period,
    cast(value as double) as index_value
from {{ source('bronze', 'cpi_observations') }}
where measure = '1'
